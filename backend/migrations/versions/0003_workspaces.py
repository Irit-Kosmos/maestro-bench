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

"""workspaces

Every existing row moves to a workspace called "default", which starts without
members: the first instance admin to sign in becomes its owner.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-05 17:54:32.150030
"""
from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = '0003'
down_revision: str | None = '0002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Tables whose rows belong to a workspace
OWNED = (
    'model', 'prompt', 'promptversion', 'agentteam', 'agent', 'dataset', 'batch',
    'experiment', 'experimentagentconfig', 'experimentexecution',
    'agentexecutionsnapshot', 'analysis', 'tag', 'taglink',
)
# ...and, among them, the ones that remember who created a row
AUTHORED = (
    'model', 'prompt', 'agentteam', 'dataset', 'batch', 'experiment', 'analysis',
    'tag',
)


def upgrade() -> None:
    op.create_table('workspace',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('slug', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('archived_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('created_by', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['user.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workspace_slug'), 'workspace', ['slug'], unique=True)
    op.create_table('membership',
    sa.Column('workspace_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('role', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('workspace_id', 'user_id')
    )
    op.create_index(op.f('ix_membership_user_id'), 'membership', ['user_id'], unique=False)

    op.execute(
        "INSERT INTO workspace (slug, name, created_at) "
        "VALUES ('default', 'Default', now())"
    )

    for table in OWNED:
        op.add_column(table, sa.Column('workspace_id', sa.Integer(), nullable=True))
        op.execute(
            f"UPDATE {table} SET workspace_id = "
            "(SELECT id FROM workspace WHERE slug = 'default')"
        )
        op.alter_column(table, 'workspace_id', nullable=False)
        op.create_index(op.f(f'ix_{table}_workspace_id'), table, ['workspace_id'], unique=False)
        op.create_foreign_key(
            f'{table}_workspace_id_fkey', table, 'workspace', ['workspace_id'], ['id']
        )
    for table in AUTHORED:
        op.add_column(table, sa.Column('created_by', sa.Integer(), nullable=True))
        op.create_foreign_key(
            f'{table}_created_by_fkey', table, 'user', ['created_by'], ['id'],
            ondelete='SET NULL',
        )

    # Tag names were unique ignoring case across the app: now within a workspace
    op.create_index(
        'uq_tag_workspace_name', 'tag',
        ['workspace_id', sa.literal_column('lower(name)')], unique=True,
    )


def downgrade() -> None:
    op.drop_index('uq_tag_workspace_name', table_name='tag')
    for table in AUTHORED:
        op.drop_constraint(f'{table}_created_by_fkey', table, type_='foreignkey')
        op.drop_column(table, 'created_by')
    for table in OWNED:
        op.drop_constraint(f'{table}_workspace_id_fkey', table, type_='foreignkey')
        op.drop_index(op.f(f'ix_{table}_workspace_id'), table_name=table)
        op.drop_column(table, 'workspace_id')
    op.drop_index(op.f('ix_membership_user_id'), table_name='membership')
    op.drop_table('membership')
    op.drop_index(op.f('ix_workspace_slug'), table_name='workspace')
    op.drop_table('workspace')
