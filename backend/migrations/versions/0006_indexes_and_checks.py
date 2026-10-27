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

"""indexes on foreign keys and the lists, and CHECK constraints on closed sets

Foreign keys get an index so that joins, and the cascades that follow a delete,
do not scan the child table. The lists of a workspace get composite indexes that
match their filter and sort. Statuses, kinds and roles are checked by the database.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-06 10:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0006'
down_revision: str | None = '0005'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (table, column): the foreign keys that had no index
FOREIGN_KEYS = (
    ('agent', 'team_id'),
    ('agent', 'default_model_id'),
    ('agent', 'default_prompt_version_id'),
    ('promptversion', 'prompt_id'),
    ('batch', 'base_experiment_id'),
    ('experiment', 'dataset_id'),
    ('experimentagentconfig', 'agent_id'),
    ('experimentagentconfig', 'model_id'),
    ('experimentagentconfig', 'prompt_version_id'),
    ('agentexecutionsnapshot', 'execution_id'),
    ('agentexecutionsnapshot', 'agent_id'),
)

# (table, name, condition)
CHECKS = (
    ('agent', 'ck_agent_kind', "kind IN ('llm', 'aggregator')"),
    (
        'agentexecutionsnapshot',
        'ck_agentexecutionsnapshot_kind',
        "kind IN ('llm', 'aggregator')",
    ),
    (
        'experiment',
        'ck_experiment_status',
        "status IN ('pending', 'queued', 'running', 'completed', 'failed', "
        "'cancelled', 'interrupted')",
    ),
    (
        'experiment',
        'ck_experiment_sampling_type',
        "sampling_type IS NULL OR sampling_type IN ('all', 'random', 'range')",
    ),
    (
        'experimentexecution',
        'ck_experimentexecution_status',
        "status IN ('running', 'completed', 'failed', 'cancelled', 'interrupted')",
    ),
    (
        'experimentexecution',
        'ck_experimentexecution_rows',
        'rows_done >= 0 AND rows_failed >= 0',
    ),
    ('taglink', 'ck_taglink_kind', "kind IN ('prompt', 'analysis', 'agent')"),
    ('membership', 'ck_membership_role', "role IN ('viewer', 'editor', 'owner')"),
    ('invitation', 'ck_invitation_role', "role IN ('viewer', 'editor', 'owner')"),
)


def upgrade() -> None:
    for table, column in FOREIGN_KEYS:
        op.create_index(op.f(f'ix_{table}_{column}'), table, [column], unique=False)

    op.create_index(
        'ix_experimentexecution_experiment_started',
        'experimentexecution',
        ['experiment_id', 'started_at'],
        unique=False,
    )
    op.create_index(
        'ix_experimentexecution_workspace_started',
        'experimentexecution',
        ['workspace_id', 'started_at'],
        unique=False,
    )
    op.create_index(
        'ix_experiment_workspace_created',
        'experiment',
        ['workspace_id', 'created_at'],
        unique=False,
    )
    op.create_index(
        'ix_experiment_workspace_active',
        'experiment',
        ['workspace_id'],
        unique=False,
        postgresql_where=sa.text("status IN ('pending', 'queued', 'running')"),
    )
    op.create_index('ix_taglink_kind_item', 'taglink', ['kind', 'item_id'], unique=False)

    # Users are looked up by email ignoring case: the plain index could not serve that
    op.drop_index(op.f('ix_user_email'), table_name='user')
    op.create_index('ix_user_email_lower', 'user', [sa.literal_column('lower(email)')])
    op.create_index(
        op.f('ix_session_absolute_expires_at'),
        'session',
        ['absolute_expires_at'],
        unique=False,
    )

    for table, name, condition in CHECKS:
        op.create_check_constraint(name, table, condition)


def downgrade() -> None:
    for table, name, _ in reversed(CHECKS):
        op.drop_constraint(name, table, type_='check')

    op.drop_index(op.f('ix_session_absolute_expires_at'), table_name='session')
    op.drop_index('ix_user_email_lower', table_name='user')
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=False)
    op.drop_index('ix_taglink_kind_item', table_name='taglink')
    op.drop_index('ix_experiment_workspace_active', table_name='experiment')
    op.drop_index('ix_experiment_workspace_created', table_name='experiment')
    op.drop_index(
        'ix_experimentexecution_workspace_started', table_name='experimentexecution'
    )
    op.drop_index(
        'ix_experimentexecution_experiment_started', table_name='experimentexecution'
    )
    for table, column in reversed(FOREIGN_KEYS):
        op.drop_index(op.f(f'ix_{table}_{column}'), table_name=table)
