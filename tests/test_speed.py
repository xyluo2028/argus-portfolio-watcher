"""Latency work: batch quotes, bulk history reads, parallel fundamentals, background refresh."""

import threading
import time
from datetime import UTC, datetime, timedelta

import pytest

from argus.providers.base import Bar, ProviderError
from argus.providers.yahoo import YahooProvider
from tests.conftest import FakeQuotes


# -- Yahoo batch quotes ---------------------------------------------------------------
def test_yahoo_quotes_come_from_one_batch_request(monkeypatch):
    seen = []

    def rows(symbols, fields):
        seen.append(list(symbols))
        return [{"symbol": "BRK-B", "regularMarketPrice": 480.25, "regularMarketPreviousClose": 478.0,
                 "regularMarketTime": 1791470845},
                {"symbol": "NOPE", "regularMarketPrice": None}]

    monkeypatch.setattr(YahooProvider, "_quote_rows", staticmethod(rows))
    q = YahooProvider().get_quotes(["BRK.B", "NOPE"])
    assert seen == [["BRK-B", "NOPE"]]                       # one call, Yahoo's own symbols
    assert list(q) == ["BRK.B"] and q["BRK.B"].prev_close == 478.0
    assert q["BRK.B"].as_of == datetime.fromtimestamp(1791470845, UTC)  # Yahoo's trade time, not fetch time


def test_yahoo_falls_back_to_per_symbol_when_the_batch_fails(monkeypatch):
    def broken(symbols, fields):
        raise ProviderError("crumb rejected")

    monkeypatch.setattr(YahooProvider, "_quote_rows", staticmethod(broken))
    monkeypatch.setattr(YahooProvider, "_quotes_one_by_one", lambda self, syms, native: {"X": "fallback"})
    assert YahooProvider().get_quotes(["X"]) == {"X": "fallback"}


def test_large_lookups_ask_the_batch_provider_first(make_argus):
    finnhub = FakeQuotes("finnhub", {s: (10, 9) for s in "ABCDEFG"})
    batch = FakeQuotes("yahoo", {s: (11, 9) for s in "ABCDEFG"})
    batch.batch_quotes = True
    a = make_argus([finnhub, batch])
    a.market.get_quotes(["A", "B"])
    assert (finnhub.calls, batch.calls) == ([["A", "B"]], [])        # small: Finnhub first
    # Uncached symbols only: while the market is closed a cached quote counts as the settled close.
    q, _ = a.market.get_quotes(list("CDEFG"))
    assert batch.calls == [["C", "D", "E", "F", "G"]] and len(finnhub.calls) == 1 and q["C"].source == "yahoo"


def test_yahoo_info_is_cached(monkeypatch):
    calls = []

    class T:
        def __init__(self, s):
            calls.append(s)
            self.info = {"sector": "Technology"}

    monkeypatch.setattr("argus.providers.yahoo._yf", lambda: type("yf", (), {"Ticker": T}))
    y = YahooProvider()
    assert y.get_info("NVDA") == y.get_info("NVDA") == {"sector": "Technology"} and calls == ["NVDA"]


# -- bulk history -----------------------------------------------------------------------
def _bars(start, days):
    return [Bar(start + timedelta(days=i), 1, 1, 1, 100 + i, 1) for i in range(days)]


class PerSymbolHistory:
    """Different history per symbol; counts downloads per symbol."""

    name = "fake"

    def __init__(self, bars_by_symbol):
        self.bars = bars_by_symbol
        self.calls: dict[str, int] = {}

    def get_history(self, symbol, start, end, interval):
        self.calls[symbol] = self.calls.get(symbol, 0) + 1
        return [b for b in self.bars.get(symbol, []) if b.ts >= start]


def test_daily_closes_many_downloads_once_then_reads_from_cache(make_argus):
    now = datetime.now(UTC).replace(hour=20, minute=0, second=0, microsecond=0)
    old, new = now - timedelta(days=60), now - timedelta(days=10)  # NEW listed 10 days ago
    hist = PerSymbolHistory({"OLD": _bars(old, 61), "NEW": _bars(new, 11)})
    a = make_argus(history=hist)
    start = (now - timedelta(days=40)).date()
    first = a.market.daily_closes_many(["OLD", "NEW"], start)
    assert min(first["OLD"]) >= start and len(first["NEW"]) == 11
    again = a.market.daily_closes_many(["OLD", "NEW"], start)
    assert again == first and hist.calls == {"OLD": 1, "NEW": 1}  # the recent listing isn't re-downloaded
    assert a.market.daily_closes("NEW", start) == first["NEW"] and hist.calls["NEW"] == 1


# -- fundamentals -------------------------------------------------------------------------
class SlowFund:
    def __init__(self, name, metrics, delay=0.2):
        self.name, self.metrics, self.delay = name, metrics, delay

    def get_metrics(self, symbol):
        time.sleep(self.delay)
        if self.metrics is None:
            raise ProviderError(f"{self.name} down")
        return self.metrics


def test_fundamentals_ask_providers_in_parallel_and_merge(make_argus):
    a = make_argus(fundamentals=[SlowFund("finnhub", {"pe_ttm": 20.0, "market_cap": 1.0}),
                                 SlowFund("yahoo", {"pe_ttm": 21.0, "market_cap": 2.0})])
    t0 = time.perf_counter()
    f = a.market.get_fundamentals("NVDA")
    assert time.perf_counter() - t0 < 0.35  # both 0.2 s calls overlapped
    assert f["metrics"]["pe_ttm"] == 20.0 and f["metrics"]["market_cap"] == 2.0  # price-currency: Yahoo first


def test_portfolio_fundamentals_serves_cache_and_refreshes_in_background(make_argus):
    from argus.services.portfolio import TxnInput

    a = make_argus(fundamentals=[SlowFund("finnhub", {"pe_ttm": 20.0}, delay=0.05)])
    a.portfolios.create_portfolio("growth")
    a.portfolios.add_transactions("growth", [TxnInput("BUY", s, datetime(2026, 9, 1, tzinfo=UTC), 1, 10) for s in ("A", "B")])
    r = a.portfolio_fundamentals("growth")
    assert r["pending"] == ["A", "B"] and r["metrics"] == {}
    for _ in range(100):
        if not a.job_running("fundamentals"):
            break
        time.sleep(0.02)
    r = a.portfolio_fundamentals("growth")
    assert r["pending"] == [] and r["metrics"]["A"]["pe_ttm"] == 20.0


def test_symbols_no_provider_knows_stop_being_pending(make_argus):
    from argus.services.portfolio import TxnInput

    a = make_argus(fundamentals=[SlowFund("finnhub", None, delay=0)])
    a.portfolios.create_portfolio("growth")
    a.portfolios.add_transactions("growth", [TxnInput("BUY", "ZZZ", datetime(2026, 9, 1, tzinfo=UTC), 1, 10)])
    assert a.portfolio_fundamentals("growth")["pending"] == ["ZZZ"]
    while a.job_running("fundamentals"):
        time.sleep(0.01)
    assert a.portfolio_fundamentals("growth")["pending"] == []  # tried and failed: no endless polling


def test_background_jobs_are_single_flight(make_argus):
    a = make_argus()
    gate = threading.Event()
    assert a.run_background("x", gate.wait) is True
    assert a.run_background("x", lambda: None) is False
    gate.set()
    while a.job_running("x"):
        time.sleep(0.01)
    assert a.run_background("x", lambda: None) is True


def test_warm_caches_runs_every_step_and_survives_failures(make_argus):
    from argus.services.portfolio import TxnInput

    a = make_argus(fundamentals=[SlowFund("finnhub", {"pe_ttm": 20.0}, delay=0)])
    a.portfolios.create_portfolio("growth")
    a.portfolios.add_transactions("growth", [TxnInput("BUY", "A", datetime(2026, 9, 1, tzinfo=UTC), 1, 10)])
    r = a.warm_caches()  # no history or Yahoo providers in this fixture: those steps fail, the rest run
    assert r["fundamentals"] == "ok" and set(r) >= {"dividends", "earnings", "fund_profiles", "history", "seconds"}
    assert a.market.cached_fundamentals(["A"])["A"]["fresh"]


def test_a_failing_provider_keeps_its_last_values(make_argus):
    finnhub = SlowFund("finnhub", {"pe_ttm": 20.0, "return_1y_pct": 27.0}, delay=0)
    a = make_argus(fundamentals=[finnhub, SlowFund("yahoo", {"pe_ttm": 21.0, "sma50": 200.0}, delay=0)])
    a.market.get_fundamentals("NVDA")
    finnhub.metrics = None  # rate limited this time
    m = a.market.get_fundamentals("NVDA", refresh=True)
    assert m["metrics"]["return_1y_pct"] == 27.0 and m["sources"]["return_1y_pct"] == "finnhub"  # kept
    assert m["metrics"]["pe_ttm"] == 21.0 and m["metrics"]["sma50"] == 200.0  # fresh from Yahoo


def test_return_bases(make_argus, monkeypatch):
    from datetime import date

    import argus.app as app_mod

    days = [date(2025, 12, 29) + timedelta(days=i) for i in range(120)]
    days = [d for d in days if d.weekday() < 5]
    bars = [Bar(datetime(d.year, d.month, d.day, 21, tzinfo=UTC), 1, 1, 1, 100 + i, 1) for i, d in enumerate(days)]
    a = make_argus(history=PerSymbolHistory({"X": bars}))
    monkeypatch.setattr(app_mod, "market_status", lambda: {"session": "closed", "last_session": "2026-04-17"})
    r = a.return_bases("x")
    closes = {d: 100 + i for i, d in enumerate(days)}
    b = r["bases"]
    assert r["anchor"] == "2026-04-17"
    assert b["1D"] == {"date": "2026-04-16", "close": closes[date(2026, 4, 16)]}       # session before the anchor
    assert b["5D"]["date"] == "2026-04-10"                                             # five sessions back
    assert b["YTD"] == {"date": "2025-12-31", "close": closes[date(2025, 12, 31)]}     # last year's final close
    assert b["1M"]["date"] == "2026-03-17" and b["3M"]["date"] == "2026-01-16"          # on or before the date
    assert b["1Y"] is None and b["5Y"] is None                                         # longer than the history
    assert b["Max"]["date"] == "2025-12-29"
