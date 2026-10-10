"""Earnings reports on the financials card: estimates vs actuals, beat/miss, price reaction."""

from datetime import UTC, date, datetime

import pytest

from argus.market_calendar import NY
from argus.providers.base import Quote
from argus.services.earnings import build, reaction, timing, verdict

# Mon-Fri, Jul 27-31 2026: (open, close)
BARS = {date(2026, 7, 27): (100, 100), date(2026, 7, 28): (101, 100), date(2026, 7, 29): (99, 98),
        date(2026, 7, 30): (90, 92), date(2026, 7, 31): (93, 94)}


def test_timing_from_hour_or_report_time():
    at = lambda h, m=0: datetime(2026, 7, 29, h, m, tzinfo=NY)  # noqa: E731
    assert [timing(at(16), None), timing(at(7), None), timing(at(12), None), timing(at(0), None)] == \
        ["amc", "bmo", "dmh", None]
    assert timing(at(16), "bmo") == "bmo"  # the calendar's hour wins


def test_verdict():
    assert [verdict(7.31, 6.92), verdict(6.18, 7.36), verdict(1.0, 1.003), verdict(None, 1)] == \
        ["beat", "miss", "in_line", None]


def test_reaction_depends_on_when_the_report_came():
    today = date(2026, 8, 3)
    amc = reaction(date(2026, 7, 29), "amc", BARS, today)  # next day vs that day's close
    assert (amc["base_date"], amc["date"]) == ("2026-07-29", "2026-07-30")
    assert amc["close_pct"] == pytest.approx(92 / 98 * 100 - 100) and amc["open_pct"] == pytest.approx(90 / 98 * 100 - 100)
    bmo = reaction(date(2026, 7, 29), "bmo", BARS, today)  # that day vs the prior close
    assert (bmo["base_date"], bmo["date"], bmo["close_pct"]) == ("2026-07-28", "2026-07-29", pytest.approx(-2.0))
    unknown = reaction(date(2026, 7, 29), None, BARS, today)  # prior close -> next session's close
    assert (unknown["base_date"], unknown["date"]) == ("2026-07-28", "2026-07-30")
    assert not amc["provisional"]


def test_reaction_is_provisional_until_the_session_closes():
    bars = {d: v for d, v in BARS.items() if d <= date(2026, 7, 31)}
    # Reported Friday after the close; Monday hasn't traded: the after-hours price stands in.
    q = Quote("X", 94, 93, None, None, None, datetime(2026, 7, 31, 20, tzinfo=UTC), "fake",
              ext_price=103.4, ext_session="post", ext_as_of=datetime(2026, 7, 31, 22, tzinfo=UTC))
    r = reaction(date(2026, 7, 31), "amc", bars, date(2026, 7, 31), q, "post")
    assert (r["provisional"], r["label"], r["date"]) == (True, "after hours", None)
    assert r["close_pct"] == pytest.approx(10.0)
    # A report before today's open, mid-session: today's bar is still moving.
    r = reaction(date(2026, 7, 31), "bmo", bars, date(2026, 7, 31), None, "regular")
    assert (r["provisional"], r["label"], r["date"]) == (True, "today", "2026-07-31")
    assert reaction(date(2026, 5, 1), "amc", {}, date(2026, 7, 31), q) is None  # old and no bars


def test_build_matches_reports_to_quarters_and_prefers_adjusted_eps():
    yahoo = [
        {"date": "2026-04-29", "hour": "amc", "eps_estimate": 6.66, "eps_actual": 10.44},   # GAAP, one-offs
        {"date": "2026-07-29", "hour": "amc", "eps_estimate": 7.22, "eps_actual": 6.18},
        {"date": "2026-10-28", "hour": "amc", "eps_estimate": 6.25, "eps_actual": None},    # upcoming
    ]
    # Finnhub has both quarters; Q2 also has calendar figures, which win.
    results = [{"period": "2026-06-30", "epsActual": 6.18, "epsEstimate": 7.36},
               {"period": "2026-03-31", "epsActual": 7.31, "epsEstimate": 6.92}]
    calendar = [{"date": "2026-07-30", "hour": "amc", "epsEstimate": 7.36, "epsActual": 6.18,
                 "revenueEstimate": 58.0e9, "revenueActual": 60.8e9},          # a day off Yahoo's date
                {"date": "2026-10-28", "hour": "amc", "epsEstimate": 6.61, "revenueEstimate": 64.5e9}]
    out = build(["2026-06-30", "2026-03-31", "2025-12-31"], yahoo, calendar, results, BARS, date(2026, 8, 3))
    q2, q1 = out["reports"]  # 2025-12-31 has no report on file: left out
    assert (q2["period_end"], q2["report_date"], q2["timing"]) == ("2026-06-30", "2026-07-29", "amc")
    assert (q2["eps_estimate"], q2["eps_actual"], q2["eps_basis"], q2["eps_result"]) == (7.36, 6.18, "adjusted", "miss")
    assert (q2["revenue_result"], q2["revenue_surprise_pct"]) == ("beat", pytest.approx(60.8 / 58 * 100 - 100))
    assert q2["reaction"]["close_pct"] == pytest.approx(92 / 98 * 100 - 100)
    assert (q1["eps_actual"], q1["eps_basis"], q1["eps_result"]) == (7.31, "adjusted", "beat")  # not Yahoo's 10.44
    assert q1["revenue_estimate"] is None
    assert out["next"] == {"date": "2026-10-28", "timing": "amc", "eps_estimate": 6.61, "revenue_estimate": 64.5e9}


def test_yahoo_alone_is_marked_reported():
    out = build(["2026-06-30"], [{"date": "2026-07-29", "hour": "amc", "eps_estimate": 7.22, "eps_actual": 6.18}],
                [], [], {}, date(2026, 8, 3))
    r = out["reports"][0]
    assert (r["eps_basis"], r["eps_result"], r["reaction"], out["next"]) == ("reported", "miss", None, None)


def test_coming_up_excludes_earnings_history_rows(make_argus):
    from argus.db import session_scope
    from argus.models import Event
    a = make_argus()
    today = datetime.now(NY).date()
    with session_scope(a.engine) as s:
        s.add(Event(symbol="AAA", kind="eps_report", d=today, hour="amc", data={}, source="yahoo"))
        s.add(Event(symbol="AAA", kind="earnings", d=today, hour="amc", data={}, source="finnhub"))
    ev = a.upcoming_events(symbols=["AAA"], refresh=False)
    assert [e["kind"] for e in ev["upcoming"] + ev["recent"]] == ["earnings"]


def test_finnhub_results_pair_with_the_nearest_report_even_when_mislabeled():
    # NVDA-style: quarters ended Apr 26 / Jul 26, reported May 20 / Aug 26, filed as Jun 30 / Sep 30.
    yahoo = [{"date": "2026-05-20", "hour": "amc", "eps_estimate": 1.77, "eps_actual": 1.87},
             {"date": "2026-08-26", "hour": "amc", "eps_estimate": 2.09, "eps_actual": 2.22}]
    results = [{"period": "2026-06-30", "epsActual": 1.87, "epsEstimate": 1.79},
               {"period": "2026-09-30", "epsActual": 2.22, "epsEstimate": 2.14}]
    out = build(["2026-07-26", "2026-04-26"], yahoo, [], results, {}, date(2026, 10, 1))
    assert [(r["period_end"], r["eps_estimate"], r["eps_basis"]) for r in out["reports"]] == \
        [("2026-07-26", 2.14, "adjusted"), ("2026-04-26", 1.79, "adjusted")]
