"""Watchlists: symbols you track without holding them."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import Engine, select

from argus.db import session_scope
from argus.errors import ArgusError
from argus.models import AuditLog, Instrument, Watchlist, WatchlistItem
from argus.symbols import is_plausible_symbol, normalize_symbol

DEFAULT = "Watchlist"


class WatchlistService:
    def __init__(self, engine: Engine, resolve: Callable[[list[str]], dict[str, str]] | None = None):
        """`resolve` maps symbols to {symbol: reason} for those no provider knows; None skips the check."""
        self.engine = engine
        self.resolve = resolve

    def _get(self, s, name: str, create: bool) -> Watchlist:
        w = s.scalar(select(Watchlist).where(Watchlist.name == name))
        if w is None:
            if not create:
                names = [x.name for x in s.scalars(select(Watchlist))]
                raise ArgusError("NOT_FOUND", f"No watchlist '{name}'.",
                                 hint=f"Existing: {', '.join(names)}" if names else "Add a symbol to create it.")
            w = Watchlist(name=name)
            s.add(w)
            s.flush()
        return w

    def list_watchlists(self) -> list[dict]:
        with session_scope(self.engine) as s:
            out = []
            for w in s.scalars(select(Watchlist).order_by(Watchlist.id)):
                n = len(list(s.scalars(select(WatchlistItem).where(WatchlistItem.watchlist_id == w.id))))
                out.append({"name": w.name, "count": n})
            return out

    def items(self, name: str = DEFAULT) -> list[dict]:
        with session_scope(self.engine) as s:
            w = s.scalar(select(Watchlist).where(Watchlist.name == name))
            if w is None:
                if name == DEFAULT:
                    return []
                self._get(s, name, create=False)  # raises NOT_FOUND with hint
            rows = s.scalars(select(WatchlistItem).where(WatchlistItem.watchlist_id == w.id)
                             .order_by(WatchlistItem.added_at))
            return [{"symbol": r.symbol, "note": r.note, "added_at": r.added_at.isoformat()} for r in rows]

    def add(self, symbols: list[str], note: str | None = None, name: str = DEFAULT, actor: str = "cli") -> dict:
        syms = [normalize_symbol(x) for x in symbols if x.strip()]
        bad = [x for x in syms if not is_plausible_symbol(x)]
        if bad:
            raise ArgusError("INVALID_SYMBOL", f"Not a US ticker: {', '.join(bad)}")
        if self.resolve:
            with session_scope(self.engine) as s:
                w = s.scalar(select(Watchlist).where(Watchlist.name == name))
                new = [x for x in dict.fromkeys(syms) if w is None or s.get(WatchlistItem, (w.id, x)) is None]
            unknown = self.resolve(new) if new else {}
            if unknown:
                raise ArgusError("UNKNOWN_SYMBOL", f"No quote found for: {', '.join(sorted(unknown))}",
                                 hint="Check the ticker; only US-listed stocks and ETFs are supported.")
        added, existing = [], []
        with session_scope(self.engine) as s:
            w = self._get(s, name, create=True)
            for sym in dict.fromkeys(syms):
                item = s.get(WatchlistItem, (w.id, sym))
                if item:
                    existing.append(sym)
                    if note is not None:
                        item.note = note
                    continue
                s.add(WatchlistItem(watchlist_id=w.id, symbol=sym, note=note))
                if s.get(Instrument, sym) is None:
                    s.add(Instrument(symbol=sym))
                added.append(sym)
            if added:
                s.add(AuditLog(actor=actor, action="watch", entity="watchlist", entity_id=name, after={"added": added}))
        return {"watchlist": name, "added": added, "already_present": existing}

    def remove(self, symbols: list[str], name: str = DEFAULT, actor: str = "cli") -> dict:
        syms = [normalize_symbol(x) for x in symbols]
        removed, missing = [], []
        with session_scope(self.engine) as s:
            w = self._get(s, name, create=False)
            for sym in syms:
                item = s.get(WatchlistItem, (w.id, sym))
                if item is None:
                    missing.append(sym)
                else:
                    s.delete(item)
                    removed.append(sym)
            if removed:
                s.add(AuditLog(actor=actor, action="unwatch", entity="watchlist", entity_id=name,
                               before={"removed": removed}))
        return {"watchlist": name, "removed": removed, "not_found": missing}
