from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from config import DATABASE_URL, DB_ECHO

engine = create_engine(DATABASE_URL, echo=DB_ECHO)

# Columns added to tables that may already exist: create_all only creates
# missing tables, so these are added in place to keep existing databases.
_ADDED_COLUMNS = [
    ("experiment", "batch_id", "INTEGER"),
    ("experiment", "variant", "VARCHAR"),
    ("batch", "sampling_seed", "INTEGER"),
]


def _add_missing_columns() -> None:
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table, column, sql_type in _ADDED_COLUMNS:
            existing = {c["name"] for c in inspector.get_columns(table)}
            if column not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"))


def init_db() -> None:
    """Create all tables and add columns introduced since the database was made."""
    SQLModel.metadata.create_all(engine)
    _add_missing_columns()


def get_session():
    with Session(engine) as session:
        yield session
