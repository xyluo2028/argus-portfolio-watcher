from dataclasses import dataclass
from datetime import UTC, date, datetime

import pytest

from argus.services.performance import compute_series, summarize


@dataclass
class T:
    id: int
    type: str
    symbol: str
    ts: datetime
    qty: float = 0.0
    price: float = 0.0
    fee: float = 0.0
    amount: float = 0.0


D = [date(2026, 9, d) for d in (21, 22, 23, 24, 25)]


def at(d: date, hour=20):  # 16:00 ET
    return datetime(d.year, d.month, d.day, hour, tzinfo=UTC)


def test_opening_lot_enters_at_market_value_not_cost():
    closes = {"X": {D[0]: 200, D[1]: 210}}
    pts = compute_series([T(1, "OPENING", "X", at(D[0]), 10, 50)], D[:2], closes)
    assert pts[0].ret == pytest.approx(0)          # no fake gain from the $50 cost
    assert pts[1].ret == pytest.approx(0.05)
    assert pts[1].index == pytest.approx(1.05)


def test_buy_in_middle_is_a_flow_not_performance():
    closes = {"X": {D[0]: 100, D[1]: 100, D[2]: 110}}
    txns = [T(1, "BUY", "X", at(D[0]), 10, 100), T(2, "BUY", "X", at(D[1]), 10, 100)]
    pts = compute_series(txns, D[:3], closes)
    assert [round(p.ret, 6) for p in pts] == [0, 0, 0.1]
    assert pts[-1].value == 2200


def test_buy_below_close_counts_the_same_day_gain():
    pts = compute_series([T(1, "BUY", "X", at(D[0]), 10, 90)], D[:1], {"X": {D[0]: 99}})
    assert pts[0].ret == pytest.approx(0.1)


def test_sell_proceeds_leave_the_portfolio():
    closes = {"X": {D[0]: 100, D[1]: 120}}
    txns = [T(1, "BUY", "X", at(D[0]), 10, 100), T(2, "SELL", "X", at(D[1]), 5, 120)]
    pts = compute_series(txns, D[:2], closes)
    assert pts[1].value == 600
    assert pts[1].ret == pytest.approx(0.2)  # (600 + 600 proceeds) / 1000 - 1


def test_dividend_counts_as_return():
    closes = {"X": {D[0]: 100, D[1]: 100}}
    txns = [T(1, "BUY", "X", at(D[0]), 10, 100), T(2, "DIVIDEND", "X", at(D[1]), amount=10)]
    assert compute_series(txns, D[:2], closes)[1].ret == pytest.approx(0.01)


def test_split_adjusted_closes_with_recorded_split():
    # Yahoo closes are split-adjusted backwards: a 4:1 split on D[2] shows 25 before and after.
    closes = {"X": {D[0]: 25, D[1]: 25, D[2]: 25}}
    txns = [T(1, "BUY", "X", at(D[0]), 10, 100), T(2, "SPLIT", "X", at(D[2], 13), qty=4)]
    pts = compute_series(txns, D[:3], closes)
    assert [round(p.value) for p in pts] == [1000, 1000, 1000]
    assert all(abs(p.ret) < 1e-9 for p in pts)


def test_weekend_trade_maps_to_next_session_and_benchmark_rebased():
    closes = {"X": {D[0]: 100, D[1]: 100}}
    pts = compute_series([T(1, "BUY", "X", datetime(2026, 9, 20, 15, tzinfo=UTC), 1, 100)], D[:2], closes,
                         bench={D[0]: 500, D[1]: 505})
    assert pts[0].d == D[0] and pts[0].bench_index == 1.0 and pts[1].bench_index == pytest.approx(1.01)


def test_summary_stats():
    closes = {"X": {D[0]: 100, D[1]: 110, D[2]: 99, D[3]: 108.9, D[4]: 108.9}}
    pts = compute_series([T(1, "BUY", "X", at(D[0]), 1, 100)], D, closes, bench={d: 100 + i for i, d in enumerate(D)})
    s = summarize(pts)
    assert s["twr_pct"] == pytest.approx(8.9)
    assert s["max_drawdown_pct"] == pytest.approx(-10)
    assert s["benchmark_pct"] == pytest.approx(4)
    assert s["excess_pct"] == pytest.approx(4.9)
    assert s["volatility_pct"] > 0 and s["cagr_pct"] is None
    assert s["gain"] == pytest.approx(8.9)
