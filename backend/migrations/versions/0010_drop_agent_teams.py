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

"""agent teams are gone

An experiment is defined by the agents of its pipeline: the team they came from told
it nothing, and an agent no longer belongs to one.

Downgrading puts every agent back in a team called "Default", one per workspace.

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-12 09:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = '0010'
down_revision: str | None = '0009'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index(op.f('ix_agent_team_id'), table_name='agent')
    op.drop_constraint('agent_team_id_fkey', 'agent', type_='foreignkey')
    op.drop_column('agent', 'team_id')
    op.drop_index(op.f('ix_agentteam_workspace_id'), table_name='agentteam')
    op.drop_index(op.f('ix_agentteam_name'), table_name='agentteam')
    op.drop_table('agentteam')


def downgrade() -> None:
    op.create_table('agentteam',
    sa.Column('workspace_id', sa.Integer(), nullable=False),
    sa.Column('created_by', sa.Integer(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['user.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agentteam_name'), 'agentteam', ['name'], unique=False)
    op.create_index(op.f('ix_agentteam_workspace_id'), 'agentteam', ['workspace_id'], unique=False)

    op.add_column('agent', sa.Column('team_id', sa.Integer(), nullable=True))
    op.execute(
        "INSERT INTO agentteam (workspace_id, name, created_at) "
        "SELECT DISTINCT workspace_id, 'Default', now() FROM agent"
    )
    op.execute(
        "UPDATE agent SET team_id = agentteam.id FROM agentteam "
        "WHERE agentteam.workspace_id = agent.workspace_id"
    )
    op.alter_column('agent', 'team_id', nullable=False)
    op.create_foreign_key('agent_team_id_fkey', 'agent', 'agentteam', ['team_id'], ['id'])
    op.create_index(op.f('ix_agent_team_id'), 'agent', ['team_id'], unique=False)
