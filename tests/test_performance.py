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
    assert s["cagr_pct"] is None
    assert s["gain"] == pytest.approx(8.9)


def test_volatility_and_sharpe_withheld_on_a_short_series():
    # 4 daily returns: annualizing them gives a meaningless Sharpe, so both are null with a reason.
    closes = {"X": {D[0]: 100, D[1]: 110, D[2]: 99, D[3]: 108.9, D[4]: 108.9}}
    s = summarize(compute_series([T(1, "BUY", "X", at(D[0]), 1, 100)], D, closes))
    assert s["volatility_pct"] is None and s["sharpe"] is None
    assert s["risk_sessions"] == 4
    assert s["risk_note"] == "needs 20 sessions, has 4"


def test_volatility_and_sharpe_from_20_sessions():
    days = [date.fromordinal(date(2026, 8, 3).toordinal() + i) for i in range(21)]
    closes = {"X": {d: 100 * (1.01 if i % 2 else 1.0) * (1 + i / 1000) for i, d in enumerate(days)}}
    s = summarize(compute_series([T(1, "BUY", "X", at(days[0]), 1, 100)], days, closes))
    assert s["risk_sessions"] == 20 and s["risk_note"] is None
    assert s["volatility_pct"] > 0 and s["sharpe"] is not None
    # One session fewer and they're withheld again.
    assert summarize(compute_series([T(1, "BUY", "X", at(days[0]), 1, 100)], days[:20], closes))["sharpe"] is None


def test_summary_on_day_one_counts_the_purchase_as_invested():
    # Bought today at 100 + 1 fee, closed at 99: the slice starts before the buy.
    pts = compute_series([T(1, "BUY", "X", at(D[0]), 10, 100, fee=1)], D[:1], {"X": {D[0]: 99}})
    s = summarize(pts, inception=True)
    assert s["start_value"] == 0 and s["end_value"] == pytest.approx(990)
    assert s["net_invested"] == pytest.approx(1001)
    assert s["gain"] == pytest.approx(-11)  # = unrealized P&L
    assert s["twr_pct"] == pytest.approx((990 / 1001 - 1) * 100)


def test_summary_of_a_later_slice_starts_at_its_first_close():
    closes = {"X": {D[0]: 99, D[1]: 108.9}}
    pts = compute_series([T(1, "BUY", "X", at(D[0]), 10, 100)], D[:2], closes)
    s = summarize(pts[1:])
    assert s["start_value"] == pytest.approx(1089) and s["net_invested"] == 0 and s["gain"] == 0
    s = summarize(pts)
    assert s["start_value"] == pytest.approx(990) and s["gain"] == pytest.approx(99)
    assert s["twr_pct"] == pytest.approx(10)


def test_dividend_on_its_ex_date_offsets_the_price_drop():
    # Price-only closes fall by the dividend on the ex-date; as income that day nets to zero.
    closes = {"X": {D[0]: 100, D[1]: 99}}
    txns = [T(1, "BUY", "X", at(D[0]), 10, 100), T(2, "DIVIDEND", "X", at(D[1], 4), amount=10)]
    pts = compute_series(txns, D[:2], closes)
    assert pts[1].ret == pytest.approx(0) and pts[1].flow_out == 10
    assert summarize(pts, inception=True)["gain"] == pytest.approx(0)


def test_after_close_buy_is_invested_from_the_next_session():
    # 22:15 ET on D[0] is after the close: the flow belongs to D[1] and D[0]'s return ignores it.
    closes = {"X": {D[0]: 100, D[1]: 110}}
    txns = [T(1, "OPENING", "X", at(D[0], 15), 10, 50), T(2, "BUY", "X", datetime(2026, 9, 22, 2, 15, tzinfo=UTC), 1, 101)]
    pts = compute_series(txns, D[:2], closes)
    assert pts[0].flow_in == pytest.approx(1000) and pts[0].value == pytest.approx(1000)
    assert pts[1].flow_in == pytest.approx(101)
    assert pts[1].ret == pytest.approx(11 * 110 / (1000 + 101) - 1)
