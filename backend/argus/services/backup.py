"""Backups: a consistent copy of the SQLite file plus a portable JSON snapshot, with rotation.

Safe while `argus serve` runs: SQLite's online backup API copies a consistent state even with
writers active. The snapshot (see snapshot.py) restores across versions; the .sqlite file is the
quickest full restore, caches included.
"""

from __future__ import annotations

import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from argus.services.snapshot import SnapshotService

SET_NAME = re.compile(r"^\d{8}-\d{6}$")


def backup(db_path: Path, snapshots: SnapshotService, dest: Path, keep: int = 14) -> dict:
    target = dest / datetime.now().strftime("%Y%m%d-%H%M%S")
    target.mkdir(parents=True, exist_ok=False)
    src = sqlite3.connect(db_path)
    try:
        out = sqlite3.connect(target / "argus.sqlite")
        with out:
            src.backup(out)
        out.close()
    finally:
        src.close()
    snap = snapshots.dump(target / "snapshot.json")
    sets = sorted((p for p in dest.iterdir() if p.is_dir() and SET_NAME.match(p.name)), key=lambda p: p.name)
    removed = []
    for old in sets[:-keep] if keep > 0 else []:
        shutil.rmtree(old)
        removed.append(old.name)
    return {"dir": str(target), "db_bytes": (target / "argus.sqlite").stat().st_size,
            "counts": snap["counts"], "kept": min(len(sets), keep) if keep > 0 else len(sets), "removed": removed}
