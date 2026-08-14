"""
--------------------------------------------------------------------------------
File        : core/cruds/catalog_crud.py
Purpose     : Perform pure database operations for catalog and policy records.

Responsibilities:
    - Create and list products, identifiers, locations, and seller policies.
    - Keep master-data persistence separate from authorization and workflow rules.

Flow:
    Catalog controller
        ->
    CRUD function receives AsyncSession
        ->
    SQLAlchemy executes PostgreSQL query

Used By:
    - core/controllers/catalog_controller.py

Returns:
    CRUD functions -> SQLAlchemy model instances or collections.

Raises:
    sqlalchemy.exc.SQLAlchemyError: On database failures.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.logger import get_logger
from core.models.catalog_model import (
    Product,
    ProductIdentifier,
    SellerOrderPolicy,
    WarehouseLocation,
)

logger = get_logger(__name__)


async def create_product(session: AsyncSession, product: Product) -> Product:
    """
    Persist a seller product record.

    Product ownership and duplicate conflict handling remain in the controller.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        product: Unsaved product model.

    Returns:
        Product: Persisted product.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the insert fails.
    """
    logger.debug("Creating product sku=%s seller=%s", product.sku, product.seller_id)
    session.add(product)
    await session.flush()
    await session.refresh(product)
    return product


async def list_products(
    session: AsyncSession,
    *,
    seller_id: UUID | None,
    limit: int,
    offset: int,
) -> list[Product]:
    """
    List product records with an optional seller filter.

    The optional seller ID supports controller-applied tenant visibility without
    embedding authorization rules in the persistence layer.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        seller_id: Optional seller UUID filter.
        limit: Maximum number of rows.
        offset: Row offset.

    Returns:
        list[Product]: Product records.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the query fails.
    """
    logger.debug("Listing products seller=%s limit=%s offset=%s", seller_id, limit, offset)
    statement = select(Product).order_by(Product.sku).limit(limit).offset(offset)
    if seller_id is not None:
        statement = statement.where(Product.seller_id == seller_id)
    result = await session.execute(statement)
    return list(result.scalars().all())


async def get_product_by_id(session: AsyncSession, product_id: UUID) -> Product | None:
    """
    Read a product by unique ID.

    This function performs no tenant access check and must be wrapped by a
    controller before returning data to a requester.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        product_id: Product UUID.

    Returns:
        Product | None: Matching product or None.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the query fails.
    """
    logger.debug("Reading product by id %s", product_id)
    result = await session.execute(select(Product).where(Product.id == product_id))
    return result.scalar_one_or_none()


async def get_product_by_sku(
    session: AsyncSession, sku: str, seller_id: UUID | None = None
) -> Product | None:
    """Read a product by SKU, with optional seller_id filter."""
    logger.debug("Reading product by sku %s seller=%s", sku, seller_id)
    stmt = select(Product).where(Product.sku == sku)
    if seller_id is not None:
        stmt = stmt.where(Product.seller_id == seller_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_location_by_code(
    session: AsyncSession, warehouse_id: UUID, code: str
) -> WarehouseLocation | None:
    """Read a warehouse location by warehouse ID and location code."""
    logger.debug("Reading location by code %s for warehouse %s", code, warehouse_id)
    stmt = select(WarehouseLocation).where(
        WarehouseLocation.warehouse_id == warehouse_id,
        WarehouseLocation.code == code,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_product_identifier(
    session: AsyncSession,
    identifier: ProductIdentifier,
) -> ProductIdentifier:
    """
    Persist a product identifier record.

    Identifier normalization and uniqueness conflict translation are owned by
    the controller while this function persists the row.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        identifier: Unsaved product identifier model.

    Returns:
        ProductIdentifier: Persisted identifier.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the insert fails.
    """
    logger.debug("Creating identifier %s", identifier.identifier_value)
    session.add(identifier)
    await session.flush()
    await session.refresh(identifier)
    return identifier


async def create_warehouse_location(
    session: AsyncSession,
    location: WarehouseLocation,
) -> WarehouseLocation:
    """
    Persist a warehouse location record.

    Warehouse assignment checks are intentionally handled before this function is
    called by the catalog controller.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        location: Unsaved warehouse location model.

    Returns:
        WarehouseLocation: Persisted location.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the insert fails.
    """
    logger.debug("Creating location %s for warehouse %s", location.code, location.warehouse_id)
    session.add(location)
    await session.flush()
    await session.refresh(location)
    return location


async def list_warehouse_locations(
    session: AsyncSession,
    *,
    warehouse_id: UUID | None,
    limit: int,
    offset: int,
) -> list[WarehouseLocation]:
    """
    List warehouse location records with an optional warehouse filter.

    Controllers use the filter to restrict non-admin users to assigned
    warehouses while preserving CRUD simplicity.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        warehouse_id: Optional warehouse UUID filter.
        limit: Maximum number of rows.
        offset: Row offset.

    Returns:
        list[WarehouseLocation]: Location records.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the query fails.
    """
    logger.debug("Listing locations warehouse=%s limit=%s offset=%s", warehouse_id, limit, offset)
    statement = (
        select(WarehouseLocation).order_by(WarehouseLocation.code).limit(limit).offset(offset)
    )
    if warehouse_id is not None:
        statement = statement.where(WarehouseLocation.warehouse_id == warehouse_id)
    result = await session.execute(statement)
    return list(result.scalars().all())


async def create_seller_order_policy(
    session: AsyncSession,
    policy: SellerOrderPolicy,
) -> SellerOrderPolicy:
    """
    Persist a seller order policy version.

    Policy decision ownership remains outside this persistence function because
    unresolved business policy must not be silently invented.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        policy: Unsaved seller order policy model.

    Returns:
        SellerOrderPolicy: Persisted policy.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the insert fails.
    """
    logger.debug("Creating seller order policy seller=%s", policy.seller_id)
    session.add(policy)
    await session.flush()
    await session.refresh(policy)
    return policy


async def list_seller_order_policies(
    session: AsyncSession,
    *,
    seller_id: UUID | None,
    limit: int,
    offset: int,
) -> list[SellerOrderPolicy]:
    """
    List seller order policy versions.

    The optional seller filter supports tenant-scoped reads while keeping policy
    access decisions in the controller.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        seller_id: Optional seller UUID filter.
        limit: Maximum number of rows.
        offset: Row offset.

    Returns:
        list[SellerOrderPolicy]: Policy records.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the query fails.
    """
    logger.debug("Listing seller policies seller=%s limit=%s offset=%s", seller_id, limit, offset)
    statement = (
        select(SellerOrderPolicy)
        .order_by(SellerOrderPolicy.seller_id, SellerOrderPolicy.version)
        .limit(limit)
        .offset(offset)
    )
    if seller_id is not None:
        statement = statement.where(SellerOrderPolicy.seller_id == seller_id)
    result = await session.execute(statement)
    return list(result.scalars().all())
