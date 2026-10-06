"""experiment sampling seed

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-05 19:30:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0005'
down_revision: str | None = '0004'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('experiment', sa.Column('sampling_seed', sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column('experiment', 'sampling_seed')
