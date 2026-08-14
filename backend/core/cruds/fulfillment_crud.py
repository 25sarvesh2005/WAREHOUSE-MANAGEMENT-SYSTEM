"""
--------------------------------------------------------------------------------
File        : core/cruds/fulfillment_crud.py
Purpose     : Async CRUD operations for pick tasks, packages, and manual shipments.

Responsibilities:
    - Persist warehouse pick tasks and pick lines.
    - Fetch pick tasks by ID or warehouse scope filters.
    - Save package measurements and manual shipment records.
    - Log shipment event history streams.

Flow:
    Controller -> fulfillment_crud -> AsyncSession -> PostgreSQL

Used By:
    - core/controllers/fulfillment_controller.py

Returns:
    PickTask / Package / Shipment model instances or sequences.

Raises:
    Does NOT raise HTTPException. Returns None or model instances.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from common.logger import get_logger
from core.models.fulfillment_model import Package, PickTask, PickTaskLine, Shipment, ShipmentEvent
from core.models.order_model import Order

logger = get_logger(__name__)


async def create_pick_task(session: AsyncSession, pick_task: PickTask) -> PickTask:
    """
    Save a new warehouse pick task.

    Args:
        session: Active async database session.
        pick_task: PickTask model instance with lines populated.

    Returns:
        PickTask: Persisted pick task instance.
    """
    logger.info(
        "Executing create_pick_task for order %s warehouse %s",
        pick_task.order_id,
        pick_task.warehouse_id,
    )
    session.add(pick_task)
    await session.flush()
    await session.refresh(pick_task)
    return pick_task


async def get_pick_task_by_id(session: AsyncSession, pick_task_id: UUID) -> PickTask | None:
    """
    Retrieve a pick task by primary key ID.

    Args:
        session: Active async database session.
        pick_task_id: Pick task UUID.

    Returns:
        PickTask | None: PickTask model if found, else None.
    """
    stmt = (
        select(PickTask)
        .options(
            selectinload(PickTask.lines),
        )
        .where(PickTask.id == pick_task_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_pick_tasks(
    session: AsyncSession,
    warehouse_id: UUID | None = None,
    warehouse_ids: Sequence[UUID] | None = None,
    assigned_user_id: UUID | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[PickTask]:
    """
    List warehouse pick tasks filtered by warehouse, worker assignment, or status.

    Args:
        session: Active async database session.
        warehouse_id: Optional warehouse UUID filter.
        warehouse_ids: Optional warehouse UUID scope filter.
        assigned_user_id: Optional worker UUID filter.
        status: Optional status filter.
        limit: Page size cap.
        offset: Query offset.

    Returns:
        Sequence[PickTask]: Matching pick task instances.
    """
    stmt = (
        select(PickTask)
        .options(
            selectinload(PickTask.lines),
        )
        .order_by(PickTask.created_at.desc())
    )

    if warehouse_id is not None:
        stmt = stmt.where(PickTask.warehouse_id == warehouse_id)
    elif warehouse_ids is not None:
        stmt = stmt.where(PickTask.warehouse_id.in_(warehouse_ids))
    if assigned_user_id is not None:
        stmt = stmt.where(PickTask.assigned_user_id == assigned_user_id)
    if status is not None:
        stmt = stmt.where(PickTask.status == status)

    stmt = stmt.limit(limit).offset(offset)
    result = await session.execute(stmt)
    return result.scalars().all()


async def create_package(session: AsyncSession, package: Package) -> Package:
    """
    Save physical package dimensions for an order shipment.

    Args:
        session: Active async database session.
        package: Package model instance.

    Returns:
        Package: Persisted package record.
    """
    session.add(package)
    await session.flush()
    await session.refresh(package)
    return package


async def create_shipment(session: AsyncSession, shipment: Shipment) -> Shipment:
    """
    Save a new manual order shipment dispatch record.

    Args:
        session: Active async database session.
        shipment: Shipment model instance.

    Returns:
        Shipment: Persisted shipment record.
    """
    logger.info(
        "Executing create_shipment for order %s tracking %s",
        shipment.order_id,
        shipment.tracking_number,
    )
    session.add(shipment)
    await session.flush()
    await session.refresh(shipment)
    return shipment


async def get_shipment_by_id(session: AsyncSession, shipment_id: UUID) -> Shipment | None:
    """
    Retrieve a shipment record by primary key ID.

    Args:
        session: Active async database session.
        shipment_id: Shipment UUID.

    Returns:
        Shipment | None: Shipment model instance if found, else None.
    """
    stmt = (
        select(Shipment)
        .options(
            selectinload(Shipment.packages),
            selectinload(Shipment.events),
        )
        .where(Shipment.id == shipment_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_shipments(
    session: AsyncSession,
    order_id: UUID | None = None,
    seller_ids: Sequence[UUID] | None = None,
    warehouse_id: UUID | None = None,
    warehouse_ids: Sequence[UUID] | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[Shipment]:
    """
    List shipments filtered by order ID or warehouse facility.

    Args:
        session: Active async database session.
        order_id: Optional order UUID filter.
        seller_ids: Optional seller UUID scope filter.
        warehouse_id: Optional warehouse UUID filter.
        warehouse_ids: Optional warehouse UUID scope filter.
        limit: Page size cap.
        offset: Query offset.

    Returns:
        Sequence[Shipment]: List of matching shipments.
    """
    stmt = (
        select(Shipment)
        .options(
            selectinload(Shipment.packages),
            selectinload(Shipment.events),
        )
        .order_by(Shipment.created_at.desc())
    )

    if order_id is not None:
        stmt = stmt.where(Shipment.order_id == order_id)
    if seller_ids is not None:
        stmt = stmt.join(Order, Shipment.order_id == Order.id).where(
            Order.seller_id.in_(seller_ids)
        )
    if warehouse_id is not None:
        stmt = stmt.where(Shipment.warehouse_id == warehouse_id)
    elif warehouse_ids is not None:
        stmt = stmt.where(Shipment.warehouse_id.in_(warehouse_ids))

    stmt = stmt.limit(limit).offset(offset)
    result = await session.execute(stmt)
    return result.scalars().all()


async def add_shipment_event(session: AsyncSession, event: ShipmentEvent) -> ShipmentEvent:
    """
    Add an audit event to a shipment history log.

    Args:
        session: Active async database session.
        event: ShipmentEvent model instance.

    Returns:
        ShipmentEvent: Persisted shipment event instance.
    """
    session.add(event)
    await session.flush()
    await session.refresh(event)
    return event
