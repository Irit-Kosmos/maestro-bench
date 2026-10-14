"""reusable invitations

An invitation link now lets anyone who opens it join, until it expires or is
revoked; it may also never expire. It counts its uses instead of recording one.
A link already used stays unusable: it is revoked at the moment of its use.

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-14 10:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0012'
down_revision: str | None = '0011'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('invitation', sa.Column('uses', sa.Integer(), server_default='0', nullable=False))
    op.execute(
        "UPDATE invitation SET uses = 1, revoked_at = COALESCE(revoked_at, used_at) "
        "WHERE used_at IS NOT NULL"
    )
    op.alter_column('invitation', 'uses', server_default=None)
    op.drop_column('invitation', 'used_by')
    op.drop_column('invitation', 'used_at')
    op.alter_column('invitation', 'expires_at', existing_type=sa.DateTime(timezone=True), nullable=True)


def downgrade() -> None:
    # A single-use link cannot stay open forever, nor keep letting people in
    op.execute(
        "UPDATE invitation SET revoked_at = COALESCE(revoked_at, now()), "
        "expires_at = COALESCE(expires_at, now()) "
        "WHERE expires_at IS NULL OR uses > 0"
    )
    op.alter_column('invitation', 'expires_at', existing_type=sa.DateTime(timezone=True), nullable=False)
    op.add_column('invitation', sa.Column('used_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('invitation', sa.Column('used_by', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'invitation', 'user', ['used_by'], ['id'], ondelete='SET NULL')
    op.drop_column('invitation', 'uses')
