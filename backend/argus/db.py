"""SQLite engine and session helpers.

The schema is managed by Alembic (backend/argus/migrations). Opening a database brings it to the
latest revision: a new one is created from the models and stamped, one created before migrations
existed adopts the baseline, and anything older than head is upgraded.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import Engine, create_engine, event, inspect
from sqlalchemy.orm import Session, sessionmaker

from argus.models import Base


def make_engine(db_path: Path | str) -> Engine:
    url = "sqlite://" if str(db_path) == ":memory:" else f"sqlite:///{db_path}"
    if str(db_path) != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, future=True)

    @event.listens_for(engine, "connect")
    def _pragmas(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        # WAL lets the web server and an MCP stdio process share the file safely.
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.close()

    if str(db_path) == ":memory:":
        Base.metadata.create_all(engine)  # throwaway databases need no history
    else:
        migrate(engine)
    return engine


MIGRATIONS = Path(__file__).resolve().parent / "migrations"


def _alembic_config():
    from alembic.config import Config

    cfg = Config()
    cfg.set_main_option("script_location", str(MIGRATIONS))
    cfg.attributes["configure_logger"] = False
    return cfg


def migrate(engine: Engine) -> None:
    from alembic import command
    from alembic.runtime.migration import MigrationContext
    from alembic.script import ScriptDirectory

    cfg = _alembic_config()
    head = ScriptDirectory.from_config(cfg).get_current_head()
    with engine.begin() as conn:
        current = MigrationContext.configure(conn).get_current_revision()
        if current == head:
            return
        cfg.attributes["connection"] = conn
        if current is None and not inspect(conn).get_table_names():
            # Brand new: build from the models (identical to head; tests/test_migrations.py) and stamp.
            Base.metadata.create_all(conn)
            command.stamp(cfg, "head")
        else:
            # Pre-migration databases have no version: the idempotent baseline adopts them.
            command.upgrade(cfg, "head")


@contextmanager
def session_scope(engine: Engine) -> Iterator[Session]:
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
