"""baseline

Revision ID: 0001
Revises: 
Baseline of the schema as of the first deployment.
Create Date: 2026-10-08 00:13:14.105385
"""

from alembic import op
import sqlalchemy as sa

import argus.models  # noqa: F401 - UTCDateTime


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent: a database created before migrations existed (by create_all) already has
    # some or all of these tables; only the missing ones are created.
    existing = set(sa.inspect(op.get_bind()).get_table_names())

    if 'alert' not in existing:
        op.create_table('alert',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=16), nullable=False),
        sa.Column('kind', sa.String(length=24), nullable=False),
        sa.Column('threshold', sa.Float(), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_by', sa.String(length=16), nullable=False),
        sa.Column('created_at', argus.models.UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('alert', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_alert_symbol'), ['symbol'], unique=False)

    if 'audit_log' not in existing:
        op.create_table('audit_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ts', argus.models.UTCDateTime(), nullable=False),
        sa.Column('actor', sa.String(length=16), nullable=False),
        sa.Column('action', sa.String(length=40), nullable=False),
        sa.Column('entity', sa.String(length=40), nullable=False),
        sa.Column('entity_id', sa.String(length=40), nullable=True),
        sa.Column('before', sa.JSON(), nullable=True),
        sa.Column('after', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )

    if 'company_profile' not in existing:
        op.create_table('company_profile',
        sa.Column('symbol', sa.String(length=16), nullable=False),
        sa.Column('as_of', argus.models.UTCDateTime(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('symbol')
        )

    if 'dividend_history' not in existing:
        op.create_table('dividend_history',
        sa.Column('symbol', sa.String(length=16), nullable=False),
        sa.Column('as_of', argus.models.UTCDateTime(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('symbol')
        )

    if 'event' not in existing:
        op.create_table('event',
        sa.Column('symbol', sa.String(length=16), nullable=False),
        sa.Column('kind', sa.String(length=16), nullable=False),
        sa.Column('d', sa.Date(), nullable=False),
        sa.Column('hour', sa.String(length=8), nullable=True),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('source', sa.String(length=16), nullable=False),
        sa.Column('fetched_at', argus.models.UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint('symbol', 'kind', 'd')
        )

    if 'ext_quote' not in existing:
        op.create_table('ext_quote',
        sa.Column('symbol', sa.String(length=16), nullable=False),
        sa.Column('session', sa.String(length=4), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('as_of', argus.models.UTCDateTime(), nullable=False),
        sa.Column('fetched_at', argus.models.UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint('symbol')
        )

    if 'fund_profile' not in existing:
        op.create_table('fund_profile',
        sa.Column('symbol', sa.String(length=16), nullable=False),
        sa.Column('as_of', argus.models.UTCDateTime(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('symbol')
        )

    if 'fundamental' not in existing:
        op.create_table('fundamental',
        sa.Column('symbol', sa.String(length=16), nullable=False),
        sa.Column('as_of', argus.models.UTCDateTime(), nullable=False),
        sa.Column('metrics', sa.JSON(), nullable=False),
        sa.Column('sources', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('symbol')
        )

    if 'instrument' not in existing:
        op.create_table('instrument',
        sa.Column('symbol', sa.String(length=16), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=True),
        sa.Column('exchange', sa.String(length=32), nullable=True),
        sa.Column('type', sa.String(length=32), nullable=True),
        sa.Column('sector', sa.String(length=80), nullable=True),
        sa.Column('industry', sa.String(length=120), nullable=True),
        sa.Column('updated_at', argus.models.UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint('symbol')
        )

    if 'note' not in existing:
        op.create_table('note',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=16), nullable=False),
        sa.Column('kind', sa.String(length=12), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('review_on', sa.Date(), nullable=True),
        sa.Column('archived', sa.Boolean(), nullable=False),
        sa.Column('created_by', sa.String(length=16), nullable=False),
        sa.Column('created_at', argus.models.UTCDateTime(), nullable=False),
        sa.Column('updated_at', argus.models.UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('note', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_note_symbol'), ['symbol'], unique=False)

    if 'peer_list' not in existing:
        op.create_table('peer_list',
        sa.Column('symbol', sa.String(length=16), nullable=False),
        sa.Column('peers', sa.JSON(), nullable=False),
        sa.Column('updated_at', argus.models.UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint('symbol')
        )

    if 'portfolio' not in existing:
        op.create_table('portfolio',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=80), nullable=False),
        sa.Column('benchmark', sa.String(length=16), nullable=False),
        sa.Column('created_at', argus.models.UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
        )

    if 'price_bar' not in existing:
        op.create_table('price_bar',
        sa.Column('symbol', sa.String(length=16), nullable=False),
        sa.Column('interval', sa.String(length=8), nullable=False),
        sa.Column('ts', argus.models.UTCDateTime(), nullable=False),
        sa.Column('o', sa.Float(), nullable=False),
        sa.Column('h', sa.Float(), nullable=False),
        sa.Column('l', sa.Float(), nullable=False),
        sa.Column('c', sa.Float(), nullable=False),
        sa.Column('v', sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint('symbol', 'interval', 'ts')
        )

    if 'quote' not in existing:
        op.create_table('quote',
        sa.Column('symbol', sa.String(length=16), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('prev_close', sa.Float(), nullable=True),
        sa.Column('open', sa.Float(), nullable=True),
        sa.Column('high', sa.Float(), nullable=True),
        sa.Column('low', sa.Float(), nullable=True),
        sa.Column('as_of', argus.models.UTCDateTime(), nullable=False),
        sa.Column('source', sa.String(length=16), nullable=False),
        sa.Column('delayed', sa.Boolean(), nullable=False),
        sa.Column('fetched_at', argus.models.UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint('symbol')
        )

    if 'refresh_log' not in existing:
        op.create_table('refresh_log',
        sa.Column('key', sa.String(length=80), nullable=False),
        sa.Column('at', argus.models.UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint('key')
        )

    if 'security_map' not in existing:
        op.create_table('security_map',
        sa.Column('id', sa.String(length=16), nullable=False),
        sa.Column('ticker', sa.String(length=32), nullable=True),
        sa.Column('exchange', sa.String(length=8), nullable=True),
        sa.Column('symbol', sa.String(length=32), nullable=True),
        sa.Column('as_of', argus.models.UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
        )

    if 'watchlist' not in existing:
        op.create_table('watchlist',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=80), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
        )

    if 'alert_event' not in existing:
        op.create_table('alert_event',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('alert_id', sa.Integer(), nullable=False),
        sa.Column('session_date', sa.Date(), nullable=False),
        sa.Column('ts', argus.models.UTCDateTime(), nullable=False),
        sa.Column('value', sa.Float(), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['alert_id'], ['alert.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('alert_id', 'session_date', name='uq_alert_session')
        )
        with op.batch_alter_table('alert_event', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_alert_event_alert_id'), ['alert_id'], unique=False)

    if 'nav_daily' not in existing:
        op.create_table('nav_daily',
        sa.Column('portfolio_id', sa.Integer(), nullable=False),
        sa.Column('d', sa.Date(), nullable=False),
        sa.Column('market_value', sa.Float(), nullable=False),
        sa.Column('net_flow', sa.Float(), nullable=False),
        sa.Column('income', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolio.id'], ),
        sa.PrimaryKeyConstraint('portfolio_id', 'd')
        )

    if 'target' not in existing:
        op.create_table('target',
        sa.Column('portfolio_id', sa.Integer(), nullable=False),
        sa.Column('level', sa.String(length=8), nullable=False),
        sa.Column('key', sa.String(length=80), nullable=False),
        sa.Column('weight_pct', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolio.id'], ),
        sa.PrimaryKeyConstraint('portfolio_id', 'level', 'key')
        )

    if 'txn' not in existing:
        op.create_table('txn',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=12), nullable=False),
        sa.Column('symbol', sa.String(length=16), nullable=False),
        sa.Column('qty', sa.Float(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('fee', sa.Float(), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('ts', argus.models.UTCDateTime(), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('source', sa.String(length=16), nullable=False),
        sa.Column('external_id', sa.String(length=200), nullable=True),
        sa.Column('deleted', sa.Boolean(), nullable=False),
        sa.Column('created_at', argus.models.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolio.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('portfolio_id', 'external_id', name='uq_txn_external_id')
        )
        with op.batch_alter_table('txn', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_txn_portfolio_id'), ['portfolio_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_txn_symbol'), ['symbol'], unique=False)
            batch_op.create_index(batch_op.f('ix_txn_ts'), ['ts'], unique=False)

    if 'watchlist_item' not in existing:
        op.create_table('watchlist_item',
        sa.Column('watchlist_id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=16), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('added_at', argus.models.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(['watchlist_id'], ['watchlist.id'], ),
        sa.PrimaryKeyConstraint('watchlist_id', 'symbol')
        )

def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('watchlist_item')
    with op.batch_alter_table('txn', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_txn_ts'))
        batch_op.drop_index(batch_op.f('ix_txn_symbol'))
        batch_op.drop_index(batch_op.f('ix_txn_portfolio_id'))

    op.drop_table('txn')
    op.drop_table('target')
    op.drop_table('nav_daily')
    with op.batch_alter_table('alert_event', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_alert_event_alert_id'))

    op.drop_table('alert_event')
    op.drop_table('watchlist')
    op.drop_table('security_map')
    op.drop_table('refresh_log')
    op.drop_table('quote')
    op.drop_table('price_bar')
    op.drop_table('portfolio')
    op.drop_table('peer_list')
    with op.batch_alter_table('note', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_note_symbol'))

    op.drop_table('note')
    op.drop_table('instrument')
    op.drop_table('fundamental')
    op.drop_table('fund_profile')
    op.drop_table('ext_quote')
    op.drop_table('event')
    op.drop_table('dividend_history')
    op.drop_table('company_profile')
    op.drop_table('audit_log')
    with op.batch_alter_table('alert', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_alert_symbol'))

    op.drop_table('alert')
    # ### end Alembic commands ###
