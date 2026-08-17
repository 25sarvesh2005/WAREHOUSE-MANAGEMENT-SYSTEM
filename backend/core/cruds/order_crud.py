"""
Database persistence operations for customer orders, order lines, and reservations.
"""

from __future__ import annotations

from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from common.logger import get_logger
from core.models.order_model import InventoryReservation, Order, OrderLine

logger = get_logger(__name__)


async def create_order(session: AsyncSession, order: Order) -> Order:
    """
    Save a new customer order and lines.

    Args:
        session: Active async database session.
        order: Order model instance with lines populated.

    Returns:
        Order: Persisted order model instance.
    """
    logger.info(
        "Executing create_order for seller %s order %s", order.seller_id, order.seller_order_number
    )
    session.add(order)
    await session.flush()
    await session.refresh(order)
    return order


async def get_order_by_id(session: AsyncSession, order_id: UUID) -> Order | None:
    """
    Retrieve an order by primary key ID.

    Args:
        session: Active async database session.
        order_id: Order UUID.

    Returns:
        Order | None: Order model instance if found, else None.
    """
    stmt = (
        select(Order)
        .options(
            selectinload(Order.lines).selectinload(OrderLine.reservations),
        )
        .where(Order.id == order_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_order_by_seller_and_number(
    session: AsyncSession,
    seller_id: UUID,
    seller_order_number: str,
) -> Order | None:
    """
    Retrieve an order by seller ID and seller order number.

    Args:
        session: Active async database session.
        seller_id: Seller UUID.
        seller_order_number: External order reference string.

    Returns:
        Order | None: Order model instance if found, else None.
    """
    stmt = (
        select(Order)
        .options(
            selectinload(Order.lines).selectinload(OrderLine.reservations),
        )
        .where(
            Order.seller_id == seller_id,
            Order.seller_order_number == seller_order_number,
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_orders(
    session: AsyncSession,
    seller_id: UUID | None = None,
    seller_ids: Sequence[UUID] | None = None,
    warehouse_id: UUID | None = None,
    warehouse_ids: Sequence[UUID] | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[Order]:
    """
    Query orders matching search filters with pagination.

    Args:
        session: Active async database session.
        seller_id: Optional seller UUID filter.
        seller_ids: Optional seller UUID scope filter.
        warehouse_id: Optional warehouse UUID filter.
        warehouse_ids: Optional warehouse UUID scope filter.
        status: Optional status filter.
        limit: Page size cap.
        offset: Query offset.

    Returns:
        Sequence[Order]: List of matching orders.
    """
    stmt = (
        select(Order)
        .options(
            selectinload(Order.lines),
        )
        .order_by(Order.created_at.desc())
    )

    if seller_id is not None:
        stmt = stmt.where(Order.seller_id == seller_id)
    elif seller_ids is not None:
        stmt = stmt.where(Order.seller_id.in_(seller_ids))
    if warehouse_id is not None:
        stmt = stmt.where(Order.warehouse_id == warehouse_id)
    elif warehouse_ids is not None:
        stmt = stmt.where(Order.warehouse_id.in_(warehouse_ids))
    if status is not None:
        stmt = stmt.where(Order.status == status)

    stmt = stmt.limit(limit).offset(offset)
    result = await session.execute(stmt)
    return result.scalars().all()


async def create_reservation(
    session: AsyncSession,
    reservation: InventoryReservation,
) -> InventoryReservation:
    """
    Persist an active inventory reservation record.

    Args:
        session: Active async database session.
        reservation: InventoryReservation model instance.

    Returns:
        InventoryReservation: Persisted reservation record.
    """
    logger.info(
        "Creating inventory reservation for order line %s product %s qty %s",
        reservation.order_line_id,
        reservation.product_id,
        reservation.quantity,
    )
    session.add(reservation)
    await session.flush()
    await session.refresh(reservation)
    return reservation
