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

"""moments are stored with their time zone

Every datetime column becomes timestamptz. What was stored (naive datetimes, which
the application always wrote as UTC) is read as UTC, so no moment moves.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-06 11:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0007'
down_revision: str | None = '0006'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COLUMNS = (
    ('agent', 'created_at'),
    ('agentexecutionsnapshot', 'created_at'),
    ('agentteam', 'created_at'),
    ('analysis', 'created_at'),
    ('analysis', 'updated_at'),
    ('batch', 'created_at'),
    ('dataset', 'created_at'),
    ('experiment', 'created_at'),
    ('experiment', 'completed_at'),
    ('experimentagentconfig', 'created_at'),
    ('experimentexecution', 'started_at'),
    ('experimentexecution', 'completed_at'),
    ('identity', 'created_at'),
    ('invitation', 'created_at'),
    ('invitation', 'expires_at'),
    ('invitation', 'used_at'),
    ('invitation', 'revoked_at'),
    ('membership', 'created_at'),
    ('model', 'created_at'),
    ('prompt', 'created_at'),
    ('promptversion', 'created_at'),
    ('session', 'created_at'),
    ('session', 'last_seen_at'),
    ('session', 'expires_at'),
    ('session', 'absolute_expires_at'),
    ('tag', 'created_at'),
    ('user', 'created_at'),
    ('user', 'last_login_at'),
    ('workspace', 'archived_at'),
    ('workspace', 'created_at'),
    ('workspacecredential', 'updated_at'),
)


def upgrade() -> None:
    for table, column in COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(timezone=True),
            existing_type=sa.DateTime(),
            postgresql_using=f'"{column}" AT TIME ZONE \'UTC\'',
        )


def downgrade() -> None:
    for table, column in COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(),
            existing_type=sa.DateTime(timezone=True),
            postgresql_using=f'"{column}" AT TIME ZONE \'UTC\'',
        )
