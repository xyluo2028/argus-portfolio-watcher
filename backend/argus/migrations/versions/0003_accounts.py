"""accounts: sign-in accounts, web sessions and API keys

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-05 00:00:00
"""

from alembic import op
import sqlalchemy as sa

import argus.models  # noqa: F401 - UTCDateTime


revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Like the baseline, idempotent: a database made by create_all from newer models already has them.
    existing = set(sa.inspect(op.get_bind()).get_table_names())

    if 'account' not in existing:
        op.create_table('account',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=40), nullable=False),
        sa.Column('password_hash', sa.String(length=200), nullable=True),
        sa.Column('disabled', sa.Boolean(), nullable=False),
        sa.Column('created_at', argus.models.UTCDateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username')
        )

    if 'login_session' not in existing:
        op.create_table('login_session',
        sa.Column('id_hash', sa.String(length=64), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('created_at', argus.models.UTCDateTime(), nullable=False),
        sa.Column('expires_at', argus.models.UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['account.id'], ),
        sa.PrimaryKeyConstraint('id_hash')
        )
        with op.batch_alter_table('login_session', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_login_session_account_id'), ['account_id'], unique=False)

    if 'api_key' not in existing:
        op.create_table('api_key',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=80), nullable=False),
        sa.Column('prefix', sa.String(length=16), nullable=False),
        sa.Column('key_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', argus.models.UTCDateTime(), nullable=False),
        sa.Column('expires_at', argus.models.UTCDateTime(), nullable=True),
        sa.Column('last_used_at', argus.models.UTCDateTime(), nullable=True),
        sa.Column('revoked_at', argus.models.UTCDateTime(), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['account.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash')
        )
        with op.batch_alter_table('api_key', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_api_key_account_id'), ['account_id'], unique=False)


def downgrade() -> None:
    op.drop_table('api_key')
    op.drop_table('login_session')
    op.drop_table('account')
