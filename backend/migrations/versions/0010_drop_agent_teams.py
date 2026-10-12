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
