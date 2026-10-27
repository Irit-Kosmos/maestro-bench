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

from logging.config import fileConfig

from alembic import context
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel, create_engine

import tables  # noqa: F401  (registers every table on SQLModel.metadata)
from db import connection_options, engine

config = context.config
if config.config_file_name is not None:
    # Keep the application's own logging when migrations run at startup
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=engine.url.render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _run(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # A caller (the migration tests) may hand over the connection to migrate
    connection = config.attributes.get("connection")
    if connection is not None:
        _run(connection)
        return
    # Its own connection, without the limits of the application's: a migration may take a while
    migration_engine = create_engine(
        engine.url,
        poolclass=NullPool,
        connect_args={"options": connection_options(limits=False)},
    )
    with migration_engine.connect() as connection:
        _run(connection)
    migration_engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
