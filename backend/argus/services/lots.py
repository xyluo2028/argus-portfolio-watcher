"""FIFO lot engine: replays transactions in time order into open lots and realized P&L.

Pure functions over plain values so the accounting can be tested without a database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Protocol

from argus.errors import ArgusError
from argus.models import TxnType

EPS = 1e-9


class TxnLike(Protocol):
    id: int | None
    type: str
    symbol: str
    qty: float
    price: float
    fee: float
    amount: float
    ts: datetime


@dataclass
class Lot:
    txn_id: int | None
    symbol: str
    opened: datetime
    kind: str  # OPENING or BUY
    qty: float
    cost_per_share: float  # includes the buy fee, adjusted for splits

    @property
    def cost(self) -> float:
        return self.qty * self.cost_per_share


@dataclass
class Realization:
    sell_txn_id: int | None
    lot_txn_id: int | None
    symbol: str
    ts: datetime
    qty: float
    proceeds: float
    cost: float

    @property
    def pnl(self) -> float:
        return self.proceeds - self.cost


@dataclass
class PositionState:
    symbol: str
    lots: list[Lot] = field(default_factory=list)
    realized: list[Realization] = field(default_factory=list)
    dividends: float = 0.0
    fees: float = 0.0

    @property
    def qty(self) -> float:
        return sum(lot.qty for lot in self.lots)

    @property
    def cost_basis(self) -> float:
        return sum(lot.cost for lot in self.lots)

    @property
    def avg_cost(self) -> float | None:
        q = self.qty
        return self.cost_basis / q if q > EPS else None

    @property
    def realized_pnl(self) -> float:
        return sum(r.pnl for r in self.realized)

    @property
    def is_open(self) -> bool:
        return self.qty > EPS


def _order_key(t: TxnLike):
    # Same timestamp: apply buys/splits before sells so a same-day round trip works.
    rank = {TxnType.SELL: 1}.get(t.type, 0)
    return (t.ts, rank, t.id if t.id is not None else float("inf"))


def build_positions(txns: Iterable[TxnLike]) -> dict[str, PositionState]:
    positions: dict[str, PositionState] = {}
    for t in sorted(txns, key=_order_key):
        pos = positions.setdefault(t.symbol, PositionState(t.symbol))
        kind = TxnType(t.type)

        if kind in (TxnType.BUY, TxnType.OPENING):
            if t.qty <= 0 or t.price < 0:
                raise ArgusError("INVALID_TXN", f"{kind} needs qty > 0 and price >= 0 (txn {t.id}).")
            cps = t.price + (t.fee or 0.0) / t.qty
            pos.lots.append(Lot(t.id, t.symbol, t.ts, kind.value, t.qty, cps))

        elif kind == TxnType.SELL:
            _apply_sell(pos, t)

        elif kind == TxnType.SPLIT:
            ratio = t.qty
            if ratio <= 0:
                raise ArgusError("INVALID_TXN", f"SPLIT ratio must be > 0 (txn {t.id}).")
            for lot in pos.lots:
                lot.qty *= ratio
                lot.cost_per_share /= ratio

        elif kind == TxnType.DIVIDEND:
            pos.dividends += t.amount

        elif kind == TxnType.FEE:
            pos.fees += t.amount

    return positions


def _apply_sell(pos: PositionState, t: TxnLike) -> None:
    if t.qty <= 0:
        raise ArgusError("INVALID_TXN", f"SELL needs qty > 0 (txn {t.id}).")
    held = pos.qty
    if t.qty > held + EPS:
        raise ArgusError(
            "INSUFFICIENT_SHARES",
            f"Selling {t.qty:g} {t.symbol} on {t.ts:%Y-%m-%d} but only {held:g} held at that time.",
            hint="Argus is long-only. Check the date and quantity, or record the missing BUY first.",
        )
    proceeds_per_share = t.price - (t.fee or 0.0) / t.qty
    remaining = t.qty
    while remaining > EPS:
        lot = pos.lots[0]
        take = min(lot.qty, remaining)
        pos.realized.append(
            Realization(t.id, lot.txn_id, t.symbol, t.ts, take, take * proceeds_per_share, take * lot.cost_per_share)
        )
        lot.qty -= take
        remaining -= take
        if lot.qty <= EPS:
            pos.lots.pop(0)
