"""Thesis and free-form notes per symbol, with optional review dates."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Engine, select

from argus.db import session_scope
from argus.errors import ArgusError
from argus.models import AuditLog, Note
from argus.symbols import is_plausible_symbol, normalize_symbol

KINDS = ("thesis", "note")


def _row(n: Note) -> dict:
    return {"id": n.id, "symbol": n.symbol, "kind": n.kind, "text": n.text,
            "review_on": n.review_on.isoformat() if n.review_on else None, "archived": n.archived,
            "created_by": n.created_by, "created_at": n.created_at.isoformat(), "updated_at": n.updated_at.isoformat()}


class NoteService:
    def __init__(self, engine: Engine):
        self.engine = engine

    def add(self, symbol: str, text: str, kind: str = "note", review_on: date | None = None, actor: str = "cli") -> dict:
        sym = normalize_symbol(symbol)
        if not is_plausible_symbol(sym):
            raise ArgusError("INVALID_SYMBOL", f"'{sym}' doesn't look like a US ticker.")
        if kind not in KINDS:
            raise ArgusError("INVALID_ARG", f"kind must be one of {', '.join(KINDS)}.")
        if not text.strip():
            raise ArgusError("INVALID_ARG", "Note text is empty.")
        with session_scope(self.engine) as s:
            n = Note(symbol=sym, kind=kind, text=text.strip(), review_on=review_on, created_by=actor)
            s.add(n)
            s.flush()
            s.add(AuditLog(actor=actor, action="create", entity="note", entity_id=str(n.id), after=_row(n)))
            return _row(n)

    def update(self, note_id: int, text: str | None = None, review_on: date | None = None,
               clear_review: bool = False, archived: bool | None = None, actor: str = "cli") -> dict:
        with session_scope(self.engine) as s:
            n = s.get(Note, note_id)
            if n is None:
                raise ArgusError("NOT_FOUND", f"No note {note_id}.")
            before = _row(n)
            if text is not None:
                n.text = text.strip()
            if review_on is not None:
                n.review_on = review_on
            if clear_review:
                n.review_on = None
            if archived is not None:
                n.archived = archived
            s.flush()
            s.add(AuditLog(actor=actor, action="update", entity="note", entity_id=str(n.id), before=before, after=_row(n)))
            return _row(n)

    def list(self, symbol: str | None = None, include_archived: bool = False,
             due_by: date | None = None) -> list[dict]:
        with session_scope(self.engine) as s:
            q = select(Note)
            if symbol:
                q = q.where(Note.symbol == normalize_symbol(symbol))
            if not include_archived:
                q = q.where(Note.archived.is_(False))
            if due_by:
                q = q.where(Note.review_on.is_not(None), Note.review_on <= due_by)
            return [_row(n) for n in s.scalars(q.order_by(Note.symbol, Note.kind.desc(), Note.created_at.desc()))]
