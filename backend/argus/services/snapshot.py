"""Snapshots: dump records to one JSON file and load them into another instance.

Two kinds: the whole instance (`SnapshotService`, CLI only) and one account's own records
(`AccountSnapshots`, the web UI's Back up / Restore). The rest of this docstring is about the first.

Caches (quotes, price bars, fundamentals, events, fund profiles, NAV) are left out; they refill
on their own. Rows keep their ids, so audit-log and alert-history references stay intact.

A snapshot holds every account's records, with the accounts and their API keys (hashes only; web
sessions are left out, so everyone signs in again after a load). That is why it is CLI only. A
version 1 snapshot predates accounts: loading it keeps the accounts here, and the oldest one gets
its records.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import Date, DateTime, Engine, Table, delete, func, select
from sqlalchemy.dialects.sqlite import insert

from argus import access
from argus.db import session_scope
from argus.errors import ArgusError
from argus.models import (Alert, AlertEvent, AuditLog, Base, Instrument, LoginSession, NavDaily, Note, PeerList,
                          Portfolio, PortfolioShare, Target, Transaction, ValuationModel, Watchlist, WatchlistItem)
from argus.services.accounts import claim_unowned

FORMAT = "argus-snapshot"
VERSION = 2  # 2: accounts, API keys, portfolio shares and per-account owners
# Insert order respects foreign keys; deletes run in reverse.
ACCOUNT_TABLES = ["account", "api_key"]
TABLES = [*ACCOUNT_TABLES, "portfolio", "instrument", "txn", "target", "portfolio_share", "watchlist",
          "watchlist_item", "alert", "alert_event", "note", "peer_list", "valuation_model", "audit_log"]
# Already holding any of these means the instance has records a load would clash with.
USER_TABLES = ["account", "portfolio", "txn", "watchlist_item", "alert", "note"]


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

        # A snapshot from before accounts leaves the accounts here alone (and they don't block it).
        with_accounts = "account" in doc["tables"]
        tables = TABLES if with_accounts else [t for t in TABLES if t not in ACCOUNT_TABLES]
        occupied = {t: n for t, n in self.counts().items() if t in USER_TABLES and n and t in tables}
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
                if with_accounts:
                    s.execute(LoginSession.__table__.delete())  # its accounts are about to be replaced
                for name in reversed(tables):
                    if name != "instrument":  # metadata cache too; upserted below
                        s.execute(_table(name).delete())
            for name in tables:
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
            first = s.scalar(select(func.min(_table("account").c.id)))
            if first:  # records with no owner (from a version 1 snapshot) go to the oldest account
                claim_unowned(s, first)
        return report


# -- one account's records (the web UI's Back up / Restore) --------------------------------------
ACCOUNT_FORMAT = "argus-account-snapshot"
ACCOUNT_VERSION = 1


def _row(obj) -> dict:
    return {c.name: _encode(getattr(obj, c.name)) for c in obj.__table__.columns}


class AccountSnapshots:
    """Back up and restore the records of the account the call acts as (argus.access), and nothing
    else: no other account's records, no accounts or keys, no audit log. Rows get new ids on restore
    (other accounts' rows share the id space), so a file loads into any instance and any account.

    It also loads a version 1 instance snapshot: that predates accounts, so all of it was one person's."""

    def __init__(self, engine: Engine, on_change=None):
        self.engine = engine
        self.on_change = on_change or (lambda: None)  # caches keyed on portfolio/watchlist revisions

    def _mine(self, s) -> dict[str, list]:
        me = access.owner(s)
        portfolios = list(s.scalars(select(Portfolio).where(Portfolio.account_id == me).order_by(Portfolio.id)))
        pids = [p.id for p in portfolios]
        watchlists = list(s.scalars(select(Watchlist).where(Watchlist.account_id == me).order_by(Watchlist.id)))
        alerts = list(s.scalars(select(Alert).where(Alert.account_id == me).order_by(Alert.id)))
        by_portfolio = lambda m: list(s.scalars(select(m).where(m.portfolio_id.in_(pids))))  # noqa: E731
        return {
            "portfolio": portfolios,
            "txn": list(s.scalars(select(Transaction).where(Transaction.portfolio_id.in_(pids)).order_by(Transaction.id))),
            "target": by_portfolio(Target),
            "watchlist": watchlists,
            "watchlist_item": list(s.scalars(select(WatchlistItem).where(
                WatchlistItem.watchlist_id.in_([w.id for w in watchlists])))),
            "alert": alerts,
            "alert_event": list(s.scalars(select(AlertEvent).where(AlertEvent.alert_id.in_([a.id for a in alerts]))
                                          .order_by(AlertEvent.id))),
            "note": list(s.scalars(select(Note).where(Note.account_id == me).order_by(Note.id))),
            "peer_list": list(s.scalars(select(PeerList).where(PeerList.account_id == me))),
            "valuation_model": list(s.scalars(select(ValuationModel).where(ValuationModel.account_id == me))),
        }

    def counts(self) -> dict[str, int]:
        with session_scope(self.engine) as s:
            return {t: len(rows) for t, rows in self._mine(s).items()}

    def export(self, username: str | None = None) -> dict:
        with session_scope(self.engine) as s:
            mine = self._mine(s)
            syms = {r.symbol for t in ("txn", "watchlist_item", "alert", "note", "peer_list", "valuation_model")
                    for r in mine[t]}
            instruments = list(s.scalars(select(Instrument).where(Instrument.symbol.in_(syms))))
            tables = {t: [_row(r) for r in rows] for t, rows in mine.items()} | {
                "instrument": [_row(i) for i in instruments]}
        return {"format": ACCOUNT_FORMAT, "version": ACCOUNT_VERSION, "account": username,
                "created_at": datetime.now(UTC).isoformat(), "tables": tables}

    def restore(self, doc: dict, replace: bool = False, dry_run: bool = True, backup_dir: Path | None = None,
                username: str | None = None) -> dict:
        """Load a file into this account. Your own records block it unless `replace`, which first saves
        them to `backup_dir`. Other accounts are never touched."""
        if not isinstance(doc, dict) or not isinstance(doc.get("tables"), dict):
            raise ArgusError("INVALID_ARG", "That file is not an Argus snapshot.")
        if doc.get("format") == FORMAT:
            if doc.get("version", 0) >= 2 or "account" in doc["tables"]:
                raise ArgusError("INVALID_ARG", "That's a whole-instance snapshot with every account's records.",
                                 hint="Load it on the server: `argus snapshot load <file>`.")
        elif doc.get("format") != ACCOUNT_FORMAT:
            raise ArgusError("INVALID_ARG", "That file is not an Argus snapshot.")
        elif doc.get("version", 0) > ACCOUNT_VERSION:
            raise ArgusError("INVALID_ARG", f"Snapshot version {doc['version']} is newer than this Argus supports.",
                             hint="Update Argus, then load it again.")
        rows = {t: [r for r in doc["tables"].get(t) or [] if isinstance(r, dict)] for t in OWNED_TABLES}
        occupied = {t: n for t, n in self.counts().items() if t in USER_TABLES and n}
        report = {"created_at": doc.get("created_at"), "account": doc.get("account"), "dry_run": dry_run,
                  "replace": replace, "will_remove": occupied, "counts": {t: len(v) for t, v in rows.items()}}
        if dry_run:
            return report
        if occupied and not replace:
            raise ArgusError("ALREADY_EXISTS", "Your account already has records: "
                             + ", ".join(f"{n} {t}" for t, n in occupied.items()) + ".",
                             hint="Replace them to load the snapshot (they are backed up first).")
        if occupied and backup_dir:
            safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in (username or "account"))
            path = backup_dir / f"argus-{safe}-before-load-{datetime.now():%Y%m%d-%H%M%S}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(self.export(username), indent=1))
            report["backup"] = str(path)

        with session_scope(self.engine) as s:
            me = access.owner(s)
            if replace:
                self._delete_mine(s)
            dec = lambda name, r: {k: v for k, v in _decode(_table(name), r).items() if k != "id"}  # noqa: E731
            new_pf, new_wl, new_alert = {}, {}, {}
            for r in rows["portfolio"]:
                p = Portfolio(**dec("portfolio", r) | {"account_id": me})
                s.add(p)
                s.flush()
                new_pf[r.get("id")] = p.id
            for name, model in (("txn", Transaction), ("target", Target)):
                for r in rows[name]:
                    if r.get("portfolio_id") in new_pf:
                        s.add(model(**dec(name, r) | {"portfolio_id": new_pf[r["portfolio_id"]]}))
            for r in rows["watchlist"]:
                w = Watchlist(**dec("watchlist", r) | {"account_id": me})
                s.add(w)
                s.flush()
                new_wl[r.get("id")] = w.id
            for r in rows["watchlist_item"]:
                if r.get("watchlist_id") in new_wl:
                    s.add(WatchlistItem(**dec("watchlist_item", r) | {"watchlist_id": new_wl[r["watchlist_id"]]}))
            for r in rows["alert"]:
                a = Alert(**dec("alert", r) | {"account_id": me})
                s.add(a)
                s.flush()
                new_alert[r.get("id")] = a.id
            for r in rows["alert_event"]:
                if r.get("alert_id") in new_alert:
                    s.add(AlertEvent(**dec("alert_event", r) | {"alert_id": new_alert[r["alert_id"]]}))
            for name, model in (("note", Note), ("peer_list", PeerList), ("valuation_model", ValuationModel)):
                for r in rows[name]:
                    s.add(model(**dec(name, r) | {"account_id": me}))
            inst = [_decode(_table("instrument"), r) for r in doc["tables"].get("instrument") or [] if isinstance(r, dict)]
            if inst:
                stmt = insert(_table("instrument"))
                s.execute(stmt.on_conflict_do_nothing(index_elements=["symbol"]), inst)
            s.add(AuditLog(actor="ui", action="restore", entity="account_snapshot", entity_id=str(me),
                           after={"counts": report["counts"], "replace": replace}))
        self.on_change()
        return report

    def _delete_mine(self, s) -> None:
        """Children before parents, as plain deletes (the models declare no relationships to order them)."""
        mine = self._mine(s)
        pids = [p.id for p in mine["portfolio"]]
        wids = [w.id for w in mine["watchlist"]]
        aids = [a.id for a in mine["alert"]]
        me = access.owner(s)
        for model in (Transaction, Target, NavDaily, PortfolioShare):
            s.execute(delete(model).where(model.portfolio_id.in_(pids)))
        s.execute(delete(AlertEvent).where(AlertEvent.alert_id.in_(aids)))
        s.execute(delete(WatchlistItem).where(WatchlistItem.watchlist_id.in_(wids)))
        s.execute(delete(Alert).where(Alert.id.in_(aids)))
        s.execute(delete(Watchlist).where(Watchlist.id.in_(wids)))
        s.execute(delete(Portfolio).where(Portfolio.id.in_(pids)))
        for model in (Note, PeerList, ValuationModel):
            s.execute(delete(model).where(model.account_id == me))
        s.expire_all()


# Owned tables in an account snapshot, in insert order.
OWNED_TABLES = ["portfolio", "txn", "target", "watchlist", "watchlist_item", "alert", "alert_event", "note",
                  "peer_list", "valuation_model"]
