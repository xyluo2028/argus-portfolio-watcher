"""Portfolios, the trade log, and derived positions/P&L."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import Engine, select

from argus.db import session_scope
from argus.errors import ArgusError
from argus.market_calendar import NY, market_status, session_date
from argus.models import AuditLog, Instrument, Portfolio, Transaction, TxnType
from argus.providers.base import Quote
from argus.services.lots import EPS, PositionState, build_positions
from argus.symbols import is_plausible_symbol, normalize_symbol

# Read-only view that combines every portfolio (positions, summary, performance, exposure).
ALL = "all"

CASH_TYPES = {TxnType.DIVIDEND, TxnType.FEE}


@dataclass
class TxnInput:
    """A proposed transaction (the same shape the CLI, MCP and importer build)."""

    type: str
    symbol: str
    ts: datetime
    qty: float = 0.0
    price: float = 0.0
    fee: float = 0.0
    amount: float = 0.0
    note: str | None = None
    external_id: str | None = None
    id: int | None = None  # set once persisted; lets TxnInput satisfy lots.TxnLike


def txn_to_dict(t: Transaction) -> dict:
    return {
        "id": t.id, "type": t.type, "symbol": t.symbol, "qty": t.qty, "price": t.price, "fee": t.fee,
        "amount": t.amount, "ts": t.ts.isoformat(), "note": t.note, "source": t.source,
        "external_id": t.external_id, "deleted": t.deleted,
    }


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def position_to_dict(p: PositionState | None, symbol: str) -> dict:
    if p is None:
        return {"symbol": symbol, "qty": 0.0, "avg_cost": None, "cost_basis": 0.0, "realized_pnl": 0.0}
    return {"symbol": symbol, "qty": round(p.qty, 8), "avg_cost": p.avg_cost, "cost_basis": p.cost_basis,
            "realized_pnl": p.realized_pnl}


log = logging.getLogger("argus.portfolio")


class PortfolioService:
    def __init__(self, engine: Engine, on_new_symbols: Callable[[list[str]], None] | None = None):
        """`on_new_symbols` gets the symbols of each saved batch, to fill missing type/sector (best effort)."""
        self.engine = engine
        self.on_new_symbols = on_new_symbols
        self.revision = 0  # bumped on every transaction write; lets callers cache derived results

    def _describe(self, symbols: list[str]) -> None:
        if self.on_new_symbols and symbols:
            try:
                self.on_new_symbols(symbols)
            except Exception as e:  # metadata is cosmetic; never fail a saved trade over it
                log.warning("instrument metadata for %s: %s", ", ".join(symbols), e)

    # -- portfolios -----------------------------------------------------------
    def create_portfolio(self, name: str, benchmark: str = "SPY", actor: str = "cli") -> dict:
        name = name.strip()
        if not name:
            raise ArgusError("INVALID_ARG", "Portfolio name is empty.")
        if name.lower() == ALL:
            raise ArgusError("INVALID_ARG", f"'{ALL}' is reserved for the combined view.")
        with session_scope(self.engine) as s:
            if s.scalar(select(Portfolio).where(Portfolio.name == name)):
                raise ArgusError("ALREADY_EXISTS", f"Portfolio '{name}' already exists.")
            p = Portfolio(name=name, benchmark=normalize_symbol(benchmark))
            s.add(p)
            s.flush()
            s.add(AuditLog(actor=actor, action="create", entity="portfolio", entity_id=str(p.id),
                           after={"name": p.name, "benchmark": p.benchmark}))
            return {"id": p.id, "name": p.name, "benchmark": p.benchmark}

    def list_portfolios(self) -> list[dict]:
        with session_scope(self.engine) as s:
            return [{"id": p.id, "name": p.name, "benchmark": p.benchmark}
                    for p in s.scalars(select(Portfolio).order_by(Portfolio.id))]

    def get_portfolio(self, ref: str | int) -> Portfolio:
        with session_scope(self.engine) as s:
            p = None
            if isinstance(ref, int) or str(ref).isdigit():
                p = s.get(Portfolio, int(ref))
            if p is None:
                p = s.scalar(select(Portfolio).where(Portfolio.name == str(ref)))
            if p is None and str(ref).lower() == ALL:
                raise ArgusError("INVALID_ARG", f"'{ALL}' is a read-only combined view.",
                                 hint="Pick a single portfolio for transactions, targets and what-if trades.")
            if p is None:
                names = [x.name for x in s.scalars(select(Portfolio))]
                raise ArgusError("NOT_FOUND", f"No portfolio '{ref}'.",
                                 hint=f"Existing: {', '.join(names)}" if names else "Create one with `argus portfolio create`.")
            return p

    def view(self, ref: str | int) -> Portfolio:
        """Like get_portfolio, but also accepts ALL (an unsaved Portfolio with id None)."""
        if str(ref).lower() == ALL:
            return Portfolio(id=None, name=ALL, benchmark="SPY")
        return self.get_portfolio(ref)

    # -- transactions ---------------------------------------------------------
    def _active_txns(self, s, portfolio_id: int) -> list[Transaction]:
        return list(s.scalars(select(Transaction).where(Transaction.portfolio_id == portfolio_id,
                                                        Transaction.deleted.is_(False))))

    def add_transactions(self, portfolio: str | int, items: list[TxnInput], source: str = "cli",
                         dry_run: bool = False) -> dict:
        result = self._add_transactions(portfolio, items, source, dry_run)
        if result["inserted_ids"]:
            self._describe(result.pop("_new_symbols"))
        result.pop("_new_symbols", None)
        return result

    def _add_transactions(self, portfolio: str | int, items: list[TxnInput], source: str,
                          dry_run: bool) -> dict:
        """Validate a batch against the full history, then insert it atomically.

        Items whose external_id already exists are skipped (idempotent retries/re-imports).
        Returns positions before/after for the affected symbols.
        """
        p = self.get_portfolio(portfolio)
        for it in items:
            it.symbol = normalize_symbol(it.symbol)
            it.type = TxnType(it.type.upper()).value
            it.ts = _aware(it.ts).astimezone(UTC)
            if not is_plausible_symbol(it.symbol):
                raise ArgusError("INVALID_SYMBOL", f"'{it.symbol}' doesn't look like a US ticker.")
            if TxnType(it.type) in CASH_TYPES and it.amount <= 0:
                raise ArgusError("INVALID_TXN", f"{it.type} needs a positive amount.")

        with session_scope(self.engine) as s:
            existing = self._active_txns(s, p.id)
            known_ids = {t.external_id for t in s.scalars(select(Transaction).where(
                Transaction.portfolio_id == p.id, Transaction.external_id.is_not(None)))}
            new = [it for it in items if not (it.external_id and it.external_id in known_ids)]
            skipped = [it.external_id for it in items if it.external_id and it.external_id in known_ids]
            seen = set()
            for it in new:
                if it.external_id and it.external_id in seen:
                    raise ArgusError("DUPLICATE_ID", f"external_id '{it.external_id}' appears twice in the batch.")
                seen.add(it.external_id)

            symbols = sorted({it.symbol for it in new})
            before = build_positions(existing)
            after = build_positions([*existing, *new])  # raises on e.g. selling more than held

            result = {
                "portfolio": p.name,
                "dry_run": dry_run,
                "to_insert": len(new),
                "skipped_existing": skipped,
                "positions": [{"before": position_to_dict(before.get(sym), sym),
                               "after": position_to_dict(after.get(sym), sym)} for sym in symbols],
            }
            if dry_run or not new:
                result["inserted_ids"] = []
                return result

            rows, result["_new_symbols"] = [], symbols
            for it in new:
                t = Transaction(portfolio_id=p.id, type=it.type, symbol=it.symbol, qty=it.qty, price=it.price,
                                fee=it.fee, amount=it.amount, ts=it.ts, note=it.note, source=source,
                                external_id=it.external_id)
                s.add(t)
                rows.append(t)
                if s.get(Instrument, it.symbol) is None:
                    s.add(Instrument(symbol=it.symbol))
            s.flush()
            for t in rows:
                s.add(AuditLog(actor=source, action="create", entity="txn", entity_id=str(t.id), after=txn_to_dict(t)))
            result["inserted_ids"] = [t.id for t in rows]
            self.revision += 1
            return result

    def delete_transaction(self, txn_id: int, source: str = "cli", dry_run: bool = False) -> dict:
        with session_scope(self.engine) as s:
            t = s.get(Transaction, txn_id)
            if t is None or t.deleted:
                raise ArgusError("NOT_FOUND", f"No active transaction {txn_id}.")
            remaining = [x for x in self._active_txns(s, t.portfolio_id) if x.id != txn_id]
            build_positions(remaining)  # e.g. deleting a BUY that a later SELL depends on fails here
            out = {"deleted": txn_to_dict(t), "dry_run": dry_run}
            if not dry_run:
                t.deleted = True
                self.revision += 1
                s.add(AuditLog(actor=source, action="delete", entity="txn", entity_id=str(t.id),
                               before=txn_to_dict(t) | {"deleted": False}))
            return out

    def edit_transaction(self, txn_id: int, qty: float | None = None, price: float | None = None,
                         fee: float | None = None, ts: datetime | None = None, note: str | None = None,
                         source: str = "cli", dry_run: bool = False) -> dict:
        """Correct a transaction: soft-delete it and insert the fixed copy, after replaying the history.

        Only qty, price, fee, time and note change; the type, symbol and portfolio stay as they were.
        """
        with session_scope(self.engine) as s:
            t = s.get(Transaction, txn_id)
            if t is None or t.deleted:
                raise ArgusError("NOT_FOUND", f"No active transaction {txn_id}.")
            fixed = TxnInput(type=t.type, symbol=t.symbol, ts=_aware(ts).astimezone(UTC) if ts else t.ts,
                             qty=t.qty if qty is None else qty, price=t.price if price is None else price,
                             fee=t.fee if fee is None else fee, amount=t.amount,
                             note=t.note if note is None else note)
            if TxnType(t.type) not in CASH_TYPES and (fixed.qty <= 0 or fixed.price < 0 or fixed.fee < 0):
                raise ArgusError("INVALID_TXN", "Shares must be positive; price and fee can't be negative.")
            others = [x for x in self._active_txns(s, t.portfolio_id) if x.id != txn_id]
            before = build_positions([*others, t]).get(t.symbol)
            after = build_positions([*others, fixed]).get(t.symbol)  # e.g. shrinking a BUY a later SELL needs
            out = {"before": txn_to_dict(t), "dry_run": dry_run,
                   "position": {"before": position_to_dict(before, t.symbol), "after": position_to_dict(after, t.symbol)}}
            if dry_run:
                return out
            t.deleted = True
            new = Transaction(portfolio_id=t.portfolio_id, type=fixed.type, symbol=fixed.symbol, qty=fixed.qty,
                              price=fixed.price, fee=fixed.fee, amount=fixed.amount, ts=fixed.ts, note=fixed.note,
                              source=source)
            s.add(new)
            s.flush()
            out["after"] = txn_to_dict(new)
            self.revision += 1
            s.add(AuditLog(actor=source, action="edit", entity="txn", entity_id=str(new.id),
                           before=out["before"], after=out["after"]))
            return out

    def list_transactions(self, portfolio: str | int, symbol: str | None = None,
                          include_deleted: bool = False) -> list[dict]:
        p = self.view(portfolio)
        with session_scope(self.engine) as s:
            names = {x.id: x.name for x in s.scalars(select(Portfolio))}
            q = select(Transaction)
            if p.id is not None:
                q = q.where(Transaction.portfolio_id == p.id)
            if symbol:
                q = q.where(Transaction.symbol == normalize_symbol(symbol))
            if not include_deleted:
                q = q.where(Transaction.deleted.is_(False))
            return [txn_to_dict(t) | {"portfolio": names.get(t.portfolio_id)}
                    for t in s.scalars(q.order_by(Transaction.ts, Transaction.id))]

    def active_transactions(self, portfolio: str | int) -> list[Transaction]:
        """Active transactions; ALL returns every portfolio's (fine for value series, not for FIFO)."""
        p = self.view(portfolio)
        with session_scope(self.engine) as s:
            if p.id is None:
                return list(s.scalars(select(Transaction).where(Transaction.deleted.is_(False))))
            return self._active_txns(s, p.id)

    # -- positions ------------------------------------------------------------
    def positions(self, portfolio: str | int) -> dict[str, PositionState]:
        p = self.view(portfolio)
        with session_scope(self.engine) as s:
            if p.id is not None:
                return build_positions(self._active_txns(s, p.id))
            # FIFO runs per portfolio; the combined view merges the resulting lots by symbol.
            merged: dict[str, PositionState] = {}
            for pid in s.scalars(select(Portfolio.id)):
                for sym, pos in build_positions(self._active_txns(s, pid)).items():
                    m = merged.setdefault(sym, PositionState(sym))
                    m.lots += pos.lots
                    m.realized += pos.realized
                    m.dividends += pos.dividends
                    m.fees += pos.fees
            return merged

    def summary(self, portfolio: str | int, quotes: dict[str, Quote] | None = None,
                now: datetime | None = None, include_lots: bool = False) -> dict:
        """Positions with market value and P&L. Without quotes, only cost-side fields are filled."""
        p = self.view(portfolio)
        state = self.positions(p.id if p.id is not None else ALL)
        quotes = quotes or {}
        now = now or datetime.now(UTC)

        with session_scope(self.engine) as s:
            instruments = {i.symbol: i for i in s.scalars(select(Instrument).where(Instrument.symbol.in_(state)))}

        rows = []
        tot = {"market_value": 0.0, "cost_basis": 0.0, "day_pnl": 0.0, "realized_pnl": 0.0, "dividends": 0.0}
        ext_pnl, ext_mv, ext_sessions = 0.0, 0.0, set()
        priced_all = True
        for sym, pos in sorted(state.items()):
            tot["realized_pnl"] += pos.realized_pnl
            tot["dividends"] += pos.dividends
            if not pos.is_open:
                continue
            q = quotes.get(sym)
            inst = instruments.get(sym)
            row = {
                "symbol": sym,
                "name": inst.name if inst else None,
                "type": inst.type if inst else None,
                "sector": inst.sector if inst else None,
                "qty": round(pos.qty, 8),
                "avg_cost": pos.avg_cost,
                "cost_basis": pos.cost_basis,
                "realized_pnl": pos.realized_pnl,
                "first_opened": min(l.opened for l in pos.lots).date().isoformat(),
                "lot_count": len(pos.lots),
            }
            tot["cost_basis"] += pos.cost_basis
            if q:
                mv = pos.qty * q.price
                day = 0.0
                quote_day = session_date(q.as_of)
                for lot in pos.lots:
                    # Shares bought in the quote's session gain from their cost, not from the prior close.
                    # OPENING lots are transfers, so their (old) cost is never a day reference.
                    bought_that_day = lot.kind == TxnType.BUY and lot.opened.astimezone(NY).date() == quote_day
                    ref = lot.cost_per_share if bought_that_day else (q.prev_close or q.price)
                    day += lot.qty * (q.price - ref)
                row |= {
                    "price": q.price, "prev_close": q.prev_close, "change_pct": q.change_pct,
                    "market_value": mv, "unrealized_pnl": mv - pos.cost_basis,
                    "unrealized_pct": (mv / pos.cost_basis - 1) * 100 if pos.cost_basis > EPS else None,
                    "day_pnl": day, "quote_as_of": q.as_of.isoformat(), "quote_source": q.source,
                }
                tot["market_value"] += mv
                tot["day_pnl"] += day
                if q.ext_price is not None:
                    row |= {"ext_price": q.ext_price, "ext_change_pct": q.ext_change_pct, "ext_session": q.ext_session,
                            "ext_as_of": q.ext_as_of.isoformat(), "ext_pnl": pos.qty * q.ext_change}
                    ext_pnl += row["ext_pnl"]
                    ext_mv += mv
                    ext_sessions.add(q.ext_session)
            else:
                priced_all = False
            if include_lots:
                row["lots"] = [{"txn_id": l.txn_id, "kind": l.kind, "opened": l.opened.astimezone(NY).date().isoformat(),
                                "qty": round(l.qty, 8), "cost_per_share": l.cost_per_share} for l in pos.lots]
            rows.append(row)

        mv = tot["market_value"]
        for r in rows:
            r["weight_pct"] = (r["market_value"] / mv * 100) if mv and "market_value" in r else None
        prev_mv = mv - tot["day_pnl"]
        totals = tot | {
            "position_count": len(rows),
            "unrealized_pnl": mv - tot["cost_basis"] if priced_all else None,
            "unrealized_pct": (mv / tot["cost_basis"] - 1) * 100 if priced_all and tot["cost_basis"] else None,
            "day_pnl_pct": tot["day_pnl"] / prev_mv * 100 if priced_all and prev_mv else None,
            "fully_priced": priced_all,
            # Pre-market / after-hours move of the positions that traded then (vs the last close).
            "ext_pnl": ext_pnl if ext_sessions else None,
            "ext_pnl_pct": ext_pnl / mv * 100 if ext_sessions and mv else None,
            "ext_session": ("pre" if "pre" in ext_sessions else "post") if ext_sessions else None,
            "ext_coverage_pct": ext_mv / mv * 100 if ext_sessions and mv else None,
        }
        if not priced_all:
            totals["market_value"] = None
            totals["day_pnl"] = None
        return {
            "portfolio": {"id": p.id, "name": p.name, "benchmark": p.benchmark},
            "as_of": now.isoformat(),
            "market": market_status(now),
            "totals": totals,
            "positions": sorted(rows, key=lambda r: -(r.get("market_value") or r["cost_basis"])),
        }
