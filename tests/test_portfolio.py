from datetime import UTC, datetime, timedelta

import pytest

from argus.errors import ArgusError
from argus.providers.base import Quote
from argus.services.portfolio import TxnInput


def at(y, m, d, h=16):
    return datetime(y, m, d, h, tzinfo=UTC)


@pytest.fixture
def argus(make_argus):
    a = make_argus()
    a.portfolios.create_portfolio("growth")
    return a


def test_dry_run_previews_without_writing(argus):
    r = argus.portfolios.add_transactions("growth", [TxnInput("BUY", "nvda.o", at(2026, 9, 1), 10, 100)], dry_run=True)
    assert r["positions"][0]["after"]["qty"] == 10 and r["positions"][0]["before"]["qty"] == 0
    assert argus.portfolios.list_transactions("growth") == []


def test_idempotency_key_makes_retries_noops(argus):
    item = lambda: TxnInput("BUY", "NVDA", at(2026, 9, 1), 10, 100, external_id="k1")  # noqa: E731
    argus.portfolios.add_transactions("growth", [item()])
    r = argus.portfolios.add_transactions("growth", [item()])
    assert r["skipped_existing"] == ["k1"] and r["inserted_ids"] == []
    assert len(argus.portfolios.list_transactions("growth")) == 1


def test_oversell_rejected_and_nothing_written(argus):
    argus.portfolios.add_transactions("growth", [TxnInput("BUY", "NVDA", at(2026, 9, 1), 10, 100)])
    with pytest.raises(ArgusError) as e:
        argus.portfolios.add_transactions("growth", [TxnInput("SELL", "NVDA", at(2026, 9, 2), 11, 120)])
    assert e.value.code == "INSUFFICIENT_SHARES"
    assert len(argus.portfolios.list_transactions("growth")) == 1


def test_delete_that_would_break_history_is_refused(argus):
    buy = argus.portfolios.add_transactions("growth", [TxnInput("BUY", "X", at(2026, 9, 1), 10, 100)])["inserted_ids"][0]
    argus.portfolios.add_transactions("growth", [TxnInput("SELL", "X", at(2026, 9, 2), 10, 120)])
    with pytest.raises(ArgusError):
        argus.portfolios.delete_transaction(buy)


def test_soft_delete_hides_but_keeps(argus):
    tid = argus.portfolios.add_transactions("growth", [TxnInput("BUY", "X", at(2026, 9, 1), 1, 1)])["inserted_ids"][0]
    argus.portfolios.delete_transaction(tid)
    assert argus.portfolios.list_transactions("growth") == []
    assert argus.portfolios.list_transactions("growth", include_deleted=True)[0]["deleted"] is True


def test_summary_day_pnl_uses_cost_for_lots_bought_in_quote_session(argus):
    session_close = at(2026, 9, 25, 20)  # Fri 16:00 ET
    argus.portfolios.add_transactions("growth", [
        TxnInput("OPENING", "X", at(2026, 8, 25), 10, 50),                     # old holding
        TxnInput("BUY", "X", session_close - timedelta(hours=3), 5, 104),     # bought that Friday
    ])
    q = {"X": Quote("X", 110.0, 100.0, None, None, None, session_close, "fake")}
    s = argus.portfolios.summary("growth", q)
    row = s["positions"][0]
    assert row["day_pnl"] == pytest.approx(10 * (110 - 100) + 5 * (110 - 104))
    assert row["unrealized_pnl"] == pytest.approx(15 * 110 - (500 + 520))
    assert row["weight_pct"] == pytest.approx(100)
    assert s["totals"]["day_pnl_pct"] == pytest.approx(130 / (1650 - 130) * 100)


def test_summary_without_quotes_leaves_market_fields_empty(argus):
    argus.portfolios.add_transactions("growth", [TxnInput("BUY", "X", at(2026, 9, 1), 2, 10)])
    s = argus.portfolios.summary("growth")
    assert s["totals"]["market_value"] is None and s["totals"]["cost_basis"] == 20


def test_unknown_portfolio_lists_existing(argus):
    with pytest.raises(ArgusError) as e:
        argus.portfolios.get_portfolio("nope")
    assert "growth" in e.value.hint


def test_weekend_quote_counts_friday_buys_against_cost(argus):
    # Yahoo stamps quotes with fetch time; a Sunday fetch still belongs to Friday's session.
    argus.portfolios.add_transactions("growth", [
        TxnInput("OPENING", "X", at(2026, 8, 27), 6, 212.93),
        TxnInput("BUY", "X", at(2026, 9, 25, 20), 3, 176),
    ])
    sunday = at(2026, 9, 27, 18)
    q = {"X": Quote("X", 177.71, 172.16, None, None, None, sunday, "yahoo")}
    row = argus.portfolios.summary("growth", q)["positions"][0]
    assert row["day_pnl"] == pytest.approx(6 * (177.71 - 172.16) + 3 * (177.71 - 176))  # 38.43, as Investing.com
