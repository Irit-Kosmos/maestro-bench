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


"""more authors

Prompt versions and agents now remember who created them, and executions who
launched them. Rows made before this stay without one: nobody can tell who made them.

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-28 10:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0014'
down_revision: str | None = '0013'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = ('promptversion', 'agent', 'experimentexecution')


def upgrade() -> None:
    for table in TABLES:
        op.add_column(table, sa.Column('created_by', sa.Integer(), nullable=True))
        op.create_foreign_key(
            f'{table}_created_by_fkey', table, 'user', ['created_by'], ['id'],
            ondelete='SET NULL',
        )


def downgrade() -> None:
    for table in TABLES:
        op.drop_constraint(f'{table}_created_by_fkey', table, type_='foreignkey')
        op.drop_column(table, 'created_by')
