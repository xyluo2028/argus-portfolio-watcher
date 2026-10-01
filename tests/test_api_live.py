import asyncio
import json
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from argus.api.server import create_app
from argus.live import LiveHub
from tests.conftest import FakeQuotes


@pytest.fixture
def client(make_argus):
    a = make_argus([FakeQuotes("fake", {"AAA": (110, 100), "SPY": (500, 495)})])
    a.portfolios.create_portfolio("growth")
    app = create_app(a, start_hub=False)
    with TestClient(app, base_url="http://localhost") as c:
        yield c


def test_transaction_roundtrip_and_portfolio(client):
    r = client.post("/api/portfolios/growth/transactions",
                    json={"type": "BUY", "symbol": "aaa", "qty": 10, "price": 90, "date": "2026-09-01"})
    assert r.status_code == 200 and r.json()["inserted_ids"]
    p = client.get("/api/portfolios/growth").json()
    assert p["totals"]["market_value"] == 1100 and p["positions"][0]["unrealized_pnl"] == 200
    assert client.get("/api/portfolios/growth/transactions").json()[0]["source"] == "ui"


def test_errors_map_to_http_status(client):
    r = client.get("/api/portfolios/nope")
    assert r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND"
    r = client.post("/api/portfolios/growth/transactions", json={"type": "SELL", "symbol": "AAA", "qty": 1, "price": 1})
    assert r.status_code == 400 and r.json()["error"]["code"] == "INSUFFICIENT_SHARES"


def test_ws_trade_updates_quote_and_keeps_prev_close(make_argus):
    a = make_argus()
    hub = LiveHub(a)
    t0 = datetime(2026, 9, 28, 14, 0, tzinfo=UTC)
    from argus.providers.base import Quote
    hub.quotes["AAA"] = Quote("AAA", 100, 98, 99, 101, 97, t0, "finnhub")
    hub.status = {"session": "regular"}
    msg = {"type": "trade", "data": [
        {"s": "AAA", "p": 102.5, "t": int(t0.timestamp() * 1000) + 1000, "v": 10},
        {"s": "AAA", "p": 102.0, "t": int(t0.timestamp() * 1000) + 500, "v": 5},   # older print, same batch
    ]}
    asyncio.run(hub._on_ws_message(json.dumps(msg)))
    q = hub.quotes["AAA"]
    assert (q.price, q.prev_close, q.high, q.source) == (102.5, 98, 102.5, "finnhub-ws")
    assert hub.version == 1 and hub._dirty == {"AAA"}
    hub.apply_trade("AAA", 50, t0)  # stale print is ignored
    assert hub.quotes["AAA"].price == 102.5


def test_tracked_symbols_orders_by_value_and_adds_benchmark(make_argus):
    from argus.services.portfolio import TxnInput
    a = make_argus()
    a.portfolios.create_portfolio("p")
    a.portfolios.add_transactions("p", [
        TxnInput("BUY", "SMALL", datetime(2026, 9, 1, tzinfo=UTC), 1, 10),
        TxnInput("BUY", "BIG", datetime(2026, 9, 1, tzinfo=UTC), 1, 1000),
    ])
    assert LiveHub(a).tracked_symbols() == ["BIG", "SMALL", "SPY"]


def test_watchlist_endpoints(client):
    assert client.post("/api/watchlists/Watchlist", json={"symbols": ["aaa"], "note": "idea"}).json()["added"] == ["AAA"]
    items = client.get("/api/watchlists/Watchlist").json()["items"]
    assert items[0]["symbol"] == "AAA" and items[0]["quote"]["price"] == 110
    assert client.delete("/api/watchlists/Watchlist/AAA").json()["removed"] == ["AAA"]
    assert client.get("/api/compare?symbols=AAA,SPY&fields=pe_ttm").json()["rows"][1]["symbol"] == "SPY"


def test_rejects_foreign_host_header(client):
    assert client.get("/api/portfolios", headers={"host": "evil.example"}).status_code == 400
    assert client.get("/api/portfolios", headers={"host": "localhost:8787"}).status_code == 200


def test_edit_transaction_endpoint_and_all_view_listing(client):
    r = client.post("/api/portfolios/growth/transactions",
                    json={"type": "BUY", "symbol": "AAA", "qty": 10, "price": 90, "date": "2026-09-01"})
    txn_id = r.json()["inserted_ids"][0]
    preview = client.patch(f"/api/transactions/{txn_id}", json={"price": 80, "dry_run": True}).json()
    assert preview["position"]["after"]["avg_cost"] == 80 and "after" not in preview
    saved = client.patch(f"/api/transactions/{txn_id}", json={"qty": 12, "date": "2026-09-02"}).json()
    assert saved["after"]["qty"] == 12 and saved["after"]["ts"].startswith("2026-09-02")
    rows = client.get("/api/portfolios/all/transactions?symbol=aaa").json()
    assert [(r["qty"], r["portfolio"]) for r in rows] == [(12, "growth")]
    assert client.patch(f"/api/transactions/{txn_id}", json={"qty": 1}).status_code == 404  # replaced row


def test_snapshot_download_and_restore(client):
    client.post("/api/portfolios/growth/transactions",
                json={"type": "BUY", "symbol": "AAA", "qty": 10, "price": 90, "date": "2026-09-01"})
    r = client.get("/api/snapshot")
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    doc = r.json()
    preview = client.post("/api/snapshot/restore", json=doc).json()  # dry run by default
    assert preview["dry_run"] and preview["will_remove"] == {"portfolio": 1, "txn": 1}
    assert client.post("/api/snapshot/restore?dry_run=false", json=doc).status_code == 409
    done = client.post("/api/snapshot/restore?dry_run=false&replace=true", json=doc).json()
    assert done["backup"].endswith(".json")
    assert client.get("/api/portfolios/growth").json()["totals"]["position_count"] == 1
    assert client.post("/api/snapshot/restore", json={"nope": 1}).status_code == 400


def test_import_investing_upload(make_argus):
    from tests.conftest import FIXTURES

    a = make_argus([FakeQuotes("fake", {"AAPL": (200, 198), "KO": (62, 61), "SPY": (510, 505)})])
    body = {"filename": "C:\\Users\\me\\sample_Holdings_01152026.csv",
            "content": (FIXTURES / "sample_Holdings_01152026.csv").read_text(encoding="utf-8-sig"),
            "opening_through": "2026-01-02"}
    with TestClient(create_app(a, start_hub=False), base_url="http://localhost") as c:
        dry = c.post("/api/import/investing", json=body).json()
        assert dry["portfolio"] == "sample" and dry["status"] == "ok" and dry["dry_run"]
        assert a.portfolios.list_portfolios() == []
        assert c.post("/api/import/investing", json=body | {"dry_run": False}).json()["inserted"] == 5
        again = c.post("/api/import/investing", json=body | {"dry_run": False, "portfolio": "sample"}).json()
        assert again["skipped_existing"] == 5
        bad = c.post("/api/import/investing", json=body | {"opening_through": "Jan 2"})
        assert bad.status_code == 400
