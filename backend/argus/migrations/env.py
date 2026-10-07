"""Alembic environment. The app calls this through argus.db.migrate (connection passed in);
`uv run alembic ...` from the repo root uses the database from ARGUS_DB / ARGUS_DATA_DIR."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from argus.models import Base

config = context.config
if config.config_file_name and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _url() -> str:
    from argus.config import load_settings

    return config.get_main_option("sqlalchemy.url") or f"sqlite:///{load_settings().db_path}"


def run_migrations_offline() -> None:
    context.configure(url=_url(), target_metadata=target_metadata, literal_binds=True, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:  # called from argus.db.migrate
        context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()
        return
    engine = create_engine(_url())
    with engine.connect() as conn:
        # SQLite can't ALTER most things in place; batch mode rebuilds the table instead.
        context.configure(connection=conn, target_metadata=target_metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
