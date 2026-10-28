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


"""step usage

Each step of an execution keeps the tokens and cost it used, so spending can be told
apart by model. Executions made before this keep only their totals.

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-28 14:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0015'
down_revision: str | None = '0014'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('agentexecutionsnapshot', sa.Column('total_tokens', sa.Integer(), nullable=True))
    op.add_column('agentexecutionsnapshot', sa.Column('total_cost_usd', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('agentexecutionsnapshot', 'total_cost_usd')
    op.drop_column('agentexecutionsnapshot', 'total_tokens')
