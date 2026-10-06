"""The connections the application opens carry the limits it configures."""

import pytest
from sqlalchemy import text
from sqlmodel import create_engine

import config
import db
from tests.conftest import _test_database_url


def settings_of(engine) -> dict[str, str]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT lower(name), setting FROM pg_settings WHERE lower(name) IN "
                "('timezone', 'statement_timeout', 'lock_timeout', "
                "'idle_in_transaction_session_timeout')"
            )
        ).all()
    return dict(rows)


@pytest.fixture
def engine(_db_engine):
    engine = create_engine(
        _test_database_url(), connect_args={"options": db.connection_options()}
    )
    yield engine
    engine.dispose()


def test_connections_have_the_configured_limits(engine):
    assert settings_of(engine) == {
        "timezone": "UTC",
        "statement_timeout": str(config.DB_STATEMENT_TIMEOUT_MS),
        "lock_timeout": str(config.DB_LOCK_TIMEOUT_MS),
        "idle_in_transaction_session_timeout": str(
            config.DB_IDLE_IN_TRANSACTION_TIMEOUT_MS
        ),
    }


def test_a_query_that_runs_too_long_is_stopped(_db_engine, monkeypatch):
    monkeypatch.setattr(config, "DB_STATEMENT_TIMEOUT_MS", 100)
    engine = create_engine(
        _test_database_url(), connect_args={"options": db.connection_options()}
    )
    with engine.connect() as connection, pytest.raises(Exception, match="timeout"):
        connection.execute(text("SELECT pg_sleep(2)"))
    engine.dispose()


def test_migrations_run_without_the_limits(_db_engine):
    engine = create_engine(
        _test_database_url(),
        connect_args={"options": db.connection_options(limits=False)},
    )
    settings = settings_of(engine)
    engine.dispose()

    assert settings["statement_timeout"] == "0"
    assert settings["idle_in_transaction_session_timeout"] == "0"


def test_the_application_engine_uses_the_configured_pool():
    assert db.engine.pool.size() == config.DB_POOL_SIZE
    assert db.engine.pool._max_overflow == config.DB_MAX_OVERFLOW
