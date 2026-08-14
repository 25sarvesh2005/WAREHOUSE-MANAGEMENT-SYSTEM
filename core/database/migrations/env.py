"""
--------------------------------------------------------------------------------
File        : core/database/migrations/env.py
Purpose     : Configure Alembic migrations for SQLAlchemy models.

Responsibilities:
    - Load application settings for migration database URL.
    - Expose SQLAlchemy metadata to Alembic autogeneration.

Flow:
    Alembic command
        ->
    env.py loads settings and model metadata
        ->
    Online or offline migration execution

Used By:
    - alembic CLI

Returns:
    run_migrations_online() -> None - Executes online migrations.

Raises:
    sqlalchemy.exc.SQLAlchemyError: On migration failures.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from core.config.settings import get_settings
from core.database.base import Base
from core.models import ai_model as ai_model
from core.models import audit_model as audit_model
from core.models import catalog_model as catalog_model
from core.models import fulfillment_model as fulfillment_model
from core.models import identity_model as identity_model
from core.models import inventory_model as inventory_model
from core.models import migration_model as migration_model
from core.models import order_model as order_model
from core.models import outbox_model as outbox_model
from core.models import receiving_model as receiving_model
from core.models import return_model as return_model
from core.models import transfer_model as transfer_model
from core.models import voice_model as voice_model

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

_MODEL_IMPORTS = (
    ai_model,
    audit_model,
    catalog_model,
    fulfillment_model,
    identity_model,
    inventory_model,
    migration_model,
    order_model,
    outbox_model,
    receiving_model,
    return_model,
    transfer_model,
    voice_model,
)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run Alembic migrations without creating an engine.

    Offline mode writes SQL using the configured database URL and target
    metadata without opening a live connection.

    Returns:
        None.

    Raises:
        alembic.util.CommandError: If migration configuration is invalid.
    """
    url = get_settings().alembic_database_url
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run Alembic migrations using a live database connection.

    MIGRATION_DATABASE_URL takes precedence when supplied. The selected URL is
    normalized to SQLAlchemy's synchronous psycopg driver for Alembic.

    Returns:
        None.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If migration execution fails.
    """
    settings = get_settings()
    # configparser treats '%' as an interpolation prefix, so percent-encoded
    # characters in the password (e.g. %2F, %24) must be escaped to '%%'
    # before being stored with set_main_option.  configparser restores '%%'
    # to '%' when the value is read back, giving the correct URL to SQLAlchemy.
    safe_url = settings.alembic_database_url.replace("%", "%%")
    config.set_main_option("sqlalchemy.url", safe_url)
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
