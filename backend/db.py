from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlmodel import Session, create_engine

import workspace_scope  # noqa: F401  (registers the workspace scoping on every session)
from config import DATABASE_URL, DB_ECHO

# Naive UTC datetimes are stored in TIMESTAMP WITHOUT TIME ZONE columns:
# pin the session time zone so aware datetimes are never shifted.
engine = create_engine(
    DATABASE_URL,
    echo=DB_ECHO,
    pool_pre_ping=True,
    connect_args={"options": "-c timezone=utc"},
)

_ALEMBIC_INI = Path(__file__).parent / "alembic.ini"


def init_db() -> None:
    """Bring the database schema up to date by applying pending migrations."""
    command.upgrade(Config(str(_ALEMBIC_INI)), "head")


def get_session():
    with Session(engine) as session:
        yield session
