"""public share links

A share is a public read-only link to an experiment, a batch, an analysis or a
study. Like notes, it points to its item by kind and id; at most one link per
item is active at a time.

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-12 15:02:41.318206
"""
from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = '0011'
down_revision: str | None = '0010'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('share',
    sa.Column('workspace_id', sa.Integer(), nullable=False),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('kind', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('item_id', sa.Integer(), nullable=False),
    sa.Column('token', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_by', sa.Integer(), nullable=True),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_by', sa.Integer(), nullable=True),
    sa.CheckConstraint("kind IN ('experiment', 'batch', 'analysis', 'study')", name='ck_share_kind'),
    sa.ForeignKeyConstraint(['created_by'], ['user.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['revoked_by'], ['user.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_share_token'), 'share', ['token'], unique=True)
    op.create_index(op.f('ix_share_workspace_id'), 'share', ['workspace_id'], unique=False)
    op.create_index('uq_share_active_item', 'share', ['kind', 'item_id'], unique=True, postgresql_where=sa.text('revoked_at IS NULL'))


def downgrade() -> None:
    op.drop_index('uq_share_active_item', table_name='share', postgresql_where=sa.text('revoked_at IS NULL'))
    op.drop_index(op.f('ix_share_workspace_id'), table_name='share')
    op.drop_index(op.f('ix_share_token'), table_name='share')
    op.drop_table('share')
