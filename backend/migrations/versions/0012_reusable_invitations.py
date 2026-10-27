# MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
# Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
# Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

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
