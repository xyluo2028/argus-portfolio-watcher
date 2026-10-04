"""Snapshots: dump your own records to one JSON file and load them into another instance.

Caches (quotes, price bars, fundamentals, events, fund profiles, NAV) are left out; they refill
on their own. Rows keep their ids, so audit-log and alert-history references stay intact.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import Date, DateTime, Engine, Table, func, select
from sqlalchemy.dialects.sqlite import insert

from argus.db import session_scope
from argus.errors import ArgusError
from argus.models import Base

FORMAT = "argus-snapshot"
VERSION = 1
# Insert order respects foreign keys; deletes run in reverse.
TABLES = ["portfolio", "instrument", "txn", "target", "watchlist", "watchlist_item",
          "alert", "alert_event", "note", "peer_list", "audit_log"]
# Already holding any of these means the instance has records a load would clash with.
USER_TABLES = ["portfolio", "txn", "watchlist_item", "alert", "note"]


def _table(name: str) -> Table:
    return Base.metadata.tables[name]


def _encode(v):
    return v.isoformat() if isinstance(v, (datetime, date)) else v


def _decode(table: Table, row: dict) -> dict:
    out = {}
    for k, v in row.items():
        col = table.columns.get(k)
        if col is None:
            continue  # column from a newer schema; dropped
        kind = getattr(col.type, "impl", col.type)  # unwrap UTCDateTime
        if isinstance(v, str) and isinstance(kind, DateTime):
            d = datetime.fromisoformat(v)
            v = d if d.tzinfo else d.replace(tzinfo=UTC)
        elif isinstance(v, str) and isinstance(kind, Date):
            v = date.fromisoformat(v)
        out[k] = v
    return out


class SnapshotService:
    def __init__(self, engine: Engine):
        self.engine = engine

    def counts(self) -> dict[str, int]:
        with session_scope(self.engine) as s:
            return {t: s.scalar(select(func.count()).select_from(_table(t))) for t in TABLES}

    def export(self) -> dict:
        """The snapshot document (what `dump` writes)."""
        tables = {}
        with session_scope(self.engine) as s:
            for name in TABLES:
                t = _table(name)
                rows = s.execute(select(t).order_by(*t.primary_key.columns)).mappings()
                tables[name] = [{k: _encode(v) for k, v in r.items()} for r in rows]
        return {"format": FORMAT, "version": VERSION, "created_at": datetime.now(UTC).isoformat(), "tables": tables}

    def dump(self, path: Path) -> dict:
        doc = self.export()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, indent=1))
        return {"file": str(path), "counts": {k: len(v) for k, v in doc["tables"].items()}}

    def load(self, path: Path, replace: bool = False, dry_run: bool = True, backup_dir: Path | None = None) -> dict:
        try:
            doc = json.loads(path.read_text())
        except (OSError, ValueError) as e:
            raise ArgusError("INVALID_ARG", f"Can't read snapshot {path}: {e}") from e
        return {"file": str(path)} | self.restore(doc, replace, dry_run, backup_dir)

    def restore(self, doc: dict, replace: bool = False, dry_run: bool = True, backup_dir: Path | None = None) -> dict:
        """Load a snapshot document. Existing records block it unless `replace`, which first saves
        them to `backup_dir` (when given). A dry run only reports what would happen."""
        if not isinstance(doc, dict) or doc.get("format") != FORMAT or not isinstance(doc.get("tables"), dict):
            raise ArgusError("INVALID_ARG", "That file is not an Argus snapshot.")
        if doc.get("version", 0) > VERSION:
            raise ArgusError("INVALID_ARG", f"Snapshot version {doc['version']} is newer than this Argus supports.",
                             hint="Update Argus, then load it again.")

        occupied = {t: n for t, n in self.counts().items() if t in USER_TABLES and n}
        report = {"created_at": doc.get("created_at"), "dry_run": dry_run, "replace": replace,
                  "will_remove": occupied, "counts": {t: len(doc["tables"].get(t) or []) for t in TABLES}}
        if dry_run:
            return report
        if occupied and not replace:
            raise ArgusError("ALREADY_EXISTS", "This instance already has records: "
                             + ", ".join(f"{n} {t}" for t, n in occupied.items()) + ".",
                             hint="Replace them to load the snapshot (they are backed up first).")
        if occupied and backup_dir:
            report["backup"] = self.dump(backup_dir / f"argus-before-load-{datetime.now():%Y%m%d-%H%M%S}.json")["file"]

        with session_scope(self.engine) as s:
            if replace:
                for name in reversed(TABLES):
                    if name != "instrument":  # metadata cache too; upserted below
                        s.execute(_table(name).delete())
            for name in TABLES:
                t = _table(name)
                rows = [_decode(t, r) for r in doc["tables"].get(name) or []]
                if not rows:
                    continue
                if name == "instrument":
                    stmt = insert(t)
                    cols = {c.name: stmt.excluded[c.name] for c in t.columns if not c.primary_key}
                    s.execute(stmt.on_conflict_do_update(index_elements=["symbol"], set_=cols), rows)
                else:
                    s.execute(t.insert(), rows)
        return report
