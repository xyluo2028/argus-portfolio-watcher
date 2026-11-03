"""valuation model: saved DCF calculator inputs

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-04 00:00:00
"""

from alembic import op
import sqlalchemy as sa

import argus.models  # noqa: F401 - UTCDateTime


revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Like the baseline, idempotent: a database made by create_all from newer models already has it.
    if 'valuation_model' in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table('valuation_model',
    sa.Column('symbol', sa.String(length=16), nullable=False),
    sa.Column('inputs', sa.JSON(), nullable=False),
    sa.Column('updated_at', argus.models.UTCDateTime(), nullable=False),
    sa.PrimaryKeyConstraint('symbol')
    )


def downgrade() -> None:
    op.drop_table('valuation_model')
