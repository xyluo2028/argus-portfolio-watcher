"""stock_split: splits Yahoo reports in daily history (B-140)

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-06 03:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

import argus.models  # noqa: F401 - custom column types (UTCDateTime)


revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent like the baseline: a database created by create_all already has it.
    if 'stock_split' in set(sa.inspect(op.get_bind()).get_table_names()):
        return
    op.create_table('stock_split',
    sa.Column('symbol', sa.String(length=16), nullable=False),
    sa.Column('d', sa.Date(), nullable=False),
    sa.Column('ratio', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('symbol', 'd')
    )


def downgrade() -> None:
    op.drop_table('stock_split')
