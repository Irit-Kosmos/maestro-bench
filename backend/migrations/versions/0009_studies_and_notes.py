"""studies, the items they gather, and notes

A study gathers experiments, batches and analyses (`studyitem`), and can be tagged
like a prompt. Notes are journal entries attached to an experiment, a batch, an
analysis or a study. Like tag links, both point to their item by kind and id.

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-06 19:22:26.511073
"""
from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

revision: str = '0009'
down_revision: str | None = '0008'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('note',
    sa.Column('workspace_id', sa.Integer(), nullable=False),
    sa.Column('created_by', sa.Integer(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('kind', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('item_id', sa.Integer(), nullable=False),
    sa.Column('body', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("kind IN ('experiment', 'batch', 'analysis', 'study')", name='ck_note_kind'),
    sa.ForeignKeyConstraint(['created_by'], ['user.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_note_kind_item_created', 'note', ['kind', 'item_id', 'created_at'], unique=False)
    op.create_index(op.f('ix_note_workspace_id'), 'note', ['workspace_id'], unique=False)
    op.create_table('study',
    sa.Column('workspace_id', sa.Integer(), nullable=False),
    sa.Column('created_by', sa.Integer(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('status', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("status IN ('active', 'concluded', 'archived')", name='ck_study_status'),
    sa.ForeignKeyConstraint(['created_by'], ['user.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_study_workspace_id'), 'study', ['workspace_id'], unique=False)
    op.create_index('ix_study_workspace_updated', 'study', ['workspace_id', 'updated_at'], unique=False)
    op.create_table('studyitem',
    sa.Column('workspace_id', sa.Integer(), nullable=False),
    sa.Column('study_id', sa.Integer(), nullable=False),
    sa.Column('kind', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('item_id', sa.Integer(), nullable=False),
    sa.Column('added_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('added_by', sa.Integer(), nullable=True),
    sa.CheckConstraint("kind IN ('experiment', 'batch', 'analysis')", name='ck_studyitem_kind'),
    sa.ForeignKeyConstraint(['added_by'], ['user.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['study_id'], ['study.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['workspace_id'], ['workspace.id'], ),
    sa.PrimaryKeyConstraint('study_id', 'kind', 'item_id')
    )
    op.create_index('ix_studyitem_kind_item', 'studyitem', ['kind', 'item_id'], unique=False)
    op.create_index(op.f('ix_studyitem_workspace_id'), 'studyitem', ['workspace_id'], unique=False)

    # Studies can be tagged
    op.drop_constraint('ck_taglink_kind', 'taglink', type_='check')
    op.create_check_constraint(
        'ck_taglink_kind', 'taglink', "kind IN ('prompt', 'analysis', 'agent', 'study')"
    )


def downgrade() -> None:
    op.execute("DELETE FROM taglink WHERE kind = 'study'")
    op.drop_constraint('ck_taglink_kind', 'taglink', type_='check')
    op.create_check_constraint(
        'ck_taglink_kind', 'taglink', "kind IN ('prompt', 'analysis', 'agent')"
    )

    op.drop_index(op.f('ix_studyitem_workspace_id'), table_name='studyitem')
    op.drop_index('ix_studyitem_kind_item', table_name='studyitem')
    op.drop_table('studyitem')
    op.drop_index('ix_study_workspace_updated', table_name='study')
    op.drop_index(op.f('ix_study_workspace_id'), table_name='study')
    op.drop_table('study')
    op.drop_index(op.f('ix_note_workspace_id'), table_name='note')
    op.drop_index('ix_note_kind_item_created', table_name='note')
    op.drop_table('note')
