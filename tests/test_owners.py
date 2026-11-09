"""Each account sees only its own records; an owner can share a portfolio read-only (argus.access).

The leak tests at the end call every API route and every MCP tool as a second account against the
first account's records, and fail when a route or tool is added without being listed here.
"""

import asyncio
import json
import sqlite3
from datetime import UTC, date, datetime

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select

from argus import access
from argus.api.server import create_app
from argus.db import _alembic_config, session_scope
from argus.errors import ArgusError
from argus.live import LiveHub
from argus.mcp_server import create_mcp
from argus.models import AlertEvent, AuditLog, PeerList, Portfolio, ValuationModel
from argus.services.portfolio import ALL, TxnInput
from tests.conftest import FIXTURES, FakeQuotes

PW = "correct horse battery"
PRICES = {"AAA": (110, 100), "BBB": (50, 49), "SPY": (500, 495), "AAPL": (200, 198), "KO": (62, 61)}
T0 = datetime(2026, 9, 1, 20, tzinfo=UTC)


def buy(sym="AAA", qty=10, price=90, ts=T0):
    return TxnInput("BUY", sym, ts, qty, price)


@pytest.fixture
def argus(make_argus):
    return make_argus([FakeQuotes("fake", PRICES)])


@pytest.fixture
def two(argus):
    """`me` (the first account) with records of every kind, and `bot` with none."""
    me = argus.accounts.create("me", PW)["id"]
    bot = argus.accounts.create("bot", None)["id"]
    with access.acting_as(me):
        argus.portfolios.create_portfolio("growth")
        txn = argus.portfolios.add_transactions("growth", [buy()])["inserted_ids"][0]
        argus.set_targets("growth", "symbol", {"AAA": 100}, dry_run=False)
        argus.watchlists.add(["BBB"], name="Tech")
        alert = argus.alerts.create("AAA", "price_above", 1)["id"]
        note = argus.notes.add("AAA", "my thesis", "thesis")["id"]
        with session_scope(argus.engine) as s:
            s.add(PeerList(account_id=me, symbol="AAA", peers=["BBB"]))
            s.add(ValuationModel(account_id=me, symbol="AAA", inputs={"metric": "revenue"}))
            s.add(AlertEvent(alert_id=alert, session_date=date.today(), value=110, message="AAA: mine fired"))
    pid = argus.portfolios.list_portfolios()[0]["id"]
    return {"me": me, "bot": bot, "pid": pid, "txn": txn, "alert": alert, "note": note}


# -- separation -------------------------------------------------------------------------
def test_unset_account_fails_closed(argus):
    """Code that runs outside any account (e.g. a new thread) must fail, not guess whose records to use."""
    import contextvars

    with pytest.raises(RuntimeError, match="No account"):
        contextvars.Context().run(argus.portfolios.list_portfolios)


def test_each_account_sees_only_its_own_records(argus, two):
    with access.acting_as(two["bot"]):
        assert argus.portfolios.list_portfolios() == []
        assert argus.watchlists.list_watchlists() == []
        assert argus.alerts.list(include_inactive=True) == [] and argus.alerts.fired(date(2000, 1, 1)) == []
        assert argus.notes.list(include_archived=True) == []
        assert argus.valuation_models() == []
        assert argus.portfolios.positions(ALL) == {} and argus.held_positions() == {}
        for ref in ("growth", two["pid"], str(two["pid"])):
            with pytest.raises(ArgusError) as e:
                argus.portfolios.get_portfolio(ref)
            assert e.value.code == "NOT_FOUND" and "growth" not in (e.value.hint or "")
        for fn in (lambda: argus.portfolios.delete_transaction(two["txn"]),
                   lambda: argus.portfolios.edit_transaction(two["txn"], qty=1),
                   lambda: argus.alerts.set_active(two["alert"], False),
                   lambda: argus.notes.update(two["note"], text="mine now"),
                   lambda: argus.watchlists.remove(["BBB"], "Tech")):
            with pytest.raises(ArgusError) as e:
                fn()
            assert e.value.code == "NOT_FOUND"
        # Names are per account: the bot can have its own "growth" and "Tech".
        argus.portfolios.create_portfolio("growth")
        argus.portfolios.add_transactions("growth", [buy("BBB", 1, 40)])
        argus.watchlists.add(["AAA"], name="Tech")
        assert [p["name"] for p in argus.portfolios.list_portfolios()] == ["growth"]
        assert list(argus.portfolios.positions("growth")) == ["BBB"]
    with access.acting_as(two["me"]):
        assert list(argus.portfolios.positions("growth")) == ["AAA"]
        assert [i["symbol"] for i in argus.watchlists.items("Tech")] == ["BBB"]
        assert len(argus.notes.list()) == 1 and argus.valuation_models()[0]["symbol"] == "AAA"


def test_the_first_account_takes_over_what_was_recorded_before(argus):
    argus.portfolios.create_portfolio("growth")  # no account yet: owner 0
    argus.notes.add("AAA", "before accounts")
    me = argus.accounts.create("me", PW)
    assert me["claimed"] == {"portfolio": 1, "note": 1}
    bot = argus.accounts.create("bot", None)
    assert bot["claimed"] == {}
    with access.acting_as(bot["id"]):
        assert argus.portfolios.list_portfolios() == [] and argus.notes.list() == []
    assert [p["name"] for p in argus.portfolios.list_portfolios()] == ["growth"]  # DEFAULT is the oldest


def test_changes_are_audited_with_the_account_that_made_them(argus, two):
    with access.acting_as(two["bot"]):
        argus.notes.add("BBB", "bot note")
    with access.acting_as(access.SYSTEM):
        argus.evaluate_alerts()  # background work: no account
    with session_scope(argus.engine) as s:
        rows = {(r.entity, r.action): r.account_id for r in s.scalars(select(AuditLog))}
    assert rows[("txn", "create")] == two["me"]
    assert rows[("note", "create")] == two["bot"]  # the latest note write


def test_system_sees_every_account_and_creates_nothing(argus, two):
    with access.acting_as(two["bot"]):
        argus.portfolios.create_portfolio("sim")
        argus.portfolios.add_transactions("sim", [buy("BBB", 1, 40)])
    with access.acting_as(access.SYSTEM):
        assert {p["name"] for p in argus.portfolios.list_portfolios()} == {"growth", "sim"}
        assert set(argus.held_positions()) == {"AAA", "BBB"}
        with pytest.raises(RuntimeError):
            argus.portfolios.create_portfolio("nope")


def test_cost_alerts_use_their_own_accounts_cost(argus, two):
    with access.acting_as(two["bot"]):
        argus.portfolios.create_portfolio("sim")
        argus.portfolios.add_transactions("sim", [buy("AAA", 1, 200)])  # bot paid 200, AAA is at 110
        argus.alerts.create("AAA", "below_cost_pct", 40)
    with access.acting_as(two["me"]):
        argus.alerts.create("AAA", "below_cost_pct", 40)  # I paid 90: not below cost
    with access.acting_as(access.SYSTEM):
        fired = argus.evaluate_alerts()
    assert [(f["account_id"], f["kind"]) for f in fired if f["kind"] == "below_cost_pct"] == [(two["bot"], "below_cost_pct")]
    hub = LiveHub(argus)
    hub.fired_alerts = [*fired, {"alert_id": two["alert"], "account_id": two["me"], "message": "AAA: mine fired"}]
    assert {a["account_id"] for a in hub.snapshot(two["bot"])["alerts_fired"]} == {two["bot"]}
    assert {a["account_id"] for a in hub.snapshot(two["me"])["alerts_fired"]} == {two["me"]}
    assert hub.snapshot(None)["alerts_fired"] == []  # open mode only sees alerts made before accounts


# -- sharing ----------------------------------------------------------------------------
def test_a_shared_portfolio_is_read_only_and_stays_out_of_all(argus, two):
    with access.acting_as(two["bot"]):
        argus.portfolios.create_portfolio("sim")
        argus.portfolios.add_transactions("sim", [buy("BBB", 2, 40)])
        with pytest.raises(ArgusError) as e:
            argus.portfolios.share("growth", "me")  # not the bot's to share
        assert e.value.code == "NOT_FOUND"
        assert argus.portfolios.share("sim", "me") == {"portfolio": "sim", "shared_with": ["me"]}
        sim = argus.portfolios.get_portfolio("sim").id
    with access.acting_as(two["me"]):
        listed = argus.portfolios.list_portfolios()
        assert listed[-1] == {"id": sim, "name": "sim", "benchmark": "SPY", "shared": True, "owner": "bot"}
        assert argus.portfolio("sim")["totals"]["position_count"] == 1
        assert [t["symbol"] for t in argus.portfolios.list_transactions(sim)] == ["BBB"]
        assert argus.simulate_trades("sim", [{"symbol": "BBB", "side": "SELL", "qty": 1}])  # what-if is a read
        assert set(argus.portfolios.positions(ALL)) == {"AAA"}  # ALL is your own only
        assert argus.held_positions() == {"AAA": (10, 90)}
        txn = argus.portfolios.list_transactions(sim)[0]["id"]
        for fn in (lambda: argus.portfolios.add_transactions("sim", [buy("BBB", 1, 40)]),
                   lambda: argus.portfolios.delete_transaction(txn),
                   lambda: argus.portfolios.edit_transaction(txn, qty=1),
                   lambda: argus.set_targets("sim", "symbol", {"BBB": 100}, dry_run=False),
                   lambda: argus.delete_portfolio("sim", "sim", dry_run=False),
                   lambda: argus.portfolios.share("sim", "me"),
                   lambda: argus.portfolios.unshare("sim", "me")):
            with pytest.raises(ArgusError) as e:
                fn()
            assert e.value.code == "READ_ONLY"
        # Importing into a name only a shared portfolio has makes your own.
        imp = argus.import_investing(FIXTURES / "sample_Holdings_01152026.csv", "sim", date(2026, 1, 2), dry_run=True)
        assert imp["creates_portfolio"]
    with access.acting_as(two["bot"]):
        assert argus.portfolios.unshare("sim", "me")["shared_with"] == []
    with access.acting_as(two["me"]):
        with pytest.raises(ArgusError) as e:
            argus.portfolio(sim)
        assert e.value.code == "NOT_FOUND"


def test_own_portfolio_wins_a_name_clash_with_a_shared_one(argus, two):
    with access.acting_as(two["bot"]):
        argus.portfolios.create_portfolio("growth")
        argus.portfolios.add_transactions("growth", [buy("BBB", 1, 40)])
        argus.portfolios.share("growth", "me")
        bots = argus.portfolios.get_portfolio("growth").id
    with access.acting_as(two["me"]):
        assert argus.portfolios.get_portfolio("growth").id == two["pid"]
        assert list(argus.portfolios.positions(bots)) == ["BBB"]  # by id


def test_deleting_a_portfolio_ends_its_shares(argus, two):
    with access.acting_as(two["me"]):
        argus.portfolios.share("growth", "bot")
        argus.delete_portfolio("growth", "growth", dry_run=False)
    with access.acting_as(two["bot"]):
        assert argus.portfolios.list_portfolios() == []


def test_share_errors(argus, two):
    with access.acting_as(two["me"]):
        for who, code in (("nobody", "NOT_FOUND"), ("me", "INVALID_ARG")):
            with pytest.raises(ArgusError) as e:
                argus.portfolios.share("growth", who)
            assert e.value.code == code
        with pytest.raises(ArgusError) as e:
            argus.portfolios.unshare("growth", "bot")
        assert e.value.code == "NOT_FOUND"
        argus.portfolios.share("growth", "bot")
        assert argus.portfolios.share("growth", "bot")["shared_with"] == ["bot"]  # again: no-op


# -- migration and snapshots --------------------------------------------------------------
def test_migration_gives_existing_records_to_the_oldest_account(tmp_path):
    """A database at 0003 (accounts, no owners) with records of every kind upgrades without losing any."""
    from alembic import command

    path = tmp_path / "v3.sqlite"
    eng = create_engine(f"sqlite:///{path}")
    cfg = _alembic_config()
    with eng.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "0003")
    with sqlite3.connect(path) as c:
        c.executescript("""
            INSERT INTO account (id, username, disabled, created_at) VALUES (7, 'me', 0, '2026-11-01 00:00:00');
            INSERT INTO portfolio (id, name, benchmark, created_at) VALUES (1, 'growth', 'SPY', '2026-09-29 00:00:00');
            INSERT INTO txn (id, portfolio_id, type, symbol, qty, price, fee, amount, ts, source, deleted, created_at)
                VALUES (1, 1, 'BUY', 'AAA', 10, 90, 0, 0, '2026-09-01 20:00:00', 'cli', 0, '2026-09-01 20:00:00');
            INSERT INTO target (portfolio_id, level, key, weight_pct) VALUES (1, 'symbol', 'AAA', 100);
            INSERT INTO watchlist (id, name) VALUES (1, 'Watchlist');
            INSERT INTO watchlist_item (watchlist_id, symbol, added_at) VALUES (1, 'BBB', '2026-09-01 00:00:00');
            INSERT INTO peer_list (symbol, peers, updated_at) VALUES ('AAA', '["BBB"]', '2026-09-01 00:00:00');
            INSERT INTO valuation_model (symbol, inputs, updated_at) VALUES ('AAA', '{}', '2026-09-01 00:00:00');
            INSERT INTO note (id, symbol, kind, text, archived, created_by, created_at, updated_at)
                VALUES (1, 'AAA', 'thesis', 't', 0, 'cli', '2026-09-01 00:00:00', '2026-09-01 00:00:00');
        """)
    from argus.db import make_engine
    make_engine(path)  # upgrades to head
    with sqlite3.connect(path) as c:
        for table in ("portfolio", "watchlist", "note", "peer_list", "valuation_model"):
            assert c.execute(f"SELECT account_id FROM {table}").fetchall() == [(7,)], table
        assert c.execute("SELECT portfolio_id, symbol FROM txn").fetchall() == [(1, "AAA")]
        assert c.execute("SELECT count(*) FROM target").fetchone() == (1,)
        assert c.execute("SELECT symbol FROM watchlist_item").fetchall() == [("BBB",)]
        assert c.execute("PRAGMA foreign_key_check").fetchall() == []
        # Names are now unique per account, not overall.
        c.execute("INSERT INTO portfolio (account_id, name, benchmark, created_at) VALUES (8, 'growth', 'SPY', '2026-11-01')")
        with pytest.raises(sqlite3.IntegrityError):
            c.execute("INSERT INTO portfolio (account_id, name, benchmark, created_at) VALUES (8, 'growth', 'SPY', '2026-11-01')")


def test_snapshot_carries_accounts_and_owners(argus, two, make_argus, tmp_path):
    with access.acting_as(two["me"]):
        argus.portfolios.share("growth", "bot")
    path = argus.snapshots.dump(tmp_path / "s.json")["file"]
    doc = json.loads(open(path).read())
    assert doc["version"] == 2 and {r["username"] for r in doc["tables"]["account"]} == {"me", "bot"}

    from argus.app import Argus
    from argus.config import Settings
    other = Argus(Settings(data_dir=tmp_path / "b", db_path=tmp_path / "b" / "b.sqlite",
                           finnhub_api_key=None, sec_user_agent=None))
    other.snapshots.restore(doc, dry_run=False)
    with access.acting_as(two["bot"]):
        assert [p["owner"] for p in other.portfolios.list_portfolios()] == ["me"]
    assert other.accounts.authenticate("me", PW) is not None  # the password hash came along


def test_a_snapshot_from_before_accounts_goes_to_the_oldest_account(argus, two, tmp_path):
    doc = argus.snapshots.export()
    doc["version"] = 1
    for t in ("account", "api_key", "portfolio_share"):
        doc["tables"].pop(t)
    for t in ("portfolio", "watchlist", "alert", "note", "peer_list", "valuation_model"):
        for r in doc["tables"][t]:
            r.pop("account_id")
    report = argus.snapshots.restore(doc, replace=True, dry_run=False)
    assert "account" not in report["will_remove"]
    assert {a["username"] for a in argus.accounts.list_accounts()} == {"me", "bot"}  # kept
    with access.acting_as(two["me"]):
        assert [p["name"] for p in argus.portfolios.list_portfolios()] == ["growth"]
        assert argus.valuation_models()[0]["symbol"] == "AAA"


def test_restoring_your_snapshot_never_touches_another_account(argus, two, tmp_path):
    with access.acting_as(two["me"]):
        mine = argus.account_snapshots.export("me")
    assert {t: len(v) for t, v in mine["tables"].items() if v} == {
        "portfolio": 1, "txn": 1, "target": 1, "watchlist": 1, "watchlist_item": 1, "alert": 1, "alert_event": 1,
        "note": 1, "peer_list": 1, "valuation_model": 1, "instrument": 2}
    with access.acting_as(two["bot"]):
        assert argus.account_snapshots.export("bot")["tables"]["portfolio"] == []
        argus.account_snapshots.restore(mine, dry_run=False)  # a copy, with new ids, owned by the bot
        assert [p["name"] for p in argus.portfolios.list_portfolios()] == ["growth"]
        assert argus.portfolios.get_portfolio("growth").id != two["pid"]
        assert list(argus.portfolios.positions("growth")) == ["AAA"] and len(argus.notes.list()) == 1
        empty = {"format": "argus-account-snapshot", "version": 1, "tables": {}}
        report = argus.account_snapshots.restore(empty, replace=True, dry_run=False, backup_dir=tmp_path, username="bot")
        assert report["will_remove"]["portfolio"] == 1 and report["backup"].endswith(".json")
        assert argus.portfolios.list_portfolios() == [] and argus.notes.list() == []
    with access.acting_as(two["me"]):  # mine are all still there, under the same ids
        assert argus.portfolios.get_portfolio("growth").id == two["pid"]
        assert argus.account_snapshots.export("me")["tables"] == mine["tables"]


def test_an_old_whole_instance_snapshot_loads_into_your_account(argus, two):
    doc = argus.snapshots.export()
    doc["version"] = 1
    for t in ("account", "api_key", "portfolio_share"):
        doc["tables"].pop(t)
    with access.acting_as(two["bot"]):
        argus.account_snapshots.restore(doc, dry_run=False)
        assert [p["name"] for p in argus.portfolios.list_portfolios()] == ["growth"]
    with access.acting_as(two["bot"]):
        doc["version"] = 2
        with pytest.raises(ArgusError, match="whole-instance"):
            argus.account_snapshots.restore(doc)


# -- leak tests: every API route and MCP tool as a second account --------------------------------
@pytest.fixture
def leak(argus, two):
    with access.acting_as(two["bot"]):
        key = argus.accounts.create_key("bot", "leak test")["key"]
    with TestClient(create_app(argus, start_hub=False), base_url="http://localhost:8787",
                    headers={"Authorization": f"Bearer {key}"}) as c:
        yield c, argus, two


DENIED = (403, 404)
MINE = ('"growth"', '"Tech"', "my thesis", "mine fired")  # strings only my records contain (JSON-quoted names)
# In a refusal: an error may echo the name asked for, but must not list mine or show their contents.
MINE_IN_REFUSAL = ("Existing:", "my thesis", "mine fired")


def _clean(text: str, marks=MINE) -> bool:
    return not any(m in text for m in marks)


def _api_routes(app) -> set[tuple[str, str]]:
    return {(m, r.path) for r in app.routes if isinstance(r, APIRoute) and r.path.startswith("/api/")
            for m in r.methods if m != "HEAD"}


# Shared market data, or routes about the caller's own account and sign-in (tests/test_accounts.py).
NOT_PER_ACCOUNT = {
    ("GET", "/api/market-status"), ("GET", "/api/quotes"), ("GET", "/api/screener"), ("POST", "/api/screener"),
    ("POST", "/api/screener/rebuild"), ("GET", "/api/market-context"), ("GET", "/api/research/{symbol}"),
    ("GET", "/api/returns/{symbol}"), ("GET", "/api/history/{symbol}"), ("GET", "/api/fundamental-series/{symbol}"),
    ("GET", "/api/profile/{symbol}"), ("GET", "/api/holdings/{symbol}"), ("GET", "/api/fundamentals/{symbol}"),
    ("GET", "/api/earnings/{symbol}"), ("GET", "/api/financials/{symbol}"), ("GET", "/api/compare"),
    ("GET", "/api/compare/history"), ("GET", "/api/health"), ("GET", "/api/auth/status"),
    ("POST", "/api/auth/login"), ("POST", "/api/auth/logout"), ("GET", "/api/account"),
    ("PUT", "/api/account/password"), ("POST", "/api/account/keys"), ("DELETE", "/api/account/keys/{key_id}"),
    ("POST", "/api/auth/setup"),
    # The owner's account management: refused to anyone else (tests/test_accounts.py).
    ("GET", "/api/accounts"), ("POST", "/api/accounts"), ("PATCH", "/api/accounts/{username}"),
    ("PUT", "/api/accounts/{username}/password"), ("POST", "/api/accounts/{username}/keys"),
    ("DELETE", "/api/accounts/keys/{key_id}"),
}


def _portfolio_routes(pid):
    """Routes on one portfolio, each tried with my portfolio's name and with its id."""
    sim = {"trades": [{"symbol": "AAA", "side": "SELL", "qty": 1}]}
    txn = {"type": "BUY", "symbol": "AAA", "qty": 1, "price": 1}
    targets = {"level": "symbol", "weights": {"AAA": 1}, "dry_run": False}
    routes = {
        ("GET", "/api/portfolios/{ref}"): ("GET", "", None),
        ("DELETE", "/api/portfolios/{ref}"): ("DELETE", "?dry_run=false&confirm=growth", None),
        ("GET", "/api/portfolios/{ref}/performance"): ("GET", "/performance", None),
        ("GET", "/api/portfolios/{ref}/transactions"): ("GET", "/transactions", None),
        ("POST", "/api/portfolios/{ref}/transactions"): ("POST", "/transactions", txn),
        ("GET", "/api/portfolios/{ref}/shares"): ("GET", "/shares", None),
        ("PUT", "/api/portfolios/{ref}/shares/{username}"): ("PUT", "/shares/bot", None),
        ("DELETE", "/api/portfolios/{ref}/shares/{username}"): ("DELETE", "/shares/bot", None),
        ("GET", "/api/portfolios/{ref}/fundamentals"): ("GET", "/fundamentals", None),
        ("GET", "/api/portfolios/{ref}/earnings"): ("GET", "/earnings", None),
        ("GET", "/api/portfolios/{ref}/dividends"): ("GET", "/dividends", None),
        ("GET", "/api/portfolios/{ref}/risk"): ("GET", "/risk", None),
        ("GET", "/api/portfolios/{ref}/exposure"): ("GET", "/exposure", None),
        ("GET", "/api/portfolios/{ref}/drift"): ("GET", "/drift", None),
        ("PUT", "/api/portfolios/{ref}/targets"): ("PUT", "/targets", targets),
        ("POST", "/api/portfolios/{ref}/simulate"): ("POST", "/simulate", sim),
    }
    out = {route: [(m, f"/api/portfolios/{ref}{tail}", body) for ref in ("growth", pid)]
           for route, (m, tail, body) in routes.items()}
    out[("GET", "/api/brief/{ref}")] = [("GET", f"/api/brief/{ref}?news=false", None) for ref in ("growth", pid)]
    return out


def test_every_api_route_refuses_or_hides_another_accounts_records(leak):
    c, argus, two = leak
    denied = _portfolio_routes(two["pid"]) | {
        ("PATCH", "/api/transactions/{txn_id}"): [("PATCH", f"/api/transactions/{two['txn']}", {"qty": 1})],
        ("DELETE", "/api/transactions/{txn_id}"): [("DELETE", f"/api/transactions/{two['txn']}", None)],
        ("PATCH", "/api/alerts/{alert_id}"): [("PATCH", f"/api/alerts/{two['alert']}?active=false", None)],
        ("PATCH", "/api/notes/{note_id}"): [("PATCH", f"/api/notes/{two['note']}", {"text": "x"})],
        ("GET", "/api/watchlists/{name}"): [("GET", "/api/watchlists/Tech", None)],
        ("DELETE", "/api/watchlists/{name}/{symbol}"): [("DELETE", "/api/watchlists/Tech/BBB", None)],
        ("GET", "/api/watchlists/{name}/fundamentals"): [("GET", "/api/watchlists/Tech/fundamentals", None)],
        ("GET", "/api/watchlists/{name}/dividends"): [("GET", "/api/watchlists/Tech/dividends", None)],
        ("GET", "/api/watchlists/{name}/earnings"): [("GET", "/api/watchlists/Tech/earnings", None)],
        ("GET", "/api/events"): [("GET", "/api/events?portfolio=growth", None),
                                 ("GET", f"/api/events?portfolio={two['pid']}", None)],
    }
    # Routes that answer with the caller's own (empty) records: they must not show mine.
    own = {
        ("GET", "/api/portfolios"): ("GET", "/api/portfolios", None),
        ("POST", "/api/portfolios"): ("POST", "/api/portfolios", {"name": "bot-sim"}),
        ("GET", "/api/watchlists"): ("GET", "/api/watchlists", None),
        ("POST", "/api/watchlists/{name}"): ("POST", "/api/watchlists/Watchlist", {"symbols": ["AAA"]}),
        ("GET", "/api/alerts"): ("GET", "/api/alerts?include_inactive=true", None),
        ("POST", "/api/alerts"): ("POST", "/api/alerts", {"symbol": "AAA", "kind": "price_above", "threshold": 1}),
        ("GET", "/api/notes"): ("GET", "/api/notes?include_archived=true", None),
        ("POST", "/api/notes"): ("POST", "/api/notes", {"symbol": "AAA", "text": "bot note"}),
        ("GET", "/api/valuation"): ("GET", "/api/valuation", None),
        ("GET", "/api/valuation/{symbol}"): ("GET", "/api/valuation/AAA", None),
        ("PUT", "/api/valuation/{symbol}"): ("PUT", "/api/valuation/AAA", {"inputs": None}),
        ("GET", "/api/peers/{symbol}"): ("GET", "/api/peers/AAA?metrics=false", None),
        ("PUT", "/api/peers/{symbol}"): ("PUT", "/api/peers/AAA", {"peers": None}),
        ("GET", "/api/search"): ("GET", "/api/search?q=AAA", None),
        ("GET", "/api/snapshot"): ("GET", "/api/snapshot", None),
        ("POST", "/api/snapshot/restore"): ("POST", "/api/snapshot/restore?dry_run=false&replace=true",
                                            {"format": "argus-account-snapshot", "version": 1, "tables": {}}),
        ("POST", "/api/import/investing"): ("POST", "/api/import/investing", {
            "filename": "x.csv", "portfolio": "bot-import", "opening_through": "2026-01-02",
            "content": (FIXTURES / "sample_Holdings_01152026.csv").read_text(encoding="utf-8-sig")}),
    }
    streamed = {("GET", "/api/stream")}  # see test_the_live_stream_is_per_account
    listed = NOT_PER_ACCOUNT | set(denied) | set(own) | streamed
    assert _api_routes(c.app) == listed, "list every new /api route in this test (per account or not)"

    for route, calls in denied.items():
        for method, path, body in calls:
            r = c.request(method, path, json=body)
            assert r.status_code in DENIED and _clean(r.text, MINE_IN_REFUSAL), (route, path, r.status_code, r.text[:200])
    for route, (method, path, body) in own.items():
        r = c.request(method, path, json=body)
        assert _clean(r.text), (route, r.text[:300])
    # Importing into my portfolio's name makes the bot its own (names are per account).
    imp = own[("POST", "/api/import/investing")]
    assert c.post(imp[1], json=imp[2] | {"portfolio": "growth"}).json()["creates_portfolio"]
    # The peers and DCF model I saved are untouched by the bot resetting its own.
    with session_scope(argus.engine) as s:
        assert s.get(PeerList, (two["me"], "AAA")).peers == ["BBB"]
        assert s.get(ValuationModel, (two["me"], "AAA")) is not None
    with access.acting_as(two["me"]):
        assert argus.portfolios.list_transactions("growth")[0]["qty"] == 10
        assert argus.alerts.list()[0]["active"] and argus.notes.list()[0]["text"] == "my thesis"
        assert argus.targets("growth", "symbol") == {"AAA": 100}


def test_shared_portfolio_reads_work_and_writes_are_refused_over_http(leak):
    c, argus, two = leak
    with access.acting_as(two["me"]):
        argus.portfolios.share("growth", "bot")
    pid = two["pid"]
    assert c.get(f"/api/portfolios/{pid}").json()["totals"]["position_count"] == 1
    assert c.get("/api/portfolios").json()[0]["owner"] == "me"
    r = c.post(f"/api/portfolios/{pid}/transactions", json={"type": "BUY", "symbol": "AAA", "qty": 1, "price": 1})
    assert r.status_code == 403 and r.json()["error"]["code"] == "READ_ONLY"
    assert c.delete(f"/api/transactions/{two['txn']}").status_code == 403
    assert c.put(f"/api/portfolios/{pid}/shares/bot").status_code == 403


def test_the_live_stream_is_per_account(argus, two):
    """Over a real server: the test client can't read an endless event stream."""
    import socket
    import threading
    import time

    import httpx
    import uvicorn

    key = argus.accounts.create_key("bot", "stream")["key"]
    app = create_app(argus, start_hub=False)
    from argus.providers.base import Quote

    hub = app.state.hub
    hub.fired_alerts = [{"alert_id": two["alert"], "account_id": two["me"], "message": "AAA: mine fired"}]
    hub.quotes = {s: Quote(s, 10, 9, None, None, None, datetime.now(UTC), "fake") for s in ("AAA", "BBB", "SPY")}
    with access.acting_as(two["bot"]):
        argus.watchlists.add(["BBB"])
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        for _ in range(100):
            if server.started:
                break
            time.sleep(0.05)
        with httpx.stream("GET", f"http://127.0.0.1:{port}/api/stream?portfolio=growth", timeout=10,
                          headers={"Authorization": f"Bearer {key}"}) as r:
            line = next(x for x in r.iter_lines() if x.startswith("data:"))
    finally:
        server.should_exit = True
        thread.join(5)
    data = json.loads(line[5:])
    assert data["alerts_fired"] == [] and "portfolio" not in data
    assert data["portfolio_error"]["code"] == "NOT_FOUND"
    assert set(data["quotes"]) == {"BBB"}  # its own watchlist; not what I hold (AAA) or benchmark (SPY)


MCP_NOT_PER_ACCOUNT = {"market_status", "get_quotes", "get_price_history", "get_fund_holdings", "get_fundamentals",
                       "get_financials", "compare_symbols", "search_symbol", "get_research", "get_market_context",
                       "screen_stocks"}


def _tool(mcp, name, args):
    from mcp.server.mcpserver.exceptions import ToolError

    try:
        res = asyncio.run(mcp.call_tool(name, args))
    except ToolError as e:
        return str(e)
    return res.content[0].text


def test_every_mcp_tool_refuses_or_hides_another_accounts_records(argus, two):
    mcp = create_mcp(argus)
    pid, txn = two["pid"], two["txn"]
    sim = [{"symbol": "AAA", "side": "SELL", "qty": 1}]
    denied = {"get_portfolio": [{"portfolio": "growth"}, {"portfolio": str(pid)}],
              "get_performance": [{"portfolio": "growth"}],
              "list_transactions": [{"portfolio": "growth"}],
              "get_daily_brief_data": [{"portfolio": "growth", "include_news": False}],
              "get_events": [{"portfolio": "growth"}],
              "get_risk": [{"portfolio": "growth"}],
              "get_dividends": [{"portfolio": "growth"}],
              "get_exposure": [{"portfolio": "growth"}],
              "get_drift": [{"portfolio": "growth"}],
              "simulate_trades": [{"portfolio": "growth", "trades": sim}],
              "add_transaction": [{"portfolio": "growth", "type": "BUY", "symbol": "AAA", "qty": 1, "price": 1,
                                   "dry_run": False}],
              "edit_transaction": [{"txn_id": txn, "qty": 1, "dry_run": False}],
              "delete_transaction": [{"txn_id": txn, "dry_run": False}],
              "watchlist_remove": [{"symbols": ["BBB"], "name": "Tech"}],
              "disable_alert": [{"alert_id": two["alert"]}],
              "update_note": [{"note_id": two["note"], "text": "x"}],
              "set_targets": [{"portfolio": "growth", "level": "symbol", "weights": {"AAA": 1}, "dry_run": False}],
              "share_portfolio": [{"portfolio": "growth", "username": "bot"}]}
    own = {"list_portfolios": {}, "get_watchlist": {"name": "Watchlist"}, "list_alerts": {"include_inactive": True,
           "fired_since": "2000-01-01"}, "list_notes": {"include_archived": True}, "get_company_profile": {"symbol": "AAA"},
           "watchlist_add": {"symbols": ["AAA"]}, "set_alert": {"symbol": "AAA", "kind": "price_above", "threshold": 1},
           "add_note": {"symbol": "AAA", "text": "bot"}, "create_portfolio": {"name": "bot-sim"}}
    tools = {t.name for t in asyncio.run(mcp.list_tools())}
    assert tools == MCP_NOT_PER_ACCOUNT | set(denied) | set(own), "list every new MCP tool in this test"

    with access.acting_as(two["bot"]):
        for name, calls in denied.items():
            for args in calls:
                out = _tool(mcp, name, args)
                assert "NOT_FOUND" in out and _clean(out, MINE_IN_REFUSAL), (name, out[:200])
        for name, args in own.items():
            out = _tool(mcp, name, args)
            assert _clean(out), (name, out[:300])
        with pytest.raises(Exception) as e:
            asyncio.run(mcp.read_resource("portfolio://growth/summary"))
        cause = e.value
        while cause is not None and not isinstance(cause, ArgusError):
            cause = cause.__cause__ or cause.__context__
        assert cause is not None and cause.code == "NOT_FOUND"
    with access.acting_as(two["me"]):
        assert argus.portfolios.list_transactions("growth")[0]["qty"] == 10


def test_http_mcp_acts_as_whoever_signed_in_each_request(argus, two):
    with access.acting_as(two["me"]):
        mine = argus.accounts.create_key("me", "mcp")["key"]
    bots = argus.accounts.create_key("bot", "mcp")["key"]
    headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}

    def rpc(c, key, method, params, sid=None):
        h = headers | {"Authorization": f"Bearer {key}"} | ({"mcp-session-id": sid} if sid else {})
        r = c.post("/mcp/", headers=h, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
        body = r.text
        if r.headers.get("content-type", "").startswith("text/event-stream"):
            body = [x[5:] for x in body.splitlines() if x.startswith("data:")][-1]
        return r.headers.get("mcp-session-id"), json.loads(body)

    def portfolios(c, key, sid):
        _, out = rpc(c, key, "tools/call", {"name": "list_portfolios", "arguments": {}}, sid)
        return [p["name"] for p in json.loads(out["result"]["content"][0]["text"])]

    init = {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}}
    with TestClient(create_app(argus, start_hub=False), base_url="http://localhost:8787") as c:
        sid, _ = rpc(c, mine, "initialize", init)
        assert portfolios(c, mine, sid) == ["growth"]
        assert portfolios(c, bots, sid) == []  # my MCP session id gets the bot nothing of mine
