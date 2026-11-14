"""owners: per-account portfolios, watchlists, alerts, notes, peer lists and DCF models; read-only shares

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-10 00:00:00
"""

from alembic import op
import sqlalchemy as sa

import argus.models  # noqa: F401 - UTCDateTime


revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None

# Older schemas made these unique constraints without names; this names them so they can be dropped.
NAMING = {"uq": "uq_%(table_name)s_%(column_0_name)s"}


def _owner_column(**kw) -> sa.Column:
    return sa.Column('account_id', sa.Integer(), nullable=False, server_default='0', **kw)


def upgrade() -> None:
    # Idempotent per table, like the baseline: a database made by create_all from newer models
    # already has some of this. Runs with foreign keys off (argus.db.migrate), so tables can be rebuilt.
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = lambda table: {c['name'] for c in insp.get_columns(table)}  # noqa: E731

    for table in ('portfolio', 'watchlist'):  # unique name -> unique per account
        if 'account_id' in cols(table):
            continue
        with op.batch_alter_table(table, recreate='always', naming_convention=NAMING) as b:
            b.add_column(_owner_column())
            b.drop_constraint(f'uq_{table}_name', type_='unique')
            b.create_unique_constraint(f'uq_{table}_account_name', ['account_id', 'name'])
            b.create_index(b.f(f'ix_{table}_account_id'), ['account_id'], unique=False)

    for table in ('alert', 'note'):
        if 'account_id' not in cols(table):
            with op.batch_alter_table(table) as b:
                b.add_column(_owner_column())
                b.create_index(b.f(f'ix_{table}_account_id'), ['account_id'], unique=False)

    for table, data in (('peer_list', 'peers'), ('valuation_model', 'inputs')):  # per symbol -> per account and symbol
        if 'account_id' in cols(table):
            continue
        op.create_table(f'_new_{table}',
        _owner_column(),
        sa.Column('symbol', sa.String(length=16), nullable=False),
        sa.Column(data, sa.JSON(), nullable=False),
        sa.Column('updated_at', argus.models.UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint('account_id', 'symbol')
        )
        bind.execute(sa.text(f"INSERT INTO _new_{table} (account_id, symbol, {data}, updated_at) "
                             f"SELECT 0, symbol, {data}, updated_at FROM {table}"))
        op.drop_table(table)
        op.rename_table(f'_new_{table}', table)

    if 'account_id' not in cols('audit_log'):
        with op.batch_alter_table('audit_log') as b:
            b.add_column(sa.Column('account_id', sa.Integer(), nullable=True))

    if 'portfolio_share' not in insp.get_table_names():
        op.create_table('portfolio_share',
        sa.Column('portfolio_id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('created_at', argus.models.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['account.id'], ),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolio.id'], ),
        sa.PrimaryKeyConstraint('portfolio_id', 'account_id')
        )
        with op.batch_alter_table('portfolio_share', schema=None) as b:
            b.create_index(b.f('ix_portfolio_share_account_id'), ['account_id'], unique=False)

    # Accounts made before this migration: the oldest one takes over everything recorded so far.
    first = bind.execute(sa.text("SELECT MIN(id) FROM account")).scalar()
    if first:
        for table in ('portfolio', 'watchlist', 'alert', 'note', 'peer_list', 'valuation_model'):
            bind.execute(sa.text(f"UPDATE {table} SET account_id = :a WHERE account_id = 0"), {"a": first})


def downgrade() -> None:
    op.drop_table('portfolio_share')
    with op.batch_alter_table('audit_log') as b:
        b.drop_column('account_id')
    for table in ('peer_list', 'valuation_model'):  # keeps the oldest account's rows
        bind = op.get_bind()
        first = bind.execute(sa.text("SELECT MIN(account_id) FROM " + table)).scalar() or 0
        bind.execute(sa.text(f"DELETE FROM {table} WHERE account_id != :a"), {"a": first})
        with op.batch_alter_table(table, recreate='always') as b:
            b.drop_column('account_id')
    for table in ('alert', 'note'):
        with op.batch_alter_table(table) as b:
            b.drop_index(b.f(f'ix_{table}_account_id'))
            b.drop_column('account_id')
    for table in ('portfolio', 'watchlist'):
        with op.batch_alter_table(table, recreate='always') as b:
            b.drop_index(b.f(f'ix_{table}_account_id'))
            b.drop_constraint(f'uq_{table}_account_name', type_='unique')
            b.create_unique_constraint(f'uq_{table}_name', ['name'])
            b.drop_column('account_id')
