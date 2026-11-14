"""Stock splits (B-140): re-based history replaces the cache, unrecorded splits are flagged, and
performance has no jump on the split day once a SPLIT is recorded."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

import pytest
from sqlalchemy import select

from argus.db import session_scope, upsert
from argus.market_calendar import NY, market_status, session_before, session_date
from argus.models import DividendHistory
from argus.providers.base import Bar
from argus.services import market
from argus.services.performance import compute_series
from argus.services.portfolio import TxnInput
from argus.services.splits import clean_ratio, rebased, ratio_label, unadjusted, unrecorded
from tests.conftest import FakeHistory, FakeQuotes


def test_split_basis_helpers():
    assert rebased(227.02, 56.755) and rebased(10, 100) and rebased(150, 100)
    assert not rebased(227.02, 226.5) and not rebased(0, 5)
    assert clean_ratio(227.02 / 56.755) == 4 and clean_ratio(4.03) == 4 and clean_ratio(0.0998) == 0.1
    assert clean_ratio(1.49) == 1.5
    assert (ratio_label(4), ratio_label(0.1), ratio_label(1.5)) == ("4:1", "1:10", "3:2")


def _last_close():
    return datetime.fromisoformat(market_status()["last_close"])


def test_rebased_history_replaces_every_cached_bar_and_records_the_split(make_argus):
    """QUAL 4:1: the cache holds ~227 bars a session behind; Yahoo's next answer is split-adjusted
    (~56) for the same sessions. Every cached bar is replaced, not just the few re-fetched."""
    last = _last_close()
    days = [last - timedelta(days=i) for i in range(60, 0, -1)]
    hist = FakeHistory([Bar(t, 225, 228, 224, 227.0, 1e6) for t in days])
    a = make_argus(history=hist)
    with session_scope(a.engine) as s:
        upsert(s, DividendHistory, symbol="QUAL", as_of=datetime.now(UTC), data=[["2026-09-15", 0.473 * 4]])
    assert a.market.get_history("QUAL", "1mo")[0].c == 227.0

    hist.bars = [Bar(t, 56.25, 57, 56, 56.75, 4e6) for t in days] + [Bar(last, 56.78, 57, 54.7, 54.79, 6e6, split=4.0)]
    a.market._behind["QUAL"] -= market.BEHIND_RETRY_S
    bars = a.market.get_history("QUAL", "3mo")
    assert [b.c for b in bars] == [56.75] * len(days) + [54.79]
    assert a.market.splits(["QUAL", "SPY"]) == {"QUAL": [(last.astimezone(NY).date(), 4.0)]}
    with session_scope(a.engine) as s:  # per-share dividends were on the old basis too: re-fetched next read
        assert s.scalar(select(DividendHistory.as_of).where(DividendHistory.symbol == "QUAL")).year == 1970


def test_a_small_correction_only_updates_the_refetched_bars(make_argus):
    last = _last_close()
    days = [last - timedelta(days=i) for i in range(30, 0, -1)]
    hist = FakeHistory([Bar(t, 100, 101, 99, 100.0, 1e6) for t in days])
    a = make_argus(history=hist)
    a.market.get_history("AAA", "1mo")
    hist.bars = [Bar(t, 100, 101, 99, 100.2, 1e6) for t in days] + [Bar(last, 100, 101, 99, 101.0, 1e6)]
    a.market._behind["AAA"] -= market.BEHIND_RETRY_S
    bars = a.market.get_history("AAA", "1mo")
    assert bars[-1].c == 101.0 and bars[0].c == 100.0  # older bars untouched: no full replace
    assert hist.calls == 2 and a.market.splits(["AAA"]) == {}


@pytest.mark.parametrize("day", [None, "2026-11-09", "2026-11-27", "2026-11-28", "2027-01-01", "2027-01-03",
                                 "2027-06-30"])
def test_52_week_range_comes_from_adjusted_bars_after_a_recent_split(make_argus, freeze_today, day):
    """Yahoo's info kept QUAL's pre-split 52-week high (228.13) after the split."""
    if day:
        freeze_today(date.fromisoformat(day))
    # Bar i is i days before now, the instant the 52-week window counts back from (not the last close,
    # which is days earlier over a weekend): bar 364 is the oldest inside it, bar 365 just outside.
    now = datetime.now(UTC)
    a = make_argus()
    a.market._store_bars("QUAL", "1d", [Bar(now - timedelta(days=i), 55, 57 + i / 100, 54 - i / 1000, 56, 1e6,
                                            split=4.0 if i == 0 else 0.0) for i in range(400, -1, -1)])
    lo, hi = a.market.post_split_ranges(["QUAL", "SPY"])["QUAL"]
    assert hi == pytest.approx(57 + 364 / 100) and lo == pytest.approx(54 - 364 / 1000)
    m, src = market.with_range({"high_52w": 228.13, "low_52w": 54.75}, {}, (lo, hi))
    assert m["high_52w"] == hi and src["high_52w"] == "history"


@dataclass
class T:
    id: int
    type: str
    symbol: str
    ts: datetime
    qty: float = 0.0
    price: float = 0.0
    fee: float = 0.0
    amount: float = 0.0


SPLIT_DAY = date(2026, 11, 5)


def _ny(d: date, h=10, m=0):
    return datetime.combine(d, time(h, m), NY)


def test_unrecorded_split_is_flagged_until_a_split_txn_records_it():
    buy = T(1, "BUY", "QUAL", _ny(date(2026, 10, 20)), 53, 225.695)
    splits = {"QUAL": [(SPLIT_DAY, 4.0)]}
    [w] = unrecorded([buy], splits, "loop-macro")
    assert (w["symbol"], w["date"], w["ratio"], w["label"], w["source"]) == ("QUAL", "2026-11-05", 4.0, "4:1", "yahoo")
    assert (w["qty_before"], w["qty_after"]) == (53, 212)
    assert w["record"] == "argus txn add loop-macro SPLIT QUAL --qty 4 --date 2026-11-05T09:30"
    assert unrecorded([buy, T(2, "SPLIT", "QUAL", _ny(SPLIT_DAY, 9, 30), 4)], splits, "loop-macro") == []
    # Bought after the split, or sold out before it: the share count is already right.
    assert unrecorded([T(1, "BUY", "QUAL", _ny(SPLIT_DAY, 11), 10, 55)], splits, "p") == []
    assert unrecorded([buy, T(2, "SELL", "QUAL", _ny(date(2026, 10, 30)), 53, 222),
                       T(3, "BUY", "QUAL", _ny(date(2026, 11, 6)), 5, 55)], splits, "p") == []


def test_quote_previous_close_flags_a_split_yahoo_has_not_reported():
    buy = T(1, "BUY", "QUAL", _ny(date(2026, 10, 20)), 53, 225.695)
    [w] = unrecorded([buy], {}, "p", possible={"QUAL": (SPLIT_DAY, 4.0)})
    assert w["source"] == "quote" and w["ratio"] == 4.0 and "hasn't reported" in w["message"]
    # Once Yahoo reports it, the Yahoo row replaces the guess.
    [w] = unrecorded([buy], {"QUAL": [(SPLIT_DAY, 4.0)]}, "p", possible={"QUAL": (SPLIT_DAY, 4.0)})
    assert w["source"] == "yahoo"


def test_portfolio_summary_and_drift_carry_the_split_warning(make_argus):
    a = make_argus([FakeQuotes("fake", {"QUAL": (54.79, 56.755)})])
    a.portfolios.create_portfolio("p")
    a.portfolios.add_transactions("p", [TxnInput("BUY", "QUAL", datetime.now(UTC) - timedelta(days=20), 53, 225.695)])
    split_day = session_date(datetime.now(UTC)) - timedelta(days=1)
    a.market._store_bars("QUAL", "1d", [Bar(_ny(split_day, 0), 56.78, 57, 54.7, 54.79, 6e6, split=4.0)])
    [w] = a.portfolio("p")["split_warnings"]
    assert (w["symbol"], w["ratio"], w["qty_before"], w["portfolio"]) == ("QUAL", 4.0, 53, "p")
    assert a.portfolio("all")["split_warnings"][0]["portfolio"] == "p"
    assert w["message"] in a.drift("p")["warnings"]
    a.portfolios.add_transactions("p", [TxnInput("SPLIT", "QUAL", _ny(split_day, 9, 30), 4)])
    assert a.portfolio("p")["split_warnings"] == []
    assert a.portfolio("p")["positions"][0]["qty"] == 212


def test_portfolio_flags_a_possible_split_from_the_quote(make_argus):
    a = make_argus([FakeQuotes("fake", {"QUAL": (54.79, 56.755)})])
    a.portfolios.create_portfolio("p")
    a.portfolios.add_transactions("p", [TxnInput("BUY", "QUAL", datetime.now(UTC) - timedelta(days=20), 53, 225.695)])
    prev = session_before(session_date(datetime.now(UTC)))
    a.market._store_bars("QUAL", "1d", [Bar(_ny(prev, 0), 225, 228, 224, 227.02, 1e6)])
    [w] = a.portfolio("p")["split_warnings"]
    assert (w["source"], w["ratio"], w["date"]) == ("quote", 4.0, session_date(datetime.now(UTC)).isoformat())


DAYS = [date(2026, 10, 30), date(2026, 11, 2), date(2026, 11, 3), date(2026, 11, 4), date(2026, 11, 5)]
TXNS = [T(1, "BUY", "QUAL", datetime(2026, 10, 30, 20, tzinfo=UTC), 53, 225.695),
        T(2, "SPLIT", "QUAL", _ny(SPLIT_DAY, 9, 30), 4)]


@pytest.mark.parametrize("closes", [
    [55.6225, 55.5025, 55.4775, 56.755, 54.79],    # Yahoo's adjusted history
    [222.49, 222.01, 221.91, 227.02, 54.79],       # cached before Yahoo adjusted it
], ids=["adjusted", "unadjusted"])
def test_recorded_split_has_no_jump_on_the_split_day(closes):
    pts = compute_series(TXNS, DAYS, {"QUAL": dict(zip(DAYS, closes))})
    assert pts[-1].value == pytest.approx(212 * 54.79)
    assert max(abs(p.ret) for p in pts) < 0.04  # the day's real move (-3.5%), not +300% or -75%
    assert pts[-1].index == pytest.approx(212 * 54.79 / (53 * 225.695), rel=1e-3)


def test_unadjusted_detects_the_old_basis_only():
    assert unadjusted({DAYS[3]: 227.02, DAYS[4]: 54.79}, SPLIT_DAY, 4)
    assert not unadjusted({DAYS[3]: 56.755, DAYS[4]: 54.79}, SPLIT_DAY, 4)
    assert not unadjusted({DAYS[4]: 54.79}, SPLIT_DAY, 4)  # nothing before the split to compare


def test_yahoo_history_carries_the_split_column(monkeypatch):
    import pandas as pd

    from argus.providers import yahoo

    idx = pd.DatetimeIndex(["2026-11-04", "2026-11-05"]).tz_localize("America/New_York")
    df = pd.DataFrame({"Open": [56.2, 56.78], "High": [56.9, 57.0], "Low": [56.2, 54.7], "Close": [56.755, 54.79],
                       "Volume": [4.5e6, 6e6], "Stock Splits": [0.0, 4.0]}, index=idx)
    monkeypatch.setattr(yahoo, "_yf", lambda: type("yf", (), {"Ticker": lambda sym: type("T", (), {
        "history": lambda self, **kw: df})()}))
    bars = yahoo.YahooProvider().get_history("QUAL", datetime(2026, 11, 1, tzinfo=UTC), None)
    assert [b.split for b in bars] == [0.0, 4.0]
