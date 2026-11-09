from datetime import UTC, datetime

import pytest

from argus.errors import ArgusError
from argus.services.analysis import concentration, drift, exposure
from argus.services.portfolio import TxnInput
from tests.conftest import FakeQuotes

ROWS = [
    {"symbol": "NVDA", "sector": "Technology", "type": "Common Stock", "market_value": 600.0},
    {"symbol": "XOM", "sector": "Energy", "type": "Common Stock", "market_value": 200.0},
    {"symbol": "VONG", "sector": "ETF", "type": "ETP", "market_value": 200.0},
]
PROFILES = {"VONG": {"sectors": {"Technology": 0.5, "Healthcare": 0.25},  # 25% not classified
                     "top_holdings": [{"symbol": "NVDA", "name": "NVIDIA", "weight": 0.1}]}}


def test_exposure_direct_lookthrough_and_top_stock():
    e = exposure(ROWS, PROFILES)
    direct = {r["key"]: r["weight_pct"] for r in e["by_sector_direct"]}
    look = {r["key"]: r["weight_pct"] for r in e["by_sector_lookthrough"]}
    assert direct == {"Technology": 60, "Energy": 20, "ETF": 20}
    assert look == pytest.approx({"Technology": 70, "Energy": 20, "Healthcare": 5, "Unclassified": 5})
    nvda = e["top_stock_exposure"][0]
    assert (nvda["symbol"], nvda["direct"], nvda["via_etfs"], nvda["via"]) == ("NVDA", 600, 20, ["VONG"])
    assert {r["key"]: r["weight_pct"] for r in e["by_type"]} == {"Stock": 80, "ETF": 20}


def test_concentration():
    c = concentration([50, 30, 20])
    assert c["top1_pct"] == 50 and c["hhi"] == pytest.approx(0.38) and c["effective_positions"] == pytest.approx(2.63, abs=0.01)


def test_drift_rows_trades_and_warnings():
    d = drift(ROWS, {"NVDA": 50, "XOM": 30, "TSLA": 10}, "symbol", tolerance_pp=2)
    rows = {r["key"]: r for r in d["rows"]}
    assert rows["NVDA"]["drift_pp"] == pytest.approx(10) and rows["NVDA"]["trade_to_target"] == pytest.approx(-100)
    assert rows["TSLA"]["trade_to_target"] == pytest.approx(100) and rows["TSLA"]["value"] == 0
    assert rows["VONG"]["target_pct"] is None and d["untargeted_pct"] == pytest.approx(20)
    assert d["warnings"] == ["targets sum to 90.0%, not 100%"]
    assert drift(ROWS, {"Technology": 60, "Energy": 20, "ETF": 20}, "sector")["warnings"] == []


@pytest.fixture
def argus(make_argus):
    a = make_argus([FakeQuotes("fake", {"AAA": (110, 100), "BBB": (50, 50)})])
    a.portfolios.create_portfolio("p")
    a.portfolios.add_transactions("p", [TxnInput("BUY", "AAA", datetime(2026, 9, 1, 20, tzinfo=UTC), 10, 100),
                                        TxnInput("BUY", "BBB", datetime(2026, 9, 1, 20, tzinfo=UTC), 20, 50)])
    return a


def test_simulate_trades_does_not_save(argus):
    sim = argus.simulate_trades("p", [{"symbol": "AAA", "side": "SELL", "qty": 5}, {"symbol": "BBB", "side": "BUY", "amount": 550}])
    assert sim["net_cash"] == pytest.approx(0)  # sell 5 x 110 funds the 550 buy
    assert sim["realized_pnl_from_trades"] == pytest.approx(50)
    changed = {c["symbol"]: c for c in sim["positions_changed"]}
    assert changed["AAA"]["qty_after"] == 5 and changed["BBB"]["qty_after"] == 31
    assert len(argus.portfolios.list_transactions("p")) == 2 and sim["saved"] is False


def test_simulate_oversell_is_rejected(argus):
    with pytest.raises(ArgusError):
        argus.simulate_trades("p", [{"symbol": "AAA", "side": "SELL", "qty": 11}])


@pytest.mark.parametrize("trade", [{"symbol": "AAA", "type": "SELL", "qty": 5},
                                   {"symbol": "AAA", "type": "sell", "qty": 5},
                                   {"symbol": "AAA", "side": " Sell ", "qty": 5},
                                   {"symbol": "AAA", "side": "SELL", "type": "sell", "qty": 5}])
def test_simulate_sell_via_side_or_type(argus, trade):
    # B-147: `type` (the transactions field name) used to be ignored and the sell became a buy.
    sim = argus.simulate_trades("p", [trade])
    assert sim["trades"][0]["side"] == "SELL" and sim["net_cash"] == pytest.approx(550)
    assert sim["positions_changed"][0]["qty_after"] == 5


@pytest.mark.parametrize(("trade", "msg"), [
    ({"symbol": "AAA", "qty": 5}, "give side (or type)"),
    ({"symbol": "AAA", "side": "SHORT", "qty": 5}, "not 'SHORT'"),
    ({"symbol": "AAA", "type": "DIVIDEND", "qty": 5}, "not 'DIVIDEND'"),
    ({"symbol": "AAA", "side": "BUY", "type": "SELL", "qty": 5}, "disagree"),
    ({"side": "BUY", "qty": 5}, "give a symbol"),
])
def test_simulate_rejects_missing_or_unknown_side(argus, trade, msg):
    with pytest.raises(ArgusError) as e:
        argus.simulate_trades("p", [{"symbol": "BBB", "side": "BUY", "qty": 1}, trade])
    assert e.value.code == "INVALID_ARG" and e.value.message.startswith("Trade 2") and msg in e.value.message
    if trade.get("symbol"):
        assert "(AAA)" in e.value.message


def test_set_targets_preview_then_save(argus):
    prev = argus.set_targets("p", "symbol", {"aaa": 60, "BBB": 40})
    assert prev["dry_run"] is True and argus.targets("p", "symbol") == {}
    argus.set_targets("p", "symbol", {"AAA": 60, "BBB": 40}, dry_run=False)
    d = argus.drift("p", "symbol")
    rows = {r["key"]: r for r in d["rows"]}
    assert rows["AAA"]["weight_pct"] == pytest.approx(1100 / 2100 * 100) and rows["AAA"]["target_pct"] == 60
    with pytest.raises(ArgusError):
        argus.set_targets("p", "sector", {"Tech": 120})
