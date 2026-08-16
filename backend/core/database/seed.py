"""
--------------------------------------------------------------------------------
File        : core/database/seed.py
Purpose     : Initialize development schema and required seed records.

Responsibilities:
    - Create database extensions and tables for local development and tests.
    - Seed bootstrap administrator and Reno/Columbus warehouses.

Flow:
    FastAPI lifespan startup
        ->
    initialize_schema_for_development()
        ->
    seed_initial_data()

Used By:
    - main.py

Returns:
    initialize_schema_for_development() -> None - Schema initialized.
    seed_initial_data() -> None - Required records present.

Raises:
    sqlalchemy.exc.SQLAlchemyError: On schema or seed failures.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from common.auth import hash_password
from common.logger import get_logger
from core.config.settings import get_settings
from core.constants import BusinessStatus, UserRole, UserStatus
from core.cruds import identity_crud
from core.database.base import Base
from core.database.database import get_engine, transaction_session
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
from core.models.identity_model import User, Warehouse

logger = get_logger(__name__)

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


async def _secure_public_tables_for_supabase(connection: AsyncConnection) -> None:
    """
    Apply deny-by-default Data API protections to application tables.

    Tables in Supabase's exposed ``public`` schema receive RLS with no public
    policies. When Supabase's ``anon`` or ``authenticated`` roles exist, their
    direct table privileges are revoked because this application exposes data
    only through its FastAPI authorization layer.

    Args:
        connection: Active schema-initialization database connection.

    Returns:
        None.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If table hardening fails.
    """
    preparer = connection.dialect.identifier_preparer
    for table in Base.metadata.sorted_tables:
        schema_name = table.schema or "public"
        qualified_table = f"{preparer.quote_schema(schema_name)}.{preparer.quote(table.name)}"
        await connection.execute(text(f"ALTER TABLE {qualified_table} ENABLE ROW LEVEL SECURITY"))

        for database_role in ("anon", "authenticated"):
            role_exists = await connection.scalar(
                text("SELECT 1 FROM pg_roles WHERE rolname = :role_name"),
                {"role_name": database_role},
            )
            if role_exists:
                quoted_role = preparer.quote(database_role)
                await connection.execute(
                    text(f"REVOKE ALL PRIVILEGES ON TABLE {qualified_table} FROM {quoted_role}")
                )


async def initialize_schema_for_development() -> None:
    """
    Create extensions and tables for development and test environments.

    Production deployments should use Alembic migrations; this initializer makes
    the first implementation slice runnable before migration files are expanded.

    Returns:
        None.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If schema creation fails.
    """
    settings = get_settings()
    if settings.app_env == "production" or not settings.initialize_schema_on_startup:
        logger.info("Skipping automatic schema initialization")
        return

    logger.info("Initializing development database schema")
    engine = get_engine()
    async with engine.begin() as connection:
        await connection.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
        await connection.run_sync(Base.metadata.create_all)
        await _secure_public_tables_for_supabase(connection)


async def seed_initial_data() -> None:
    """
    Seed required bootstrap records.

    The seed operation is idempotent by email and warehouse code so local startup
    can be repeated without creating duplicate operational records.

    Returns:
        None.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If seed writes fail.
    """
    logger.info("Seeding initial warehouse data")
    settings = get_settings()
    async with transaction_session() as session:
        admin_email = settings.bootstrap_admin_email.strip().lower()
        existing_admin = await identity_crud.get_user_by_email(session, admin_email)
        if existing_admin is None:
            admin = User(
                email=admin_email,
                name="Bootstrap Administrator",
                hashed_password=hash_password(settings.bootstrap_admin_password),
                role=UserRole.ADMINISTRATOR.value,
                status=UserStatus.ACTIVE.value,
            )
            await identity_crud.create_user(session, admin)

        warehouses = await identity_crud.list_warehouses(session, limit=200, offset=0)
        existing_codes = {warehouse.code for warehouse in warehouses}
        if "RNO" not in existing_codes:
            await identity_crud.create_warehouse(
                session,
                Warehouse(
                    code="RNO",
                    name="Reno Fulfillment Warehouse",
                    city="Reno",
                    state="Nevada",
                    timezone="America/Los_Angeles",
                    status=BusinessStatus.ACTIVE.value,
                ),
            )
        if "CMH" not in existing_codes:
            await identity_crud.create_warehouse(
                session,
                Warehouse(
                    code="CMH",
                    name="Columbus Fulfillment Warehouse",
                    city="Columbus",
                    state="Ohio",
                    timezone="America/New_York",
                    status=BusinessStatus.ACTIVE.value,
                ),
            )
