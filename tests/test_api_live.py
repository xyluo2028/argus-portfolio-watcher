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
    with TestClient(app) as c:
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
