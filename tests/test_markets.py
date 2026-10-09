from datetime import date, timedelta

import pytest

from argus.providers.macro import MacroProvider
from argus.services import market_context as mc


def _series(start, n, step):
    return {start + timedelta(days=i): 100.0 + step * i for i in range(n)}


def test_period_returns():
    c = _series(date(2025, 10, 1), 400, 0.1)
    last_d = max(c)
    r = mc.period_returns(c)
    assert r["1D"] == pytest.approx((c[last_d] / c[last_d - timedelta(days=1)] - 1) * 100)
    assert r["YTD"] == pytest.approx((c[last_d] / c[date(2025, 12, 31)] - 1) * 100)
    assert mc.period_returns({date(2026, 1, 2): 1.0})["1M"] is None


def test_build_breadth_and_calendar_filter():
    up, down = _series(date(2025, 6, 1), 400, 0.1), _series(date(2025, 6, 1), 400, -0.1)
    closes = {s: (up if s in ("XLK", "SPY") else down) for s in mc.ALL_SYMBOLS}
    events = [
        {"date": "2026-10-15", "time_et": "08:30", "event": "CPI", "consensus": None, "previous": "0.4%", "actual": None},
        {"date": "2026-10-15", "time_et": "08:30", "event": "CPI", "consensus": None, "previous": "0.4%", "actual": None},  # dup
        {"date": "2026-10-15", "time_et": "08:30", "event": "CPI Index, s.a", "consensus": None, "previous": "334", "actual": None},
        {"date": "2026-10-14", "time_et": "06:00", "event": "NFIB Small Business Optimism", "consensus": None, "previous": None, "actual": None},
        {"date": "2026-10-14", "time_et": "13:00", "event": "FOMC Member Barkin Speaks", "consensus": None, "previous": None, "actual": None},
        {"date": "2026-10-20", "time_et": "10:00", "event": "Fed Chair Powell Speaks", "consensus": None, "previous": None, "actual": None},
    ]
    fomc = [{"date": "2026-09-16", "days": "15-16", "month": "September", "projections": True},
            {"date": "2026-10-28", "days": "27-28", "month": "October", "projections": False}]
    out = mc.build(closes, None, fomc, events, date(2026, 10, 9))
    b = out["breadth"]
    assert b["sectors_above_50d"] == 1 and b["sectors_above_200d"] == 1 and b["sectors"] == 11
    assert b["equal_vs_cap"]["1M"] < 0  # RSP fell while SPY rose
    assert [e["event"] for e in out["calendar"]["events"]] == ["CPI", "Fed Chair Powell Speaks"]
    assert [f["date"] for f in out["calendar"]["fomc"]] == ["2026-10-28"]


FED_HTML = """
<h4>2026 FOMC Meetings</h4>
<div class="fomc-meeting__month"><strong>January</strong></div><div class="fomc-meeting__date">27-28</div>
<div class="fomc-meeting__month"><strong>March</strong></div><div class="fomc-meeting__date">17-18*</div>
<div class="fomc-meeting__month"><strong>Apr/May</strong></div><div class="fomc-meeting__date">30-1</div>
<div class="fomc-meeting__month"><strong>Dec/Jan</strong></div><div class="fomc-meeting__date">31-1</div>
<h4>2025 FOMC Meetings</h4>
<div class="fomc-meeting__month"><strong>June</strong></div><div class="fomc-meeting__date">17-18</div>
"""


def test_fomc_parsing(monkeypatch):
    class Resp:
        text = FED_HTML

    p = MacroProvider(client=type("C", (), {"get": lambda self, url, **kw: Resp()})())
    monkeypatch.setattr("argus.providers.macro.date", type("D", (date,), {"today": classmethod(lambda cls: date(2026, 1, 5))}))
    m = p.fomc_meetings()
    assert [(x["date"], x["projections"]) for x in m] == [("2026-01-28", False), ("2026-03-18", True), ("2026-05-01", False),
                                                          ("2027-01-01", False)]
