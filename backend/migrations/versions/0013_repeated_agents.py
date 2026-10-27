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

"""agents that run more than once in an experiment

An agent may now be a step of an experiment several times. A step is told apart
by its key: the id of its agent for the first one, then "<id>#2", "<id>#3"…
Existing rows are the first step of their agent, so they keep that key.

Revision ID: 0013
Revises: 0012
Create Date: 2026-10-26 10:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = '0013'
down_revision: str | None = '0012'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('experimentagentconfig', sa.Column('step_key', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('experimentagentconfig', sa.Column('label', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.execute("UPDATE experimentagentconfig SET step_key = CAST(agent_id AS VARCHAR)")
    op.alter_column('experimentagentconfig', 'step_key', nullable=False)
    op.drop_index('idx_experiment_agent_unique', table_name='experimentagentconfig')
    op.create_index('idx_experiment_step_unique', 'experimentagentconfig', ['experiment_id', 'step_key'], unique=True)

    # Left empty on the snapshots already made: their step is their agent
    op.add_column('agentexecutionsnapshot', sa.Column('step_key', sqlmodel.sql.sqltypes.AutoString(), nullable=True))


def downgrade() -> None:
    op.drop_column('agentexecutionsnapshot', 'step_key')
    # Only the first step of each agent can stay
    op.execute("DELETE FROM experimentagentconfig WHERE step_key <> CAST(agent_id AS VARCHAR)")
    op.drop_index('idx_experiment_step_unique', table_name='experimentagentconfig')
    op.create_index('idx_experiment_agent_unique', 'experimentagentconfig', ['experiment_id', 'agent_id'], unique=True)
    op.drop_column('experimentagentconfig', 'label')
    op.drop_column('experimentagentconfig', 'step_key')
