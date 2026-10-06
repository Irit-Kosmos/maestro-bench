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
