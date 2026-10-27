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


def test_migrations_run_without_the_limits(_db_engine):
    engine = create_engine(
        _test_database_url(),
        connect_args={"options": db.connection_options(limits=False)},
    )
    settings = settings_of(engine)
    engine.dispose()

    assert settings["statement_timeout"] == "0"
    assert settings["idle_in_transaction_session_timeout"] == "0"
