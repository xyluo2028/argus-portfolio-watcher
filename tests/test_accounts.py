"""Accounts: passwords, web sessions and API keys, and how they turn sign-in on for every request."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from argus.api import server
from argus.api.server import create_app
from argus.app import Argus
from argus.db import session_scope
from argus.errors import ArgusError
from argus.models import ApiKey, AuditLog, LoginSession
from argus.services.accounts import hash_password, verify_password

TOKEN = "s3cret-token-for-tests"
PW = "correct horse battery"


@pytest.fixture(autouse=True)
def no_login_delay(monkeypatch):
    monkeypatch.setattr(server, "LOGIN_FAIL_DELAY_S", 0)


@pytest.fixture
def argus(settings):
    return Argus(settings)


@pytest.fixture
def client(argus):
    with TestClient(create_app(argus, start_hub=False), base_url="http://localhost") as c:
        yield c


def _login(c, username="me", password=PW):
    return c.post("/api/auth/login", json={"username": username, "password": password})


# -- service ----------------------------------------------------------------------------
def test_password_hashes_verify_and_never_store_the_password():
    h = hash_password(PW)
    assert PW not in h and h.startswith("scrypt$")
    assert verify_password(PW, h) and not verify_password(PW + "!", h)
    assert hash_password(PW) != h  # salted
    assert not verify_password(PW, "garbage") and not verify_password(PW, "bcrypt$1$2$3$4$5")


def test_usernames_are_normalized_and_unique(argus):
    assert argus.accounts.create("  Me ", PW)["username"] == "me"
    with pytest.raises(ArgusError) as e:
        argus.accounts.create("ME", PW)
    assert e.value.code == "ALREADY_EXISTS"
    for bad in ["", "-bot", "a b", "x" * 41, "bot/1"]:
        with pytest.raises(ArgusError):
            argus.accounts.create(bad, PW)
    with pytest.raises(ArgusError):
        argus.accounts.create("short", "1234567")  # under 8 characters


def test_authenticate(argus):
    argus.accounts.create("me", PW)
    argus.accounts.create("bot", None)  # keys only
    assert argus.accounts.authenticate("ME", PW).username == "me"
    assert argus.accounts.authenticate("me", "wrong") is None
    assert argus.accounts.authenticate("nobody", PW) is None
    assert argus.accounts.authenticate("bot", "") is None
    argus.accounts.set_disabled("me", True)
    assert argus.accounts.authenticate("me", PW) is None


def test_keys_are_hashed_and_can_be_revoked_or_expire(argus):
    argus.accounts.create("bot", None)
    made = argus.accounts.create_key("bot", "sim routine")
    raw = made["key"]
    assert raw.startswith("argus_") and made["prefix"] == raw[:12]
    with session_scope(argus.engine) as s:
        stored = s.get(ApiKey, made["id"])
        assert raw not in (stored.key_hash, stored.prefix) and len(stored.key_hash) == 64
        assert raw not in str([a.after for a in s.query(AuditLog)])  # nor in the audit log
    p = argus.accounts.key_principal(raw)
    assert (p.username, p.via) == ("bot", "key")
    assert argus.accounts.list_keys("bot")[0]["last_used_at"] is not None
    assert argus.accounts.key_principal(raw + "x") is None and argus.accounts.key_principal("nope") is None

    argus.accounts.revoke_key(made["id"])
    assert argus.accounts.key_principal(raw) is None
    assert argus.accounts.list_keys("bot") == [] and len(argus.accounts.list_keys("bot", include_revoked=True)) == 1

    short = argus.accounts.create_key("bot", "short-lived", expires_days=1)
    with session_scope(argus.engine) as s:
        s.get(ApiKey, short["id"]).expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert argus.accounts.key_principal(short["key"]) is None
    assert argus.accounts.list_keys("bot")[0]["active"] is False


def test_revoking_someone_elses_key_is_not_found(argus):
    a = argus.accounts.create("me", PW)
    argus.accounts.create("bot", None)
    k = argus.accounts.create_key("bot", "bot key")
    with pytest.raises(ArgusError) as e:
        argus.accounts.revoke_key(k["id"], account_id=a["id"])
    assert e.value.code == "NOT_FOUND"


def test_disabling_stops_sessions_and_keys_until_enabled(argus):
    acct = argus.accounts.create("bot", PW)
    sid = argus.accounts.create_session(acct["id"])
    key = argus.accounts.create_key("bot", "k")["key"]
    argus.accounts.set_disabled("bot", True)
    assert argus.accounts.session_principal(sid) is None and argus.accounts.key_principal(key) is None
    assert argus.accounts.exist()  # a disabled account still keeps sign-in on
    argus.accounts.set_disabled("bot", False)
    assert argus.accounts.session_principal(sid) and argus.accounts.key_principal(key)


def test_new_password_ends_other_sessions(argus):
    acct = argus.accounts.create("me", PW)
    mine, other = argus.accounts.create_session(acct["id"]), argus.accounts.create_session(acct["id"])
    with pytest.raises(ArgusError) as e:
        argus.accounts.change_password(acct["id"], "wrong", "new password 1", keep_session=mine)
    assert e.value.code == "WRONG_PASSWORD"
    assert argus.accounts.change_password(acct["id"], PW, "new password 1", keep_session=mine)["sessions_ended"] == 1
    assert argus.accounts.session_principal(mine) and argus.accounts.session_principal(other) is None
    assert argus.accounts.authenticate("me", "new password 1")


def test_expired_sessions_are_refused_and_cleaned_up(argus):
    acct = argus.accounts.create("me", PW)
    old = argus.accounts.create_session(acct["id"])
    with session_scope(argus.engine) as s:
        for row in s.query(LoginSession):
            row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert argus.accounts.session_principal(old) is None
    argus.accounts.create_session(acct["id"])
    with session_scope(argus.engine) as s:
        assert s.query(LoginSession).count() == 1


# -- HTTP ---------------------------------------------------------------------------------
def test_no_accounts_and_no_token_stays_open(client):
    assert client.get("/api/portfolios").status_code == 200
    assert client.get("/api/auth/status").json() == {"required": False, "authenticated": True, "methods": [],
                                                     "account": None, "setup": True, "owner": False}


def test_an_account_turns_sign_in_on_even_from_localhost(argus, client):
    argus.accounts.create("me", PW)  # e.g. from the CLI while the server runs
    assert client.get("/api/portfolios").status_code == 401
    assert client.post("/mcp/", json={}).status_code == 401
    assert client.get("/api/stream").status_code == 401
    assert client.get("/api/auth/status").json() == {"required": True, "authenticated": False,
                                                     "methods": ["password"], "account": None, "setup": False,
                                                     "owner": False}


def test_password_sign_in_sets_a_session_cookie(argus, client):
    argus.accounts.create("me", PW)
    assert _login(client, password="wrong").status_code == 401
    assert _login(client, username="nobody").status_code == 401
    r = _login(client, username="Me")
    cookie = r.headers["set-cookie"].lower()
    assert r.status_code == 200 and r.json()["account"]["username"] == "me"
    assert "argus_session=" in cookie and "httponly" in cookie and "samesite=strict" in cookie
    assert client.get("/api/portfolios").status_code == 200
    status = client.get("/api/auth/status").json()
    assert status["authenticated"] and status["account"]["username"] == "me"

    client.post("/api/auth/logout")
    with session_scope(argus.engine) as s:
        assert s.query(LoginSession).count() == 0  # ended on the server, not just forgotten by the browser
    client.cookies.clear()
    assert client.get("/api/portfolios").status_code == 401


def test_a_stolen_cookie_stops_working_after_logout(argus, client):
    argus.accounts.create("me", PW)
    _login(client)
    sid = client.cookies.get("argus_session")
    client.post("/api/auth/logout")
    client.cookies.set("argus_session", sid)  # replayed by someone who copied it
    assert client.get("/api/portfolios").status_code == 401


def test_api_key_works_for_api_and_mcp(argus, client):
    argus.accounts.create("bot", None)
    key = argus.accounts.create_key("bot", "sim")["key"]
    auth = {"Authorization": f"Bearer {key}"}
    assert client.get("/api/portfolios", headers=auth).status_code == 200
    assert client.post("/mcp/", json={}, headers=auth).status_code != 401
    assert client.get("/api/account", headers=auth).json()["account"]["username"] == "bot"
    assert client.get("/api/portfolios", headers={"Authorization": "Bearer argus_wrong"}).status_code == 401


def test_api_keys_cannot_mint_keys_or_change_the_password(argus, client):
    argus.accounts.create("bot", PW)
    auth = {"Authorization": f"Bearer {argus.accounts.create_key('bot', 'sim')['key']}"}
    assert client.post("/api/account/keys", json={"name": "more"}, headers=auth).status_code == 403
    assert client.put("/api/account/password", json={"current_password": PW, "new_password": "x" * 9},
                      headers=auth).status_code == 403
    assert client.delete("/api/account/keys/1", headers=auth).status_code == 403


def test_manage_your_own_keys_and_password_from_the_ui(argus, client):
    argus.accounts.create("me", PW)
    _login(client)
    made = client.post("/api/account/keys", json={"name": "my claude", "expires_days": 30})
    assert made.status_code == 201 and made.json()["key"].startswith("argus_")
    keys = client.get("/api/account").json()["keys"]
    assert [k["name"] for k in keys] == ["my claude"] and "key" not in keys[0]
    assert client.delete(f"/api/account/keys/{made.json()['id']}").json()["active"] is False

    r = client.put("/api/account/password", json={"current_password": "wrong", "new_password": "new password 1"})
    assert r.status_code == 403  # not 401: that would bounce the UI to the sign-in screen
    r = client.put("/api/account/password", json={"current_password": PW, "new_password": "new password 1"})
    assert r.status_code == 200
    assert client.get("/api/portfolios").status_code == 200  # this browser stays signed in


def test_repeated_failures_are_throttled(argus, client):
    argus.accounts.create("me", PW)
    for _ in range(10):
        assert _login(client, password="wrong").status_code == 401
    r = _login(client)  # even the right password, for a while
    assert r.status_code == 429 and r.json()["error"]["code"] == "TOO_MANY_ATTEMPTS"


# -- the server token alongside accounts --------------------------------------------------
@pytest.fixture
def token_client(settings):
    a = Argus(replace(settings, token=TOKEN))
    with TestClient(create_app(a, start_hub=False), base_url="http://localhost") as c:
        yield a, c


def test_server_token_still_works_and_acts_as_the_oldest_account(token_client):
    a, c = token_client
    bearer = {"Authorization": f"Bearer {TOKEN}"}
    assert c.get("/api/portfolios", headers=bearer).status_code == 200
    assert c.get("/api/account", headers=bearer).json()["error"]["code"] == "NO_ACCOUNT"
    a.accounts.create("me", PW)
    a.accounts.create("bot", PW)
    assert c.get("/api/account", headers=bearer).json()["account"]["username"] == "me"
    assert c.get("/api/auth/status").json()["methods"] == ["password", "token"]
    assert c.post("/api/auth/login", json={"token": TOKEN}).status_code == 200  # the UI's token sign-in
    assert c.get("/api/portfolios").status_code == 200


def test_serve_allows_a_public_bind_once_an_account_exists(monkeypatch, settings):
    monkeypatch.setattr(server, "_lock_data_dir", lambda d: None)
    monkeypatch.setattr("argus.config.load_settings", lambda: settings)
    ran = {}
    monkeypatch.setattr("uvicorn.run", lambda app, **kw: ran.update(kw))
    with pytest.raises(ArgusError) as e:
        server.serve(8999, "0.0.0.0")
    assert e.value.code == "INSECURE"
    Argus(settings).accounts.create("me", PW)
    server.serve(8999, "0.0.0.0")
    assert ran["host"] == "0.0.0.0"


# -- first-run setup and the owner's account management (web UI) -----------------------------------
def test_first_run_setup_makes_the_first_account_once_and_signs_in(argus, client):
    argus.portfolios.create_portfolio("growth")  # recorded before any account
    assert client.get("/api/auth/status").json()["setup"] is True
    r = client.post("/api/auth/setup", json={"username": "Me", "password": PW})
    assert r.status_code == 201 and r.json()["claimed"] == {"portfolio": 1}
    status = client.get("/api/auth/status").json()
    assert status["account"]["username"] == "me" and status["owner"] and not status["setup"]
    assert [p["name"] for p in client.get("/api/portfolios").json()] == ["growth"]
    again = client.post("/api/auth/setup", json={"username": "intruder", "password": PW})
    assert again.status_code == 409 and len(argus.accounts.list_accounts()) == 1


def test_setup_asks_for_the_server_token_when_one_is_set(token_client):
    a, c = token_client
    body = {"username": "me", "password": PW}
    assert c.post("/api/auth/setup", json=body).status_code == 401
    assert c.post("/api/auth/setup", json=body | {"token": "wrong"}).status_code == 401
    assert a.accounts.list_accounts() == []
    assert c.post("/api/auth/setup", json=body | {"token": TOKEN}).status_code == 201
    assert c.get("/api/account").json()["account"]["username"] == "me"


def test_only_the_owner_manages_accounts_and_never_with_a_key(argus, client):
    argus.accounts.create("me", PW)
    _login(client)
    made = client.post("/api/accounts", json={"username": "trader-bot"}).json()
    assert made["username"] == "trader-bot" and not made["has_password"]
    key = client.post("/api/accounts/trader-bot/keys", json={"name": "sim"}).json()
    assert key["key"].startswith("argus_")
    listed = client.get("/api/accounts").json()
    assert [x["username"] for x in listed["accounts"]] == ["me", "trader-bot"] and len(listed["keys"]) == 1
    assert "key" not in listed["keys"][0] and "key_hash" not in listed["keys"][0]
    assert client.post("/api/accounts", json={"username": "friend", "password": PW}).status_code == 201
    assert client.put("/api/accounts/friend/password", json={"password": PW + "2"}).status_code == 200
    assert client.patch("/api/accounts/friend", json={"disabled": True}).json()["disabled"]
    assert client.patch("/api/accounts/me", json={"disabled": True}).status_code == 400  # not yourself
    assert client.put("/api/accounts/me/password", json={"password": PW + "2"}).status_code == 400

    # A Bearer key is checked before the cookie, so these act as the bot.
    bot = {"Authorization": f"Bearer {key['key']}"}
    assert client.get("/api/auth/status", headers=bot).json()["owner"] is False
    for method, path, body in [("GET", "/api/accounts", None), ("POST", "/api/accounts", {"username": "x"}),
                               ("PATCH", "/api/accounts/me", {"disabled": True}),
                               ("PUT", "/api/accounts/me/password", {"password": PW + "3"}),
                               ("POST", "/api/accounts/me/keys", {"name": "steal"}),
                               ("DELETE", f"/api/accounts/keys/{key['id']}", None)]:
        assert client.request(method, path, json=body, headers=bot).status_code == 403, path
    # Even the owner's own API key can't: a leaked key mustn't be able to make accounts.
    mine = argus.accounts.create_key("me", "script")["key"]
    assert client.get("/api/accounts", headers={"Authorization": f"Bearer {mine}"}).status_code == 403
    assert client.delete(f"/api/accounts/keys/{key['id']}").json()["active"] is False
