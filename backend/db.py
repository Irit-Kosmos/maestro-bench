from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import text, inspect

from config import DATABASE_URL, DB_ECHO

engine = create_engine(DATABASE_URL, echo=DB_ECHO)

# V2 columns that may be missing from an existing DB.
# Format: (table, column, SQL type with default)
_V2_COLUMNS = [
    ("experimentexecution", "total_tokens", "INTEGER DEFAULT NULL"),
    ("experimentexecution", "total_cost_usd", "REAL DEFAULT NULL"),
]


def _ensure_v2_columns() -> None:
    """Add any missing V2 columns to existing tables (safe for SQLite)."""
    insp = inspect(engine)
    for table, column, col_type in _V2_COLUMNS:
        if not insp.has_table(table):
            continue
        existing = {c["name"] for c in insp.get_columns(table)}
        if column not in existing:
            with engine.begin() as conn:
                conn.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                )
                print(f"  Added column {table}.{column}")


def init_db() -> None:
    """Create all tables and ensure V2 columns exist."""
    SQLModel.metadata.create_all(engine)
    _ensure_v2_columns()


def get_session():
    with Session(engine) as session:
        yield session
