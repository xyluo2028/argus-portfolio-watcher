from datetime import UTC, date, datetime, timedelta

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


def test_calendar_keeps_pce_price_index_eci_and_labels_gdp_report_prices():
    def ev(name, prev, day="2026-10-29"):
        return {"date": day, "time_et": "08:30", "event": name, "consensus": None, "previous": prev, "actual": None}
    events = [ev("Core PCE Price Index", "0.3%"), ev("Core PCE Price Index", "3.0%"), ev("PCE price index", "0.3%"),
              ev("PCE Price index", "3.4%"), ev("GDP Price Index", "6.1%"), ev("Employment Cost Index", "0.9%", "2026-10-30"),
              ev("Core PCE Prices", "3.30%"), ev("PCE Prices", "5.0%"), ev("GDP", "2.2%"),
              ev("CPI Index, s.a", "336.30"), ev("CPI Index, n.s.a.", "336.94"), ev("CPI, n.s.a", "0.59%"),
              ev("Cleveland CPI", "0.2%"), ev("House Price Index", "433.1"), ev("NAHB Housing Market Index", "29")]
    cal = mc.build({}, None, None, events, date(2026, 10, 29))["calendar"]
    shown = [e["event"] for e in cal["all_events"]]
    assert shown == ["Core PCE Price Index", "Core PCE Price Index", "PCE price index", "PCE Price index",
                     "GDP Price Index (QoQ ann.)", "Employment Cost Index", "Core PCE Prices (QoQ ann.)",
                     "PCE Prices (QoQ ann.)", "GDP"]
    assert cal["all_count"] == len(events)
    curated = [e["event"] for e in cal["events"]]
    assert curated.count("Core PCE Price Index") == 2 and "Employment Cost Index" in curated
    assert "PCE price index" in curated and "Core PCE Prices (QoQ ann.)" in curated
    assert events[6]["event"] == "Core PCE Prices"  # input rows aren't mutated


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
    "2026-10-20": [{"gmt": "11:30", "country": US, "eventName": "3-Month Bill Auction"}],  # the day before yesterday: dropped
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
    # 22:15 ET on 10-20 is already 10-21 in UTC: the calendar still starts on New York's 10-20 (B-034)
    now = [datetime(2026, 10, 21, 2, 15, tzinfo=UTC)]
    monkeypatch.setattr("argus.providers.macro.datetime",
                        type("DT", (datetime,), {"now": classmethod(lambda cls, tz=None: now[0].astimezone(tz))}))
    ev = p.economic_events(20)
    assert min(asked) == "2026-10-20" and max(asked) == "2026-11-11"
    got = {(e["event"], e["date"]): e["time_et"] for e in ev}
    assert got == {
        ("3-Month Bill Auction", "2026-10-19"): "11:30",         # yesterday's releases stay on the calendar
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

    # cached for the New York day; at New York midnight the window moves on
    asked.clear()
    now[0] = datetime(2026, 10, 21, 3, 59, tzinfo=UTC)
    assert p.economic_events(20) == ev and not asked
    now[0] = datetime(2026, 10, 21, 4, 0, tzinfo=UTC)
    rolled = p.economic_events(20)
    assert min(asked) == "2026-10-21" and min(e["date"] for e in rolled) >= "2026-10-20"


def _nasdaq_client(answers, asked=None):
    """A fake Nasdaq: `answers` maps a queried date to its raw rows, and can be changed between fetches."""
    class Resp:
        def __init__(self, rows):
            self.rows = rows

        def raise_for_status(self):
            pass

        def json(self):
            return {"data": {"rows": self.rows}}

    def get(self, url, params=None, **kw):
        if asked is not None:
            asked.append(params["date"])
        return Resp(answers.get(params["date"], []))
    return type("C", (), {"get": get})()


def _at(monkeypatch, now):
    monkeypatch.setattr("argus.providers.macro.datetime",
                        type("DT", (datetime,), {"now": classmethod(lambda cls, tz=None: now[0].astimezone(tz))}))
    monkeypatch.setattr("argus.providers.macro.time.monotonic", lambda: now[0].timestamp())


def test_economic_events_keep_todays_releases_when_nasdaq_flips(monkeypatch, tmp_path):
    # 10-29, 22:15 ET. First fetch: `date=10-30` answers with 10-29's rows, actuals in, PCE still blank.
    pce = {"gmt": "08:30", "country": US, "eventName": "Core PCE Price Index MoM", "consensus": "0.2%"}
    pce_yoy = pce | {"actual": "3.1%", "consensus": "3.1%"}  # Nasdaq names MoM and YoY alike
    gdp = {"gmt": "08:30", "country": US, "eventName": "GDP Growth Rate QoQ", "actual": "3.4%", "consensus": "3.2%"}
    answers = {"2026-10-29": [{"gmt": "08:30", "country": US, "eventName": "Initial Jobless Claims", "actual": "229K"}],
               "2026-10-30": [pce, pce_yoy, gdp],
               "2026-10-31": [{"gmt": "10:00", "country": US, "eventName": "Michigan Consumer Sentiment"}]}
    now = [datetime(2026, 10, 30, 2, 15, tzinfo=UTC)]
    _at(monkeypatch, now)
    p = MacroProvider(client=_nasdaq_client(answers), cache_dir=tmp_path)
    first = {(e["date"], e["event"]): e["actual"] for e in p.economic_events(5)}
    assert first[("2026-10-29", "GDP Growth Rate QoQ")] == "3.4%"
    assert first[("2026-10-28", "Initial Jobless Claims")] == "229K"  # yesterday, from today's query

    # Minutes later the mapping flips: `date=10-30` and `10-31` both answer with 10-30's rows, so 10-29's
    # come from no query.
    answers.update({"2026-10-29": [], "2026-10-30": [{"gmt": "10:00", "country": US, "eventName": "Michigan Consumer Sentiment"}]})
    now[0] = datetime(2026, 10, 30, 2, 21, tzinfo=UTC)
    p._cache.clear()  # past the 6 h cache: the flipped fetch is the one under test
    ev = p.economic_events(5)
    today = {e["event"]: e for e in ev if e["date"] == "2026-10-29"}
    assert set(today) == {"Core PCE Price Index MoM", "GDP Growth Rate QoQ"}
    assert today["GDP Growth Rate QoQ"]["actual"] == "3.4%"
    assert any(e["date"] == "2026-10-28" and e["event"] == "Initial Jobless Claims" for e in ev)
    assert [e["date"] for e in ev] == sorted(e["date"] for e in ev)

    # That answer is retried soon; now only PCE comes back, with its actual and without a consensus.
    answers["2026-10-30"] = [pce | {"actual": "0.2%", "consensus": None}]
    now[0] += timedelta(minutes=11)
    rows = [e for e in p.economic_events(5) if e["date"] == "2026-10-29"]
    assert [e["consensus"] for e in rows if e["event"] == pce["eventName"]] == ["0.2%", "3.1%"]
    assert {e["event"] for e in rows} == {"Core PCE Price Index MoM", "GDP Growth Rate QoQ"}  # nothing deleted
    mom = rows[0]  # the first of the two PCE rows, as Nasdaq lists them
    assert mom["actual"] == "0.2%"  # a later actual fills the blank...
    assert mom["consensus"] == "0.2%"  # ...and a later blank erases nothing

    # Kept across a restart.
    answers.clear()
    fresh = MacroProvider(client=_nasdaq_client(answers), cache_dir=tmp_path)
    assert {e["event"] for e in fresh.economic_events(5) if e["date"] == "2026-10-29"} == set(today)


def test_economic_events_retry_soon_when_today_is_missing(monkeypatch):
    asked = []
    answers = {"2026-10-31": [{"gmt": "10:00", "country": US, "eventName": "Michigan Consumer Sentiment"}]}
    now = [datetime(2026, 10, 29, 20, 0, tzinfo=UTC)]  # a Thursday; `date=10-30` came back empty
    _at(monkeypatch, now)
    p = MacroProvider(client=_nasdaq_client(answers, asked))
    assert not any(e["date"] == "2026-10-29" for e in p.economic_events(3))

    asked.clear()
    now[0] += timedelta(minutes=9)
    p.economic_events(3)
    assert not asked  # cached briefly...
    now[0] += timedelta(minutes=2)
    answers["2026-10-30"] = [{"gmt": "08:30", "country": US, "eventName": "GDP Growth Rate QoQ", "actual": "3.4%"}]
    assert any(e["date"] == "2026-10-29" for e in p.economic_events(3)) and asked  # ...not for 6 h

    asked.clear()
    now[0] += timedelta(hours=1)
    p.economic_events(3)
    assert not asked  # a full answer is held as before


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

    def quote_rows(symbols, fields, *_a):
        if fields == mc.QUOTE_FIELDS:  # the gauges' quotes
            return []
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


def _ts(iso: str) -> float:
    from datetime import datetime

    return datetime.fromisoformat(iso).timestamp()


def test_one_day_uses_the_previous_session_close_with_ragged_bars(monkeypatch):
    """Yahoo's bulk download (B-066): ^GSPC's 10-21 close comes back null, bitcoin has no 10-22 bar,
    and after 6 pm the oil and FX bars for "10-22" hold the overnight price, the settle gone."""
    import pandas as pd

    days = pd.to_datetime(["2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23"])
    nan = float("nan")
    raw = {"^GSPC": [7690.73, 7712.57, nan, 7663.43, nan],
           "XLU": [41.36, 41.88, 42.0, 42.87, nan],
           "CL=F": [103.66, 101.79, 97.15, 100.5, nan],
           "JPY=X": [157.81, 158.52, 158.27, 158.13, 156.84],
           "BTC-USD": [81853.5, 82941.0, 84011.97, nan, 81358.8]}
    df = pd.concat({s: pd.DataFrame({"Close": v}, index=days) for s, v in raw.items()}, axis=1)
    monkeypatch.setattr("argus.providers.yahoo._yf", lambda: type("Y", (), {"download": staticmethod(lambda *a, **k: df)}))
    closes = MacroProvider(client=object()).closes(list(raw))
    assert date(2026, 10, 21) not in closes["^GSPC"] and date(2026, 10, 22) not in closes["BTC-USD"]

    at = _ts("2026-10-23T02:20:00+00:00")  # 10:20 pm New York on 10-22
    quotes = [
        {"symbol": "^GSPC", "quoteType": "INDEX", "regularMarketPrice": 7663.43, "regularMarketPreviousClose": 7757.17,
         "regularMarketTime": _ts("2026-10-22T20:31:48+00:00")},
        {"symbol": "XLU", "quoteType": "ETF", "regularMarketPrice": 42.87, "regularMarketPreviousClose": 42.0,
         "regularMarketTime": _ts("2026-10-22T20:00:00+00:00")},
        {"symbol": "CL=F", "quoteType": "FUTURE", "regularMarketPrice": 100.76, "regularMarketPreviousClose": 99.47,
         "regularMarketTime": at},
        {"symbol": "JPY=X", "quoteType": "CURRENCY", "regularMarketPrice": 156.90, "regularMarketPreviousClose": 156.80,
         "regularMarketTime": at},
        {"symbol": "BTC-USD", "quoteType": "CRYPTOCURRENCY", "regularMarketPrice": 81338.7,
         "regularMarketPreviousClose": 81316.2, "regularMarketTime": at},
    ]
    out = mc.build(closes, None, None, None, date(2026, 10, 22), quotes=quotes)
    g = {x["symbol"]: x for x in out["gauges"]}
    one_day = lambda last, prev: pytest.approx((last / prev - 1) * 100)
    assert g["^GSPC"]["returns"]["1D"] == one_day(7663.43, 7757.17)  # not 7712.57, two sessions back
    assert g["^GSPC"]["as_of"] == "2026-10-22" and g["^GSPC"]["change"] == pytest.approx(7663.43 - 7757.17)
    assert g["CL=F"]["returns"]["1D"] == one_day(100.76, 99.47)  # vs the 10-22 settle, on the 10-23 session
    assert g["CL=F"]["as_of"] == "2026-10-23" and g["CL=F"]["spark"][-3:] == [97.15, 99.47, 100.76]
    assert g["JPY=X"]["returns"]["1D"] == one_day(156.90, 156.80)
    assert g["BTC-USD"]["returns"]["1D"] == one_day(81338.7, 81316.2)
    assert g["BTC-USD"]["spark"][-3:] == [84011.97, 81316.2, 81338.7]  # 10-21, 10-22 (filled), 10-23
    assert {s["symbol"]: s["returns"]["1D"] for s in out["sectors"]}["XLU"] == one_day(42.87, 42.0)

    # Without quotes (the batch failed) the bars still give a figure.
    assert mc.build(closes, None, None, None, date(2026, 10, 22))["gauges"][0]["returns"]["1D"] is not None


def test_quote_sessions_over_a_weekend_and_a_holiday():
    row = lambda kind, iso: {"quoteType": kind, "regularMarketTime": _ts(iso)}
    # Sunday 7 pm New York: futures and FX are on Monday's session, which follows Friday's
    assert mc.quote_sessions(row("FUTURE", "2026-10-25T23:00:00+00:00")) == (date(2026, 10, 26), date(2026, 10, 23))
    assert mc.quote_sessions(row("CURRENCY", "2026-10-25T23:30:00+00:00")) == (date(2026, 10, 26), date(2026, 10, 23))
    # Saturday: stocks are still on Friday's close, measured from Thursday's
    assert mc.quote_sessions(row("ETF", "2026-10-24T15:00:00+00:00")) == (date(2026, 10, 23), date(2026, 10, 22))
    # The Friday after Thanksgiving follows Wednesday
    assert mc.quote_sessions(row("INDEX", "2026-11-27T18:00:00+00:00")) == (date(2026, 11, 27), date(2026, 11, 25))
    assert mc.quote_sessions(row("CRYPTOCURRENCY", "2026-10-25T01:00:00+00:00")) == (date(2026, 10, 25), date(2026, 10, 24))
    assert mc.quote_sessions({"quoteType": "INDEX"}) is None
