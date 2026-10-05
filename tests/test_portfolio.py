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


def test_all_view_merges_positions_across_portfolios(argus):
    argus.portfolios.create_portfolio("income")
    argus.portfolios.add_transactions("growth", [TxnInput("BUY", "X", at(2026, 9, 1), 10, 50),
                                                 TxnInput("BUY", "Y", at(2026, 9, 1), 5, 20)])
    argus.portfolios.add_transactions("income", [TxnInput("BUY", "X", at(2026, 9, 2), 10, 70),
                                                 TxnInput("SELL", "X", at(2026, 9, 3), 4, 80)])
    now = at(2026, 9, 25, 20)
    q = {"X": Quote("X", 100.0, 100.0, None, None, None, now, "fake"),
         "Y": Quote("Y", 40.0, 40.0, None, None, None, now, "fake")}
    s = argus.portfolios.summary("all", q)
    x = next(r for r in s["positions"] if r["symbol"] == "X")
    assert s["portfolio"]["name"] == "all" and s["totals"]["position_count"] == 2
    assert x["qty"] == 16 and x["cost_basis"] == pytest.approx(500 + 6 * 70)  # FIFO stayed within "income"
    assert x["realized_pnl"] == pytest.approx(4 * (80 - 70))
    assert x["weight_pct"] == pytest.approx(1600 / (1600 + 200) * 100)


def test_all_view_is_read_only_and_reserved(argus):
    with pytest.raises(ArgusError) as e:
        argus.portfolios.add_transactions("all", [TxnInput("BUY", "X", at(2026, 9, 1), 1, 1)])
    assert e.value.code == "INVALID_ARG"
    with pytest.raises(ArgusError):
        argus.portfolios.create_portfolio("All")


def test_edit_transaction_replaces_row_and_keeps_history_valid(argus):
    ids = argus.portfolios.add_transactions("growth", [TxnInput("BUY", "X", at(2026, 9, 1), 10, 50)])["inserted_ids"]
    argus.portfolios.add_transactions("growth", [TxnInput("SELL", "X", at(2026, 9, 5), 8, 60)])

    preview = argus.portfolios.edit_transaction(ids[0], price=40, dry_run=True)
    assert preview["position"]["after"]["realized_pnl"] == pytest.approx(8 * (60 - 40))
    assert argus.portfolios.list_transactions("growth")[0]["price"] == 50  # dry run wrote nothing

    with pytest.raises(ArgusError):
        argus.portfolios.edit_transaction(ids[0], qty=5)  # the later SELL of 8 needs at least 8
    out = argus.portfolios.edit_transaction(ids[0], qty=12, price=40)
    rows = argus.portfolios.list_transactions("growth", include_deleted=True)
    assert [(r["qty"], r["deleted"]) for r in rows if r["type"] == "BUY"] == [(10, True), (12, False)]
    assert out["after"]["ts"] == out["before"]["ts"]  # untouched fields carry over
    assert argus.portfolios.positions("growth")["X"].qty == 4


class FakeProfiles:
    def __init__(self):
        self.calls = []

    def get_info(self, symbol):
        self.calls.append(symbol)
        return {"quoteType": "ETF"} if symbol == "BSV" else {"sector": "Technology"}


def test_trades_fill_instrument_metadata_so_funds_are_not_stocks(make_argus):
    from argus.services.analysis import is_fund

    a = make_argus()
    a.market.profile_provider = prof = FakeProfiles()
    a.portfolios.create_portfolio("growth")
    a.portfolios.add_transactions("growth", [TxnInput("BUY", "BSV", at(2026, 10, 1), 20, 76.11)])
    row = a.portfolio("growth", with_quotes=False)["positions"][0]
    assert row["sector"] == "ETF" and is_fund(row, {})
    a.portfolios.add_transactions("growth", [TxnInput("BUY", "BSV", at(2026, 10, 2), 1, 76)])
    a.portfolio("growth", with_quotes=False)
    assert prof.calls == ["BSV"]  # known sector: no further lookups


def test_metadata_failure_never_blocks_a_trade(make_argus):
    class Broken:
        def get_info(self, symbol):
            raise RuntimeError("yahoo down")

    a = make_argus()
    a.market.profile_provider = Broken()
    a.portfolios.create_portfolio("growth")
    assert a.portfolios.add_transactions("growth", [TxnInput("BUY", "X", at(2026, 9, 1), 1, 10)])["inserted_ids"]
    assert a.portfolio("growth", with_quotes=False)["positions"][0]["symbol"] == "X"


def test_events_follow_the_selected_portfolio(make_argus):
    from argus.db import session_scope
    from argus.market_calendar import NY
    from argus.models import Event

    a = make_argus([FakeQuotesAll()])
    for name, sym in (("growth", "MU"), ("fixed-income", "BND")):
        a.portfolios.create_portfolio(name)
        a.portfolios.add_transactions(name, [TxnInput("BUY", sym, at(2026, 9, 1), 1, 10)])
    a.watchlists.add(["BNS"])
    soon = datetime.now(NY).date() + timedelta(days=3)
    with session_scope(a.engine) as s:
        for sym in ("MU", "BND", "BNS"):
            s.add(Event(symbol=sym, kind="ex_dividend", d=soon, data={}, source="test"))

    syms = lambda **kw: [e["symbol"] for e in a.upcoming_events(refresh=False, **kw)["upcoming"]]  # noqa: E731
    assert syms(portfolio="fixed-income") == ["BND"]
    assert syms(portfolio="growth") == ["MU"]
    assert syms(portfolio="all") == syms() == ["BND", "BNS", "MU"]
    assert syms(symbols=["mu"]) == ["MU"]


class FakeQuotesAll:
    name = "fake"

    def get_quotes(self, symbols):
        return {s: Quote(s, 10.0, 10.0, None, None, None, datetime.now(UTC), "fake") for s in symbols}
