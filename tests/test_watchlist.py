import pytest

from argus.errors import ArgusError
from tests.conftest import FakeQuotes


class FakeFund:
    name = "fake"

    def get_metrics(self, symbol):
        return {"pe_ttm": 20.0, "pb": 3.0}


def test_watchlist_add_is_idempotent_and_remove_reports_missing(make_argus):
    a = make_argus([FakeQuotes("fake", {"TSLA": (250, 245), "BRK.B": (480, 478)})], fundamentals=[FakeFund()])
    assert a.watchlists.add(["tsla", "TSLA", "brk-b"])["added"] == ["TSLA", "BRK.B"]
    assert a.watchlists.add(["TSLA"], note="EV")["already_present"] == ["TSLA"]
    w = a.watchlist()
    tsla = next(i for i in w["items"] if i["symbol"] == "TSLA")
    assert tsla["note"] == "EV" and tsla["quote"]["price"] == 250 and tsla["metrics"]["pe_ttm"] == 20.0
    assert a.watchlists.remove(["TSLA", "NOPE"]) == {"watchlist": "Watchlist", "removed": ["TSLA"], "not_found": ["NOPE"]}


def test_watchlist_add_rejects_unknown_tickers(make_argus):
    a = make_argus([FakeQuotes("fake", {"ISRG": (409, 415)})])
    with pytest.raises(ArgusError) as e:
        a.watchlists.add(["ISRG", "ISGR"])
    assert e.value.code == "UNKNOWN_SYMBOL" and "ISGR" in e.value.message
    assert a.watchlists.items() == []  # nothing written when any ticker is unknown
    a.watchlists.add(["ISRG"])
    assert a.watchlists.add(["ISRG"], note="robotics")["already_present"] == ["ISRG"]


def test_default_watchlist_empty_before_first_add_and_named_missing_errors(make_argus):
    a = make_argus()
    assert a.watchlists.items() == []
    with pytest.raises(ArgusError):
        a.watchlists.items("Nope")


def test_compare_combines_quotes_and_metrics(make_argus):
    a = make_argus([FakeQuotes("fake", {"AAA": (10, 9)})], fundamentals=[FakeFund()])
    out = a.compare(["AAA", "BBB"], ["pe_ttm", "pb"])
    assert out["rows"][0] == {"symbol": "AAA", "price": 10, "change_pct": pytest.approx(11.111, abs=1e-3), "pe_ttm": 20.0, "pb": 3.0}
    assert out["rows"][1]["price"] is None and "BBB" in out["errors"]


def test_watchlist_views_share_the_portfolio_machinery(make_argus):
    from datetime import UTC, date, datetime, timedelta

    from argus.providers.base import Bar
    from tests.test_speed import PerSymbolHistory

    today = date.today()
    days = [today - timedelta(days=60 - i) for i in range(61)]
    bars = [Bar(datetime(d.year, d.month, d.day, 21, tzinfo=UTC), 1, 1, 1, 100 + i, 1) for i, d in enumerate(days)]
    a = make_argus([FakeQuotes("fake", {"TSLA": (250, 245)})], history=PerSymbolHistory({"TSLA": bars}),
                   fundamentals=[FakeFund()])
    a.watchlists.add(["TSLA"])
    f = a.watchlist_fundamentals()
    m = f["metrics"]["TSLA"]
    from argus.services.dividends import add_months

    target = add_months(days[-1], -1)
    base_i = max(i for i, d in enumerate(days) if d <= target)
    assert f["symbols"] == ["TSLA"] and m["return_1m_pct"] == pytest.approx(((160) / (100 + base_i) - 1) * 100)
    d = a.watchlist_dividends()
    assert d["watchlist"] == "Watchlist" and d["holdings"][0]["symbol"] == "TSLA" and d["totals"]["annual_income"] == 0
    assert a.watchlist_earnings()["rows"] == [{"symbol": "TSLA", "last": None, "next": None}]
