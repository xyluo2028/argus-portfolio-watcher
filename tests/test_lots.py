from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from argus.errors import ArgusError
from argus.services.lots import build_positions


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


def d(month, day, hour=16):
    return datetime(2026, month, day, hour, tzinfo=UTC)


def test_fifo_realizes_oldest_lots_first():
    # The worked example from the design discussion.
    pos = build_positions([
        T(1, "BUY", "NVDA", d(1, 5), 10, 100),
        T(2, "BUY", "NVDA", d(3, 5), 10, 150),
        T(3, "SELL", "NVDA", d(6, 5), 15, 200),
    ])["NVDA"]
    assert pos.realized_pnl == pytest.approx(10 * 100 + 5 * 50)  # 1,250
    assert pos.qty == pytest.approx(5)
    assert pos.avg_cost == pytest.approx(150)
    assert [r.lot_txn_id for r in pos.realized] == [1, 2]


def test_input_order_does_not_matter():
    txns = [T(3, "SELL", "X", d(6, 5), 15, 200), T(2, "BUY", "X", d(3, 5), 10, 150), T(1, "BUY", "X", d(1, 5), 10, 100)]
    assert build_positions(txns)["X"].realized_pnl == pytest.approx(1250)


def test_fees_raise_cost_and_reduce_proceeds():
    pos = build_positions([
        T(1, "BUY", "X", d(1, 5), 10, 100, fee=10),   # cost/share 101
        T(2, "SELL", "X", d(2, 5), 10, 110, fee=20),  # proceeds/share 108
    ])["X"]
    assert pos.realized_pnl == pytest.approx(70)
    assert not pos.is_open


def test_opening_lots_behave_like_buys_for_cost():
    pos = build_positions([T(1, "OPENING", "X", d(1, 5), 5, 60), T(2, "BUY", "X", d(2, 5), 5, 80)])["X"]
    assert pos.avg_cost == pytest.approx(70)
    assert [lot.kind for lot in pos.lots] == ["OPENING", "BUY"]


def test_split_scales_quantity_and_cost():
    pos = build_positions([
        T(1, "BUY", "X", d(1, 5), 10, 400),
        T(2, "SPLIT", "X", d(2, 5), qty=4),
        T(3, "SELL", "X", d(3, 5), 20, 120),
    ])["X"]
    assert pos.qty == pytest.approx(20)
    assert pos.avg_cost == pytest.approx(100)
    assert pos.realized_pnl == pytest.approx(20 * 20)


def test_cannot_sell_more_than_held_at_that_time():
    with pytest.raises(ArgusError) as e:
        build_positions([
            T(1, "SELL", "X", d(1, 5), 5, 100),  # before the buy
            T(2, "BUY", "X", d(2, 5), 10, 100),
        ])
    assert e.value.code == "INSUFFICIENT_SHARES"


def test_same_timestamp_buy_applies_before_sell():
    pos = build_positions([T(2, "SELL", "X", d(1, 5), 5, 110), T(1, "BUY", "X", d(1, 5), 5, 100)])["X"]
    assert pos.realized_pnl == pytest.approx(50)


def test_dividends_and_fees_tracked_separately():
    pos = build_positions([
        T(1, "BUY", "X", d(1, 5), 1, 100),
        T(2, "DIVIDEND", "X", d(2, 5), amount=3.5),
        T(3, "FEE", "X", d(2, 6), amount=1.0),
    ])["X"]
    assert (pos.dividends, pos.fees, pos.realized_pnl) == (3.5, 1.0, 0)


def test_float_residue_closes_position():
    pos = build_positions([
        T(1, "BUY", "X", d(1, 5), 0.1, 10), T(2, "BUY", "X", d(1, 6), 0.2, 10),
        T(3, "SELL", "X", d(1, 7), 0.3, 10),
    ])["X"]
    assert not pos.is_open and pos.lots == []
