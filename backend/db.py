from pathlib import Path
from typing import Annotated

from alembic import command
from alembic.config import Config
from fastapi import Depends
from sqlmodel import Session, create_engine

import config
import workspace_scope  # noqa: F401  (registers the workspace scoping on every session)


def connection_options(*, limits: bool = True) -> str:
    """The server settings of every connection.

    Moments are timestamptz columns, read back as aware UTC datetimes. The session time
    zone is pinned to UTC so that a naive datetime (a script, a test) is read as UTC too.
    The limits (see config) do not apply to the migrations, which may rewrite a table.
    """
    settings = {"timezone": "utc"}
    if limits:
        settings |= {
            "statement_timeout": config.DB_STATEMENT_TIMEOUT_MS,
            "lock_timeout": config.DB_LOCK_TIMEOUT_MS,
            "idle_in_transaction_session_timeout": (
                config.DB_IDLE_IN_TRANSACTION_TIMEOUT_MS
            ),
        }
    return " ".join(f"-c {name}={value}" for name, value in settings.items())


engine = create_engine(
    config.DATABASE_URL,
    echo=config.DB_ECHO,
    pool_size=config.DB_POOL_SIZE,
    max_overflow=config.DB_MAX_OVERFLOW,
    pool_timeout=config.DB_POOL_TIMEOUT,
    # A connection the server or a firewall closed is replaced instead of failing a request
    pool_pre_ping=True,
    pool_recycle=1800,
    connect_args={"options": connection_options()},
)

_ALEMBIC_INI = Path(__file__).parent / "alembic.ini"


def init_db() -> None:
    """Bring the database schema up to date by applying pending migrations."""
    command.upgrade(Config(str(_ALEMBIC_INI)), "head")


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
