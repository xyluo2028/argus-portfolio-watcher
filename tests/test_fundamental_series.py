"""Valuation ratios and revenue for the price chart's panes."""

from datetime import UTC, date, datetime, timedelta

import pytest

from argus.errors import ArgusError
from argus.providers.base import Bar
from tests.test_speed import PerSymbolHistory


def _bars(start: date, closes: list[float]) -> list[Bar]:
    out, d = [], start
    for c in closes:
        while d.weekday() >= 5:
            d += timedelta(days=1)
        out.append(Bar(datetime(d.year, d.month, d.day, 21, tzinfo=UTC), c, c, c, c, 1))
        d += timedelta(days=1)
    return out


class Directory:
    def __init__(self, series):
        self.series = series

    def ratio_series(self, symbol):
        return self.series


@pytest.fixture
def a(make_argus):
    today = date.today()
    start = today - timedelta(days=300)
    bars = _bars(start, [100.0 + i * 0.5 for i in range(220)])
    a = make_argus(history=PerSymbolHistory({"AAA": bars}))
    q1, q2 = bars[40].ts.date(), bars[120].ts.date()  # two quarter ends inside the chart
    a.market.directory = Directory({
        # P/E 20 at q1 (EPS TTM = close/20), 25 at q2; P/S negative-free; P/E on losses later
        "peTTM": [{"period": q2.isoformat(), "v": 25.0}, {"period": q1.isoformat(), "v": 20.0}],
        "psTTM": [{"period": q1.isoformat(), "v": 4.0}],
        "pb": [{"period": q1.isoformat(), "v": -3.0}],  # negative book: meaningless
    })
    a._q = (q1, q2, {b.ts.date(): b.c for b in bars})
    return a


def test_ratios_track_the_daily_price_and_equal_finnhub_at_quarter_ends(a):
    q1, q2, close = a._q
    r = a.fundamental_series("AAA", "1y")
    pe = dict(r["ratios"]["pe_ttm"])
    assert pe[q1.isoformat()] == 20.0 and pe[q2.isoformat()] == 25.0  # exactly Finnhub's on its dates
    later = next(d for d in sorted(close) if d > q1 + timedelta(days=10) and d < q2)
    assert pe[later.isoformat()] == pytest.approx(close[later] / (close[q1] / 20.0), abs=0.01)  # moves with price
    first = min(close)
    assert pe[first.isoformat()] is None  # before the first quarter: nothing to divide by
    assert "pb" not in r["ratios"]  # negative book value: no ratio at all
    assert r["medians"]["pe_ttm"] == 22.5 and r["labels"]["ev_ebitda"] == "EV/EBITDA"


def test_a_quarter_stops_carrying_forward_once_stale(a, make_argus):
    q1, _, close = a._q
    a.FUND_SERIES_STALE_DAYS = 30
    ps = dict(a.fundamental_series("AAA", "1y")["ratios"]["ps_ttm"])
    assert ps[q1.isoformat()] == 4.0 and ps[max(close).isoformat()] is None


def test_revenue_comes_with_year_over_year_change(a):
    class Sec:
        def get_financials(self, symbol, period, limit):
            return {"periods": [{"period_end": "2026-06-30", "revenue": 150.0}, {"period_end": "2025-06-30", "revenue": 100.0},
                                {"period_end": "2026-03-31", "revenue": 140.0}]}

    a.market.sec = Sec()
    a.settings = a.settings.__class__(**{**a.settings.__dict__, "sec_user_agent": "test test@example.com"})
    a.market.settings = a.settings
    rev = a.fundamental_series("AAA", "1y")["revenue"]
    assert [(x["period_end"], x["yoy_pct"]) for x in rev] == [("2025-06-30", None), ("2026-03-31", None),
                                                              ("2026-06-30", pytest.approx(50.0))]


def test_intraday_ranges_are_refused(a):
    with pytest.raises(ArgusError):
        a.fundamental_series("AAA", "5d")
