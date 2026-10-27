from datetime import UTC, date, datetime, timedelta

import pytest

from argus.errors import ArgusError
from argus.providers.base import Quote
from argus.services.alerts import KINDS, check
from argus.services.events import EventsService
from argus.services.portfolio import TxnInput
from tests.conftest import FakeQuotes

TODAY = date(2026, 9, 28)
NOW = datetime(2026, 9, 28, 15, tzinfo=UTC)


def q(price, prev=100.0):
    return Quote("X", price, prev, None, None, None, NOW, "fake")


@pytest.mark.parametrize("kind,t,quote,m,cost,earn,fired", [
    ("price_above", 100, q(101), {}, None, None, True),
    ("price_below", 100, q(101), {}, None, None, False),
    ("day_move_pct", 3, q(96.5), {}, None, None, True),
    ("day_gain_pct", 3, q(96.5), {}, None, None, False),
    ("day_loss_pct", 3, q(96.5), {}, None, None, True),
    ("near_52w_high", 2, q(99), {"high_52w": 100}, None, None, True),
    ("near_52w_low", 2, q(99), {"low_52w": 90}, None, None, False),
    ("pe_above", 30, None, {"pe_ttm": 35}, None, None, True),
    ("below_cost_pct", 10, q(85), {}, 100, None, True),
    ("above_cost_pct", 10, q(105), {}, 100, None, False),
    ("earnings_within_days", 3, None, {}, None, TODAY + timedelta(days=2), True),
    ("earnings_within_days", 3, None, {}, None, TODAY + timedelta(days=5), False),
])
def test_alert_checks(kind, t, quote, m, cost, earn, fired):
    assert check(kind, t, quote, m, cost, earn, TODAY)[0] is fired


def test_alert_check_without_data_is_skipped():
    assert check("near_52w_high", 2, q(99), {}, None, None, TODAY) is None
    assert check("below_cost_pct", 5, q(99), {}, None, None, TODAY) is None
    assert set(KINDS) >= {"price_above", "earnings_within_days"}


def test_alert_fires_once_per_session(make_argus):
    a = make_argus([FakeQuotes("fake", {"AAA": (110, 100)})])
    alert = a.alerts.create("aaa", "day_gain_pct", 5, note="momentum")
    assert alert["label"] == "Up 5% or more in a day"
    first = a.evaluate_alerts()
    assert [f["symbol"] for f in first] == ["AAA"] and "+10.00%" in first[0]["message"]
    assert a.evaluate_alerts() == []  # same session: not again
    assert a.alerts.fired(since=date(2000, 1, 1))[0]["note"] == "momentum"
    a.alerts.set_active(alert["id"], False)
    assert a.alerts.list() == []


def test_alert_validation(make_argus):
    a = make_argus()
    with pytest.raises(ArgusError):
        a.alerts.create("AAA", "moon", 1)
    with pytest.raises(ArgusError):
        a.alerts.create("AAA", "price_above", -1)


def test_notes_and_due_reviews(make_argus):
    a = make_argus()
    n = a.notes.add("nvda", "AI capex cycle; exit if DC growth < 20%", kind="thesis", review_on=TODAY)
    a.notes.add("NVDA", "watch Blackwell ramp")
    assert [x["kind"] for x in a.notes.list("NVDA")] == ["thesis", "note"]
    assert [x["id"] for x in a.notes.list(due_by=TODAY)] == [n["id"]]
    a.notes.update(n["id"], archived=True)
    assert a.notes.list(due_by=TODAY) == []


class FakeFinnhub:
    def __init__(self):
        self.calls = 0

    def earnings_calendar(self, symbol, start, end):
        self.calls += 1
        if symbol != "AAA":
            return []
        return [{"date": "2026-10-01", "hour": "amc", "epsEstimate": 1.0, "revenueEstimate": 5e9, "quarter": 3, "year": 2026},
                {"date": "2026-07-01", "hour": "bmo", "epsEstimate": 1.0, "epsActual": 1.2, "quarter": 2, "year": 2026}]

    def company_news(self, symbol, start, end):
        return [{"datetime": 1790366400, "headline": f"{symbol} does a thing", "source": "Wire", "url": "u"}]


class FakeYahoo:
    def get_calendar(self, symbol):
        return {"Ex-Dividend Date": date(2026, 10, 5)} if symbol == "AAA" else {}


def test_events_refresh_is_cached_and_filters_window(make_argus):
    a = make_argus()
    fh = FakeFinnhub()
    ev = EventsService(a.engine, fh, FakeYahoo())
    ev.refresh(["AAA", "ETF1"], today=TODAY)
    ev.refresh(["AAA", "ETF1"], today=TODAY)  # within 20h: no provider calls
    assert fh.calls == 2
    rows = ev.between(["AAA"], TODAY, TODAY + timedelta(days=30))
    assert [(r["kind"], r["date"], r.get("hour")) for r in rows] == [("earnings", "2026-10-01", "amc"),
                                                                     ("ex_dividend", "2026-10-05", None)]
    assert ev.next_earnings(["AAA", "ETF1"], TODAY) == {"AAA": date(2026, 10, 1)}
    assert ev.news("AAA")[0]["headline"] == "AAA does a thing"


def test_daily_brief_shape(make_argus):
    a = make_argus([FakeQuotes("fake", {"AAA": (110, 100), "BBB": (95, 100), "SPY": (500, 495)})])
    a.portfolios.create_portfolio("growth")
    a.portfolios.add_transactions("growth", [TxnInput("BUY", "AAA", NOW - timedelta(days=30), 10, 90),
                                             TxnInput("BUY", "BBB", NOW - timedelta(days=30), 10, 100)])
    a.alerts.create("BBB", "day_loss_pct", 3)
    a.notes.add("AAA", "thesis", kind="thesis", review_on=datetime.now(UTC).date())
    b = a.daily_brief("growth", news=False)
    assert b["top_gainers"][0]["symbol"] == "AAA" and b["top_losers"][0]["symbol"] == "BBB"
    assert b["benchmark"]["symbol"] == "SPY" and b["totals"]["position_count"] == 2
    assert [x["symbol"] for x in b["alerts_fired"]] == ["BBB"]
    assert b["theses_due"][0]["symbol"] == "AAA"


def test_daily_brief_movers_keep_their_sign(make_argus):
    # Mostly up on the day: losers must not be padded with gainers (nor gainers with losers).
    a = make_argus([FakeQuotes("fake", {"AAA": (110, 100), "BBB": (101, 100), "CCC": (100, 100),
                                        "DDD": (99, 100), "SPY": (500, 495)})])
    a.portfolios.create_portfolio("growth")
    a.portfolios.add_transactions("growth", [TxnInput("BUY", s, NOW - timedelta(days=30), 10, 90)
                                             for s in ("AAA", "BBB", "CCC", "DDD")])
    b = a.daily_brief("growth", news=False)
    assert [m["symbol"] for m in b["top_gainers"]] == ["AAA", "BBB"]
    assert [m["symbol"] for m in b["top_losers"]] == ["DDD"]


def test_daily_brief_is_scoped_to_its_portfolio(make_argus):
    from argus.db import session_scope
    from argus.market_calendar import NY
    from argus.models import Event

    a = make_argus([FakeQuotes("fake", {"AAA": (95, 100), "BBB": (95, 100), "WWW": (95, 100), "SPY": (500, 495)})])
    a.portfolios.create_portfolio("growth")
    a.portfolios.create_portfolio("income")
    a.portfolios.add_transactions("growth", [TxnInput("BUY", "AAA", NOW - timedelta(days=30), 10, 90)])
    a.portfolios.add_transactions("income", [TxnInput("BUY", "BBB", NOW - timedelta(days=30), 10, 90)])
    a.watchlists.add(["WWW"])
    today = datetime.now(NY).date()
    a.events.refresh(["AAA", "BBB", "WWW"])  # mark fresh so the brief keeps the rows below
    with session_scope(a.engine) as s:
        for sym in ("AAA", "BBB", "WWW"):
            s.add(Event(symbol=sym, kind="earnings", d=today + timedelta(days=2), hour="amc", data={}, source="t"))
            s.add(Event(symbol=sym, kind="ex_dividend", d=today + timedelta(days=3), data={}, source="t"))
        # Reported today: it already happened, so it is recent, not upcoming.
        s.add(Event(symbol="BBB", kind="earnings", d=today, hour="bmo", data={"epsActual": 1.1}, source="t"))
    for sym in ("AAA", "BBB", "WWW"):
        a.alerts.create(sym, "day_loss_pct", 3)
        a.notes.add(sym, "thesis", kind="thesis", review_on=today)

    def pairs(rows):
        return [(e["symbol"], e["held"]) for e in rows]

    b = a.daily_brief("income", news=False)
    assert pairs(b["earnings_upcoming"]) == [("BBB", True)]
    assert pairs(b["dividends_upcoming"]) == [("BBB", True)]
    assert [(e["symbol"], e["date"]) for e in b["earnings_recent"]] == [("BBB", today.isoformat())]
    assert [x["symbol"] for x in b["alerts_fired"]] == ["BBB"]
    assert [x["symbol"] for x in b["theses_due"]] == ["BBB"]

    g = a.daily_brief("growth", news=False)
    assert pairs(g["earnings_upcoming"]) == pairs(g["dividends_upcoming"]) == [("AAA", True)]
    assert g["earnings_recent"] == []
    assert [x["symbol"] for x in g["alerts_fired"]] == ["AAA"]
    assert [x["symbol"] for x in g["theses_due"]] == ["AAA"]


@pytest.mark.parametrize("hour,hm,actual,happened", [
    ("bmo", (9, 0), None, False), ("bmo", (10, 0), None, True),
    ("amc", (15, 0), None, False), ("amc", (16, 30), None, True),
    (None, (8, 0), 1.0, True), (None, (23, 0), None, False),
])
def test_todays_earnings_count_as_happened_once_reported_or_past_their_time(hour, hm, actual, happened):
    from argus.app import _event_happened
    from argus.market_calendar import NY

    now = datetime(2026, 10, 20, *hm, tzinfo=NY)
    e = {"symbol": "X", "kind": "earnings", "date": "2026-10-20", "hour": hour}
    if actual is not None:
        e["epsActual"] = actual
    assert _event_happened(e, now) is happened
    assert _event_happened(e | {"date": "2026-10-19"}, now) is True
    assert _event_happened({**e, "date": "2026-10-21", "epsActual": None}, now) is False


def test_dividend_events_follow_ex_date_ownership_and_projection(make_argus):
    from argus.db import session_scope
    from argus.market_calendar import NY, session_on_or_after
    from argus.models import DividendHistory, Event
    from argus.services.dividends import add_months

    today = datetime.now(NY).date()
    if (today + timedelta(days=10)).year != today.year:
        pytest.skip("projections stop at the year end")
    a = make_argus([FakeQuotes("fake", {s: (100, 100) for s in ("JJJ", "MMM", "AAA", "SPY")})])
    ex, pay = today - timedelta(days=20), today + timedelta(days=3)
    a.portfolios.create_portfolio("late")
    a.portfolios.create_portfolio("early")
    a.portfolios.add_transactions("late", [TxnInput("BUY", "JJJ", datetime.now(UTC) - timedelta(days=10), 10, 90),
                                           TxnInput("BUY", "MMM", datetime.now(UTC) - timedelta(days=200), 10, 90),
                                           TxnInput("BUY", "AAA", datetime.now(UTC) - timedelta(days=200), 10, 90)])
    a.portfolios.add_transactions("early", [TxnInput("BUY", "JJJ", datetime.now(UTC) - timedelta(days=30), 5, 90)])
    target = today + timedelta(days=3)  # MMM and AAA pay monthly; their next ex-date lands about here
    monthly = [[add_months(target, -k).isoformat(), 0.25] for k in range(6, 0, -1)]
    a.events.refresh(["JJJ", "MMM", "AAA"])  # mark fresh so the rows below stay
    with session_scope(a.engine) as s:
        for sym, data in (("JJJ", [[add_months(ex, -3).isoformat(), 1.0], [ex.isoformat(), 1.0]]),
                          ("MMM", monthly), ("AAA", monthly)):
            s.add(DividendHistory(symbol=sym, as_of=datetime.now(UTC), data=data))
        s.add(Event(symbol="JJJ", kind="dividend_pay", d=pay, data={}, source="t"))
        s.add(Event(symbol="AAA", kind="ex_dividend", d=target - timedelta(days=1), data={}, source="t"))

    # (1) "late" bought JJJ after its ex-date: not owed the payment; "early" is
    b = a.daily_brief("late", news=False)
    assert [e["symbol"] for e in b["dividends_upcoming"] if e["kind"] == "dividend_pay"] == []
    early = a.upcoming_events(refresh=False, portfolio="early")["upcoming"]
    assert [(e["symbol"], e["held"], e["ex_date"]) for e in early] == [("JJJ", True, ex.isoformat())]
    jjj = a.upcoming_events(refresh=False, symbols=["JJJ"])["upcoming"]  # stock page: any portfolio
    assert [(e["kind"], e["held"]) for e in jjj] == [("dividend_pay", True)]

    # (2) + (3) MMM's projected ex-date (moved to a trading day) shows as an estimate, the same date as
    # the Dividends page; AAA's announced ex-date replaces its estimate
    est = session_on_or_after(add_months(target, 0)).isoformat()
    div = {h["symbol"]: h for h in a.dividends("late")["holdings"]}
    assert div["MMM"]["next_ex_date_est"] == est
    rows = [(e["symbol"], e["date"], e.get("estimated", False), e["held"]) for e in b["dividends_upcoming"]]
    assert rows == sorted([("MMM", est, True, True), ("AAA", (target - timedelta(days=1)).isoformat(), False, True)],
                          key=lambda r: (r[1], r[0]))
    mmm = next(e for e in b["dividends_upcoming"] if e["symbol"] == "MMM")
    assert mmm["amount"] == pytest.approx(2.5)
