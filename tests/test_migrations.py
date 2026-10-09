"""Migrations and models must describe the same schema, and every kind of database must end at head."""

import sqlite3

from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

from argus.db import _alembic_config, make_engine
from argus.models import Base

HEAD = ScriptDirectory.from_config(_alembic_config()).get_current_head()


def _revision(engine):
    with engine.connect() as c:
        return MigrationContext.configure(c).get_current_revision()


def _upgrade_from_empty(path):
    """Apply the migration chain itself to an empty file (not the create_all shortcut)."""
    from alembic import command

    eng = create_engine(f"sqlite:///{path}")
    cfg = _alembic_config()
    with eng.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")
    return eng


def test_migrations_reproduce_the_models(tmp_path):
    eng = _upgrade_from_empty(tmp_path / "m.sqlite")
    with eng.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == [], f"models changed without a migration: run `uv run alembic revision --autogenerate`\\n{diff}"


def test_new_database_is_created_at_head(tmp_path):
    eng = make_engine(tmp_path / "new.sqlite")
    assert _revision(eng) == HEAD
    assert set(Base.metadata.tables) <= set(inspect(eng).get_table_names())


def test_pre_migration_database_is_adopted_without_losing_data(tmp_path):
    path = tmp_path / "old.sqlite"
    old = create_engine(f"sqlite:///{path}")
    keep = [t for name, t in Base.metadata.tables.items() if name != "peer_list"]  # an older app version
    Base.metadata.create_all(old, tables=keep)
    with sqlite3.connect(path) as c:
        c.execute("INSERT INTO portfolio (id, name, benchmark, created_at) VALUES (1, 'growth', 'SPY', '2026-09-29 00:00:00')")
    eng = make_engine(path)
    assert _revision(eng) == HEAD and "peer_list" in inspect(eng).get_table_names()
    with sqlite3.connect(path) as c:
        assert c.execute("SELECT name FROM portfolio").fetchall() == [("growth",)]
