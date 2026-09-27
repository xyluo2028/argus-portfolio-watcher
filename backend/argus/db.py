"""SQLite engine and session helpers.

Schema is created with `create_all` while the project is pre-1.0; Alembic will be
introduced with the first change that needs to migrate existing data.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import Engine, create_engine, event
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

    Base.metadata.create_all(engine)
    return engine


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
