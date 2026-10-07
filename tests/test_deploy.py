"""Safety rails for running Argus beyond localhost: token auth, host allow-list, static-file
containment, the startup guard and the one-server-per-data-dir lock."""

from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from argus.api import server
from argus.api.server import create_app
from argus.app import Argus
from argus.errors import ArgusError

TOKEN = "s3cret-token-for-tests"


@pytest.fixture
def client(settings):
    a = Argus(replace(settings, token=TOKEN, allowed_hosts=("argus.tail1234.ts.net",)))
    with TestClient(create_app(a, start_hub=False), base_url="http://localhost") as c:
        yield c


def test_api_and_mcp_need_the_token(client):
    assert client.get("/api/portfolios").status_code == 401
    assert client.get("/api/stream").status_code == 401
    assert client.post("/mcp/", json={}).status_code == 401
    assert client.get("/api/portfolios", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.get("/api/portfolios", headers={"Authorization": f"Bearer {TOKEN}"}).json() == []


def test_public_paths_stay_open(client):
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/auth/status").json() == {"required": True, "authenticated": False}
    assert client.get("/").status_code == 200  # UI shell (or the "not built" note): no data in it


def test_login_sets_an_httponly_cookie_that_unlocks_the_api(client):
    assert client.post("/api/auth/login", json={"token": "nope"}).status_code == 401
    r = client.post("/api/auth/login", json={"token": TOKEN})
    cookie = r.headers["set-cookie"].lower()
    assert r.status_code == 200 and "httponly" in cookie and "samesite=strict" in cookie
    assert client.get("/api/auth/status").json()["authenticated"] is True
    assert client.get("/api/portfolios").status_code == 200
    client.post("/api/auth/logout")
    client.cookies.clear()
    assert client.get("/api/portfolios").status_code == 401


def test_host_allow_list(client):
    ok = {"Authorization": f"Bearer {TOKEN}"}
    assert client.get("/api/health", headers={"host": "argus.tail1234.ts.net"}).status_code == 200
    assert client.get("/api/health", headers={"host": "evil.example"}).status_code == 400
    assert client.get("/api/portfolios", headers=ok | {"host": "argus.tail1234.ts.net"}).status_code == 200


def test_without_a_token_everything_is_open(settings):
    with TestClient(create_app(Argus(settings), start_hub=False), base_url="http://localhost") as c:
        assert c.get("/api/portfolios").status_code == 200
        assert c.get("/api/auth/status").json() == {"required": False, "authenticated": True}


@pytest.mark.skipif(not server.UI_DIST.exists(), reason="web UI not built")
@pytest.mark.parametrize("path", ["/%2e%2e/%2e%2e/pyproject.toml", "/..%2f..%2fpyproject.toml",
                                  "/assets/%2e%2e/%2e%2e/%2e%2e/pyproject.toml"])
def test_static_files_cannot_escape_dist(client, path):
    r = client.get(path)
    assert "[project]" not in r.text  # never the repo's files; the SPA fallback or 404 instead


def test_serve_refuses_public_bind_without_token(monkeypatch, settings):
    monkeypatch.setattr(server, "_lock_data_dir", lambda d: None)
    monkeypatch.setattr("argus.config.load_settings", lambda: replace(settings, token=None))
    with pytest.raises(ArgusError) as e:
        server.serve(8999, "0.0.0.0")
    assert e.value.code == "INSECURE"


def test_one_server_per_data_dir(tmp_path):
    first = server._lock_data_dir(tmp_path)
    if first is None:
        pytest.skip("no flock on this platform")
    with pytest.raises(ArgusError) as e:
        server._lock_data_dir(tmp_path)
    assert e.value.code == "ALREADY_RUNNING"
    first.close()
    server._lock_data_dir(tmp_path).close()  # free again once the first one exits
