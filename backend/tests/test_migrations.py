"""The migrations build the schema the models describe, and can be undone."""

import json

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlmodel import create_engine

from db import _ALEMBIC_INI
from tests.conftest import (
    _CONNECT_ARGS,
    _create_database_if_missing,
    _test_database_url,
)


@pytest.fixture
def migrated_connection():
    """A connection to a database of its own, emptied before and after the test."""
    url = _test_database_url()
    url = url.set(database=f"{url.database}_migrations")
    _create_database_if_missing(url)
    engine = create_engine(url, connect_args=_CONNECT_ARGS)
    with engine.connect() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
        connection.commit()
        yield connection
        connection.rollback()
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
        connection.commit()
    engine.dispose()


def _config(connection) -> Config:
    config = Config(str(_ALEMBIC_INI))
    config.attributes["connection"] = connection
    return config


def test_migrations_match_the_models(migrated_connection):
    config = _config(migrated_connection)
    command.upgrade(config, "head")
    migrated_connection.commit()
    # Raises when the models describe something the migrations do not create
    command.check(config)


def test_migrations_can_be_undone(migrated_connection):
    config = _config(migrated_connection)
    command.upgrade(config, "head")
    migrated_connection.commit()
    command.downgrade(config, "base")
    migrated_connection.commit()
    command.upgrade(config, "head")
    migrated_connection.commit()


def test_moments_do_not_move_when_they_gain_a_time_zone(migrated_connection):
    config = _config(migrated_connection)
    command.upgrade(config, "0006")
    migrated_connection.commit()
    # The application always wrote UTC, in columns without a time zone
    migrated_connection.execute(
        text(
            "INSERT INTO workspace (slug, name, created_at, archived_at) "
            "VALUES ('w', 'W', '2026-01-02 03:04:05', '2026-02-03 04:05:06')"
        )
    )
    migrated_connection.commit()

    command.upgrade(config, "head")
    migrated_connection.commit()

    created, archived = migrated_connection.execute(
        text(
            "SELECT created_at = '2026-01-02 03:04:05+00', "
            "archived_at = '2026-02-03 04:05:06+00' FROM workspace WHERE slug = 'w'"
        )
    ).one()
    assert created and archived

    command.downgrade(config, "0006")
    migrated_connection.commit()
    created = migrated_connection.execute(
        text("SELECT created_at = '2026-01-02 03:04:05' FROM workspace WHERE slug = 'w'")
    ).scalar()
    assert created


def _insert_analysis(connection, config: str) -> None:
    connection.execute(
        text(
            "INSERT INTO analysis (name, config, runs, created_at, updated_at, workspace_id) "
            "VALUES ('a', :config, '[]', now(), now(), "
            "(SELECT id FROM workspace WHERE slug = 'default'))"
        ),
        {"config": config},
    )


def test_json_text_becomes_jsonb_without_losing_anything(migrated_connection):
    config = _config(migrated_connection)
    command.upgrade(config, "0007")
    migrated_connection.commit()
    _insert_analysis(migrated_connection, '{"truth_column": "é",   "n": [1, 2]}')
    migrated_connection.execute(
        text(
            "INSERT INTO prompt (name, created_at, workspace_id) "
            "VALUES ('p', now(), (SELECT id FROM workspace WHERE slug = 'default'))"
        )
    )
    # One version with variables, one with a blank text, one without
    for version, variables in (("1", '["a"]'), ("2", "  "), ("3", None)):
        migrated_connection.execute(
            text(
                "INSERT INTO promptversion (prompt_id, version, variables, is_active, "
                "is_default, created_at, workspace_id) VALUES "
                "((SELECT id FROM prompt), :version, :variables, true, false, now(), "
                "(SELECT id FROM workspace WHERE slug = 'default'))"
            ),
            {"version": version, "variables": variables},
        )
    migrated_connection.commit()

    command.upgrade(config, "head")
    migrated_connection.commit()

    stored = migrated_connection.execute(
        text("SELECT config FROM analysis")
    ).scalar()
    assert stored == {"truth_column": "é", "n": [1, 2]}
    variables = dict(
        migrated_connection.execute(
            text("SELECT version, variables FROM promptversion")
        ).all()
    )
    assert variables == {"1": ["a"], "2": None, "3": None}

    command.downgrade(config, "0007")
    migrated_connection.commit()
    text_back = migrated_connection.execute(text("SELECT config FROM analysis")).scalar()
    assert json.loads(text_back) == {"truth_column": "é", "n": [1, 2]}


def test_the_migration_names_the_column_that_holds_invalid_json(migrated_connection):
    config = _config(migrated_connection)
    command.upgrade(config, "0007")
    migrated_connection.commit()
    _insert_analysis(migrated_connection, "not json")
    migrated_connection.commit()

    with pytest.raises(RuntimeError, match=r"analysis\.config: 1 row"):
        command.upgrade(config, "head")
