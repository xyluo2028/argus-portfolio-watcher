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


# Raw rows as Nasdaq serves them (checked Oct 2026): `?date=D` holds the day before D, clock at fixed UTC-4,
# except some dates that answer with their own day.
US = "United States"
NASDAQ_ROWS = {
    "2026-10-20": [{"gmt": "11:30", "country": US, "eventName": "3-Month Bill Auction"}],  # yesterday: dropped
    "2026-10-21": [{"gmt": "08:30", "country": US, "eventName": "Housing Starts", "actual": "1.221M"},
                   {"gmt": "02:00", "country": "United Kingdom", "eventName": "Claimant Count Change"}],
    "2026-10-26": [{"gmt": "08:30", "country": US, "eventName": "Chicago Fed National Activity"}],  # Monday's own
    "2026-10-27": [{"gmt": "10:00", "country": US, "eventName": "CB Consumer Confidence"}],  # still its own day...
    "2026-10-28": [{"gmt": "10:00", "country": US, "eventName": "CB Consumer Confidence", "actual": "95"}],  # ...repeated
    "2026-10-29": [{"gmt": "14:00", "country": US, "eventName": "Fed Interest Rate Decision", "actual": "&nbsp;"}],
    "2026-10-31": [{"gmt": "10:00", "country": US, "eventName": "Michigan Consumer Sentiment"},
                   {"gmt": "All Day", "country": US, "eventName": "Some Holiday"}],
    "2026-11-03": [{"gmt": "11:00", "country": US, "eventName": "ISM Manufacturing PMI"}],
    "2026-11-09": [{"gmt": "11:00", "country": US, "eventName": "Wholesale Inventories"}],  # Monday answering its own day
    "2026-11-10": [{"gmt": "11:00", "country": US, "eventName": "Wholesale Inventories"}],  # and the copy
    "2026-11-07": [{"gmt": "09:30", "country": US, "eventName": "Nonfarm Payrolls"},
                   {"gmt": "11:00", "country": US, "eventName": "Michigan Consumer Sentiment"}],
}


def test_economic_events_shift_nasdaq_dates_and_dst(monkeypatch):
    asked = []

    class Resp:
        def __init__(self, d):
            self.d = d

        def raise_for_status(self):
            pass

        def json(self):
            return {"data": {"rows": NASDAQ_ROWS.get(self.d, [])}}

    def get(self, url, params=None, **kw):
        asked.append(params["date"])
        return Resp(params["date"])

    p = MacroProvider(client=type("C", (), {"get": get})())
    monkeypatch.setattr("argus.providers.macro.date", type("D", (date,), {"today": classmethod(lambda cls: date(2026, 10, 20))}))
    ev = p.economic_events(20)
    assert min(asked) == "2026-10-20" and max(asked) == "2026-11-11"
    got = {(e["event"], e["date"]): e["time_et"] for e in ev}
    assert got == {
        ("Housing Starts", "2026-10-20"): "08:30",               # before DST ends: same clock, day before
        ("Chicago Fed National Activity", "2026-10-26"): "08:30",
        ("CB Consumer Confidence", "2026-10-27"): "10:00",       # once
        ("Fed Interest Rate Decision", "2026-10-28"): "14:00",   # the FOMC end date, not Thursday
        ("Michigan Consumer Sentiment", "2026-10-30"): "10:00",
        ("Some Holiday", "2026-10-30"): "All Day",
        ("ISM Manufacturing PMI", "2026-11-02"): "10:00",        # after DST ends: an hour earlier than listed
        ("Nonfarm Payrolls", "2026-11-06"): "08:30",
        ("Michigan Consumer Sentiment", "2026-11-06"): "10:00",
        ("Wholesale Inventories", "2026-11-09"): "10:00",         # once, on the Monday
    }
    assert all(date.fromisoformat(e["date"]).weekday() < 5 for e in ev)  # releases land on weekdays
    assert next(e for e in ev if e["event"] == "Housing Starts")["actual"] == "1.221M"


def _row(sym, price, prev, hi, lo, a50, a200, hi52, lo52):
    return {"symbol": sym, "regularMarketPrice": price, "regularMarketPreviousClose": prev, "regularMarketDayHigh": hi,
            "regularMarketDayLow": lo, "fiftyDayAverage": a50, "twoHundredDayAverage": a200,
            "fiftyTwoWeekHigh": hi52, "fiftyTwoWeekLow": lo52, "regularMarketTime": 1_792_440_000}


def test_stock_breadth_counts():
    rows = [
        _row("UP", 110, 100, 111, 101, 100, 90, 111, 60),    # up, above both, at its 52-week high
        _row("DN", 50, 55, 56, 49.99, 60, 70, 120, 50),       # down, below both, a hair from its 52-week low
        _row("FLAT", 20, 20, 21, 19, 19, None, 30, 10),       # unchanged, no 200-day average yet
        {"symbol": "BAD", "regularMarketPrice": None},          # no price: not counted
    ]
    s = mc.stock_breadth(rows)
    assert (s["count"], s["advancers"], s["decliners"], s["unchanged"]) == (3, 1, 1, 1)
    assert (s["above_50d"], s["below_50d"], s["above_200d"], s["below_200d"]) == (2, 1, 1, 1)
    assert s["pct_above_50d"] == pytest.approx(200 / 3) and s["pct_above_200d"] == 50
    assert (s["highs"], s["lows"], s["pct_new_highs"]) == (["UP"], ["DN"], pytest.approx(100 / 3))
    assert s["as_of"].startswith("2026-10")
    assert mc.stock_breadth([]) is None


def test_fear_greed_scores_and_labels():
    start = date(2024, 9, 1)
    days = [start + timedelta(days=i) for i in range(500)]
    rising = {d: 100 * 1.002 ** i for i, d in enumerate(days)}           # steady gains, then a jump
    rising[days[-1]] = rising[days[-2]] * 1.05
    calm = {d: 20.0 - (i == 499) * 6 for i, d in enumerate(days)}       # VIX drops on the last day
    flat = {d: 100.0 for d in days}
    closes = {"^GSPC": rising, "SPY": rising, "^VIX": calm, "^VIX3M": {d: 20.0 for d in days},
              "TLT": flat, "HYG": rising, "LQD": flat}
    stocks = {"count": 500, "new_highs": 30, "new_lows": 10, "pct_above_50d": 70.0}
    fg = mc.fear_greed(closes, stocks)
    by = {c["key"]: c for c in fg["components"]}
    assert set(by) == {"momentum", "strength", "breadth", "volatility", "term", "safe_haven", "junk"}
    assert by["momentum"]["score"] > 95 and by["volatility"]["score"] > 95 and by["term"]["score"] > 95
    assert by["strength"]["score"] == 75 and by["breadth"]["score"] == 70
    assert fg["score"] == pytest.approx(sum(c["score"] for c in fg["components"]) / 7, abs=0.1)
    assert fg["rating"] == "Extreme greed" and by["breadth"]["rating"] == "Greed"
    assert [mc.fg_label(v) for v in (0, 24.9, 25, 50, 60, 100)] == ["Extreme fear", "Extreme fear", "Fear", "Neutral", "Greed", "Extreme greed"]

    # Only history: the snapshot-based readings drop out, the rest still score.
    assert len(mc.fear_greed(closes, None)["components"]) == 5
    assert mc.fear_greed({}, None) is None


def test_market_context_counts_the_largest_stocks(make_argus, monkeypatch):
    a = make_argus()
    monkeypatch.setattr(a.screener, "largest", lambda n: ["AAA", "BBB"])
    seen = {}

    def quote_rows(symbols, fields):
        seen["symbols"], seen["fields"] = symbols, fields
        return [_row("AAA", 10, 9, 10, 9, 8, 7, 10, 5), _row("BBB", 10, 11, 11, 10, 12, 13, 20, 10)]

    monkeypatch.setattr(a.macro, "quote_rows", quote_rows)
    for name in ("closes", "treasury_curve", "fomc_meetings", "economic_events"):
        monkeypatch.setattr(a.macro, name, lambda *_a, **_k: None)
    out = a.market_context()
    assert seen["symbols"] == ["AAA", "BBB"] and "fiftyDayAverage" in seen["fields"]
    s = out["breadth"]["stocks"]
    assert (s["advancers"], s["decliners"], s["new_highs"], s["new_lows"]) == (1, 1, 1, 1)
    assert [c["key"] for c in out["fear_greed"]["components"]] == ["strength", "breadth"]

    monkeypatch.setattr(a.screener, "largest", lambda n: [])  # universe not built yet
    out = a.market_context()
    assert out["breadth"]["stocks"] is None and "screener" in out["errors"]["breadth"]


def test_breadth_universe_is_the_largest_listed_companies(tmp_path):
    from argus.services.screener import ScreenerService

    svc = ScreenerService(tmp_path, None, None)
    assert svc.largest(2) == []
    svc._mem = {"rows": [
        {"symbol": "SMALL", "market_cap": 1e9, "otc": False, "quote_type": "EQUITY"},
        {"symbol": "BIG", "market_cap": 9e11, "otc": False, "quote_type": "EQUITY"},
        {"symbol": "OTCX", "market_cap": 5e11, "otc": True, "quote_type": "EQUITY"},
        {"symbol": "FUND", "market_cap": 4e11, "otc": False, "quote_type": "ETF"},
        {"symbol": "MID", "market_cap": 2e10, "otc": False, "quote_type": "EQUITY"},
        {"symbol": "NOCAP", "market_cap": None, "otc": False, "quote_type": "EQUITY"},
    ]}
    assert svc.largest(2) == ["BIG", "MID"]
