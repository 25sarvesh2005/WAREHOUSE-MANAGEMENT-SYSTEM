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
    """
    try:
        roles_res = await connection.execute(
            text("SELECT rolname FROM pg_roles WHERE rolname IN ('anon', 'authenticated')")
        )
        existing_roles = set(roles_res.scalars().all())
        preparer = connection.dialect.identifier_preparer
        for table in Base.metadata.sorted_tables:
            schema_name = table.schema or "public"
            qualified_table = f"{preparer.quote_schema(schema_name)}.{preparer.quote(table.name)}"
            await connection.execute(text(f"ALTER TABLE {qualified_table} ENABLE ROW LEVEL SECURITY"))
            for role in existing_roles:
                quoted_role = preparer.quote(role)
                await connection.execute(
                    text(f"REVOKE ALL PRIVILEGES ON TABLE {qualified_table} FROM {quoted_role}")
                )
    except Exception as exc:
        logger.debug("Supabase role hardening skipped or failed: %s", exc)


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
        else:
            existing_admin.hashed_password = hash_password(settings.bootstrap_admin_password)
            existing_admin.status = UserStatus.ACTIVE.value

        # Seed enterprise seller tenant
        aura_seller = await identity_crud.get_seller_by_code(session, "SL-AURA")
        if aura_seller is None:
            from core.models.identity_model import Seller
            aura_seller = Seller(
                code="SL-AURA",
                name="Aura Electronics Corp",
                status=BusinessStatus.ACTIVE.value,
            )
            await identity_crud.create_seller(session, aura_seller)

        # Seed demo seller user
        seller_email = "seller@whitfield.local"
        existing_seller_user = await identity_crud.get_user_by_email(session, seller_email)
        if existing_seller_user is None:
            seller_user = User(
                email=seller_email,
                name="David Chen (Aura Electronics Merchant)",
                hashed_password=hash_password("Seller123!"),
                role=UserRole.SELLER.value,
                status=UserStatus.ACTIVE.value,
            )
            created_seller_user = await identity_crud.create_user(session, seller_user)
            await identity_crud.assign_user_to_seller(
                session,
                user_id=created_seller_user.id,
                seller_id=aura_seller.id,
                assignment_role="SELLER_PRIMARY",
            )
        else:
            existing_seller_user.hashed_password = hash_password("Seller123!")
            existing_seller_user.status = UserStatus.ACTIVE.value
            if not existing_seller_user.seller_assignments:
                await identity_crud.assign_user_to_seller(
                    session,
                    user_id=existing_seller_user.id,
                    seller_id=aura_seller.id,
                    assignment_role="SELLER_PRIMARY",
                )

        warehouses = await identity_crud.list_warehouses(session, limit=200, offset=0)
        existing_codes = {warehouse.code for warehouse in warehouses}
        wh_map = {warehouse.code: warehouse for warehouse in warehouses}
        if "RNO" not in existing_codes:
            rno_wh = await identity_crud.create_warehouse(
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
            wh_map["RNO"] = rno_wh
        if "CMH" not in existing_codes:
            cmh_wh = await identity_crud.create_warehouse(
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
            wh_map["CMH"] = cmh_wh

        # Seed 1 canonical user per role category
        staff_seeds = [
            ("manager@whitfield.local", "Marcus Vance (Operations Manager)", UserRole.WAREHOUSE_MANAGER.value, "Manager123!"),
            ("receiver@whitfield.local", "Elena Rostova (Inbound Receiver)", UserRole.RECEIVER.value, "Receiver123!"),
            ("picker@whitfield.local", "John Doe (Lead Picker/Packer)", UserRole.PICKER_PACKER.value, "Picker123!"),
        ]
        for s_email, s_name, s_role, s_pwd in staff_seeds:
            existing_staff = await identity_crud.get_user_by_email(session, s_email)
            if existing_staff is None:
                staff_user = User(
                    email=s_email,
                    name=s_name,
                    hashed_password=hash_password(s_pwd),
                    role=s_role,
                    status=UserStatus.ACTIVE.value,
                )
                created_staff = await identity_crud.create_user(session, staff_user)
                for wh in wh_map.values():
                    await identity_crud.assign_user_to_warehouse(
                        session,
                        user_id=created_staff.id,
                        warehouse_id=wh.id,
                        assignment_role="PRIMARY",
                    )
            else:
                existing_staff.hashed_password = hash_password(s_pwd)
                existing_staff.status = UserStatus.ACTIVE.value
                for wh in wh_map.values():
                    if not any(a.warehouse_id == wh.id for a in existing_staff.warehouse_assignments):
                        await identity_crud.assign_user_to_warehouse(
                            session,
                            user_id=existing_staff.id,
                            warehouse_id=wh.id,
                            assignment_role="PRIMARY",
                        )
