"""
Shared database fixtures: the tests run on PostgreSQL, like the application.

They use a dedicated database (``<main database>_test`` on the same server, or
``TEST_DATABASE_URL``) that is created on first use. Every table is emptied after
each test, so the real database is never touched.
"""

import os
from contextlib import contextmanager

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL, make_url
from sqlmodel import Session, SQLModel, create_engine

import tables  # noqa: F401  (registers every table on SQLModel.metadata)
import workspace_files
from config import DATABASE_URL
from workspace_scope import scope_session

_CONNECT_ARGS = {"options": "-c timezone=utc"}

# The workspace every test works in (the first row after the tables are emptied)
TEST_WORKSPACE_ID = 1


@contextmanager
def scoped(engine, workspace_id: int = TEST_WORKSPACE_ID):
    """A session confined to a workspace, to set data up outside the app."""
    with Session(engine) as session:
        yield scope_session(session, workspace_id)


def _test_database_url() -> URL:
    explicit = os.getenv("TEST_DATABASE_URL")
    if explicit:
        return make_url(explicit)
    main = make_url(DATABASE_URL)
    return main.set(database=f"{main.database}_test")


def _create_database_if_missing(url: URL) -> None:
    maintenance = create_engine(
        url.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
        connect_args=_CONNECT_ARGS,
    )
    with maintenance.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": url.database},
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    maintenance.dispose()


@pytest.fixture(scope="session")
def _db_engine():
    url = _test_database_url()
    if url.database == make_url(DATABASE_URL).database:
        pytest.exit("Refusing to run tests on the application database", returncode=2)
    _create_database_if_missing(url)
    engine = create_engine(url, connect_args=_CONNECT_ARGS)
    # Start from a blank schema (drop_all cannot order the batch/experiment cycle)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    SQLModel.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def engine(_db_engine):
    with _db_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO workspace (slug, name, created_at) "
                "VALUES ('test', 'Test', now())"
            )
        )
    yield _db_engine
    names = ", ".join(f'"{table.name}"' for table in SQLModel.metadata.tables.values())
    with _db_engine.begin() as conn:
        conn.execute(text("SET LOCAL lock_timeout = '5s'"))
        conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))


@pytest.fixture
def session(engine):
    with Session(engine) as session:
        scope_session(session, TEST_WORKSPACE_ID)
        yield session


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    """Keep every test's files (results, datasets) out of the real data directory."""
    monkeypatch.setattr(workspace_files, "get_data_dir", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def datasets_dir(data_dir):
    """The datasets folder of the test workspace."""
    path = workspace_files.datasets_dir(TEST_WORKSPACE_ID)
    path.mkdir(parents=True)
    return path


@pytest.fixture
def results_dir(data_dir):
    """The results folder of the test workspace."""
    path = workspace_files.results_dir(TEST_WORKSPACE_ID)
    path.mkdir(parents=True)
    return path
