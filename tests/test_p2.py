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
