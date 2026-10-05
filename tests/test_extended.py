"""Pre-market and after-hours prices: kept beside the regular price, never in place of it."""

from datetime import UTC, datetime, timedelta

import pytest

from argus.live import LiveHub
from argus.providers.base import ProviderError, Quote
from tests.conftest import FakeQuotes

LAST_CLOSE = datetime(2026, 10, 2, 20, 0, tzinfo=UTC)  # Fri 4:00 PM New York
PRE = {"session": "pre", "last_close": LAST_CLOSE.isoformat()}


class FakeExtended:
    def __init__(self, rows):
        self.rows, self.calls, self.fail = rows, [], False

    def get_extended(self, symbols):
        self.calls.append(list(symbols))
        if self.fail:
            raise ProviderError("yahoo down")
        return {s: r for s, r in self.rows.items() if s in symbols}


@pytest.fixture
def a(make_argus):
    a = make_argus([FakeQuotes("fake", {"AAA": (100, 98), "BBB": (50, 50), "CCC": (10, 10)})])
    a.market.profile_provider = FakeExtended({
        "AAA": ("pre", 102.0, LAST_CLOSE + timedelta(hours=60)),       # Monday pre-market
        "BBB": ("post", 49.0, LAST_CLOSE + timedelta(minutes=30)),     # Friday after hours
        "CCC": ("post", 11.0, LAST_CLOSE - timedelta(days=1)),         # Thursday: older than the close
    })
    return a


def test_extended_prices_sit_beside_the_regular_price(a):
    quotes = a.market.attach_extended({s: Quote(s, p, p, None, None, None, LAST_CLOSE, "fake")
                                       for s, p in (("AAA", 100), ("BBB", 50), ("CCC", 10))}, PRE)
    aaa, bbb, ccc = quotes["AAA"], quotes["BBB"], quotes["CCC"]
    assert (aaa.price, aaa.ext_session, aaa.ext_price, aaa.ext_change_pct) == (100, "pre", 102.0, pytest.approx(2.0))
    assert (bbb.ext_session, bbb.ext_change) == ("post", -1.0)  # Friday's after-hours until Monday's pre trades
    assert ccc.ext_price is None  # before the last close: not news
    d = aaa.to_dict()
    assert d["ext_change_pct"] == pytest.approx(2.0) and d["ext_as_of"].startswith("2026-10-05")


def test_extended_prices_are_cached_and_dropped_in_the_regular_session(a):
    q = {"AAA": Quote("AAA", 100, 98, None, None, None, LAST_CLOSE, "fake")}
    a.market.attach_extended(q, PRE)
    a.market.attach_extended(q, PRE)
    assert len(a.market.profile_provider.calls) == 1  # one batch fetch per minute

    a.market.profile_provider.fail = True
    a.market.store_extended({"AAA": ("pre", 103.0, LAST_CLOSE + timedelta(hours=61))},
                            datetime.now(UTC) - timedelta(minutes=5))  # stale cache row
    assert a.market.attach_extended(q, PRE)["AAA"].ext_price == 103.0  # provider down: serve the cache

    with_ext = a.market.attach_extended(q, PRE)
    regular = a.market.attach_extended(with_ext, {"session": "regular", "last_close": LAST_CLOSE.isoformat()})
    assert regular["AAA"].ext_price is None


def test_hub_routes_pre_market_prints_to_extended_fields(make_argus):
    hub = LiveHub(make_argus())
    hub.status = PRE
    hub.quotes["AAA"] = Quote("AAA", 100, 98, 99, 101, 97, datetime.now(UTC), "yahoo")  # fallback: fetch-time stamp
    t = LAST_CLOSE + timedelta(hours=60)
    hub.apply_trade("AAA", 101.5, t)
    q = hub.quotes["AAA"]
    assert (q.price, q.high, q.ext_price, q.ext_session, q.ext_as_of) == (100, 101, 101.5, "pre", t)
    hub.apply_trade("AAA", 90, t - timedelta(seconds=1))  # older print
    hub.apply_trade("AAA", 90, LAST_CLOSE - timedelta(minutes=1))  # before the close
    assert hub.quotes["AAA"].ext_price == 101.5 and hub._dirty == {"AAA"}

    hub.status = {"session": "regular", "last_close": LAST_CLOSE.isoformat()}
    hub.apply_trade("AAA", 104, t + timedelta(hours=6))
    assert (hub.quotes["AAA"].price, hub.quotes["AAA"].high) == (104, 104)


def test_portfolio_summary_reports_the_extended_move(a):
    a.portfolios.create_portfolio("growth")
    from argus.services.portfolio import TxnInput
    a.portfolios.add_transactions("growth", [TxnInput(type="BUY", symbol=s, ts=LAST_CLOSE - timedelta(days=30), qty=10,
                                                      price=40) for s in ("AAA", "BBB", "CCC")])
    quotes = a.market.attach_extended({s: Quote(s, p, p, None, None, None, LAST_CLOSE, "fake")
                                       for s, p in (("AAA", 100), ("BBB", 50), ("CCC", 10))}, PRE)
    s = a.portfolios.summary("growth", quotes)
    rows = {r["symbol"]: r for r in s["positions"]}
    assert (rows["AAA"]["ext_pnl"], rows["BBB"]["ext_pnl"], "ext_pnl" in rows["CCC"]) == (20.0, -10.0, False)
    t = s["totals"]
    assert (t["ext_pnl"], t["ext_session"]) == (10.0, "pre")
    assert t["ext_pnl_pct"] == pytest.approx(10 / 1600 * 100) and t["ext_coverage_pct"] == pytest.approx(1500 / 1600 * 100)
