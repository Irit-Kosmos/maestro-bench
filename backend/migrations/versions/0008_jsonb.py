"""JSON documents are stored as jsonb

The columns that held JSON as text become jsonb: the database now refuses what is not
JSON, and can query it. The application still reads and writes them as text (see
`tables.JsonText`).

A blank text in a column that may be empty becomes NULL. Anything else must be valid
JSON, otherwise the migration stops and says which column to fix.

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-06 12:00:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0008'
down_revision: str | None = '0007'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (table, column, nullable)
COLUMNS = (
    ('analysis', 'config', False),
    ('analysis', 'runs', False),
    ('batch', 'variations', False),
    ('experimentexecution', 'dataset_snapshot', False),
    ('experimentagentconfig', 'input_mappings', True),
    ('experimentagentconfig', 'formulas', True),
    ('agentexecutionsnapshot', 'final_variables', True),
    ('agentexecutionsnapshot', 'final_input_mappings', True),
    ('agentexecutionsnapshot', 'final_formulas', True),
    ('promptversion', 'variables', True),
)


def upgrade() -> None:
    for table, column, nullable in COLUMNS:
        invalid = op.get_bind().execute(
            sa.text(
                f'SELECT count(*) FROM "{table}" WHERE "{column}" IS NOT NULL '
                f'AND NOT ("{column}" IS JSON)'
                + (f' AND btrim("{column}") <> \'\'' if nullable else '')
            )
        ).scalar()
        if invalid:
            raise RuntimeError(
                f'{table}.{column}: {invalid} row(s) are not valid JSON. '
                'Fix or clear them, then start the application again.'
            )
        using = (
            f'CASE WHEN btrim("{column}") = \'\' THEN NULL ELSE "{column}"::jsonb END'
            if nullable
            else f'"{column}"::jsonb'
        )
        op.alter_column(
            table,
            column,
            type_=postgresql.JSONB(none_as_null=True),
            existing_type=sa.Text(),
            existing_nullable=nullable,
            postgresql_using=using,
        )


def downgrade() -> None:
    for table, column, nullable in COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.Text(),
            existing_type=postgresql.JSONB(),
            existing_nullable=nullable,
            postgresql_using=f'"{column}"::text',
        )
