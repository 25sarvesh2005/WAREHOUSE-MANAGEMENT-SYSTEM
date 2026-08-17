"""
Database CRUD operations for inventory movements and balance projections.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from common.logger import get_logger
from core.models.inventory_model import (
    InventoryBalance,
    InventoryMovement,
    InventoryReconciliation,
)

logger = get_logger(__name__)


async def record_movement(
    session: AsyncSession,
    movement: InventoryMovement,
) -> InventoryMovement:
    """
    Persist an append-only inventory movement ledger record.

    Movements are strictly additive and cannot be updated or deleted.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        movement: Unsaved InventoryMovement model.

    Returns:
        InventoryMovement: Persisted movement.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If persistence fails.
    """
    logger.debug(
        "Recording movement delta=%s type=%s", movement.quantity_delta, movement.movement_type
    )
    session.add(movement)
    await session.flush()
    await session.refresh(movement)
    return movement


async def get_balance_for_update(
    session: AsyncSession,
    seller_id: UUID,
    product_id: UUID,
    warehouse_id: UUID,
    inventory_state: str,
    location_id: UUID | None = None,
) -> InventoryBalance | None:
    """
    Retrieve operational inventory balance row with SELECT FOR UPDATE row locking.

    Args:
        session: Active transaction session.
        seller_id: Seller UUID.
        product_id: Product UUID.
        warehouse_id: Warehouse UUID.
        inventory_state: Inventory state string.
        location_id: Optional location UUID.

    Returns:
        InventoryBalance | None: Locked balance model if found, else None.
    """
    stmt = (
        select(InventoryBalance)
        .where(
            InventoryBalance.seller_id == seller_id,
            InventoryBalance.product_id == product_id,
            InventoryBalance.warehouse_id == warehouse_id,
            (
                InventoryBalance.location_id == location_id
                if location_id is not None
                else InventoryBalance.location_id.is_(None)
            ),
            InventoryBalance.inventory_state == inventory_state,
        )
        .with_for_update()
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_balance_projection(
    session: AsyncSession,
    *,
    seller_id: UUID,
    product_id: UUID,
    warehouse_id: UUID,
    location_id: UUID | None = None,
    inventory_state: str,
    quantity_delta: Decimal,
) -> InventoryBalance:
    """
    Atomically update or insert the operational balance projection.

    Upserts the inventory balance for the composite scope and adds the quantity delta.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        seller_id: Seller UUID.
        product_id: Product UUID.
        warehouse_id: Warehouse UUID.
        location_id: Warehouse location UUID (or None).
        inventory_state: Inventory state label.
        quantity_delta: Signed quantity delta to apply.

    Returns:
        InventoryBalance: Updated balance projection record.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If update fails.
    """
    logger.debug(
        "Updating balance projection product=%s state=%s delta=%s",
        product_id,
        inventory_state,
        quantity_delta,
    )
    stmt = (
        select(InventoryBalance)
        .where(
            InventoryBalance.seller_id == seller_id,
            InventoryBalance.product_id == product_id,
            InventoryBalance.warehouse_id == warehouse_id,
            (
                InventoryBalance.location_id == location_id
                if location_id is not None
                else InventoryBalance.location_id.is_(None)
            ),
            InventoryBalance.inventory_state == inventory_state,
        )
        .with_for_update()
    )

    result = await session.execute(stmt)
    balance = result.scalar_one_or_none()

    if balance is None:
        new_quantity = quantity_delta
        if new_quantity < Decimal("0.00") and inventory_state in {
            "AVAILABLE",
            "RESERVED",
            "PICKED",
            "PACKED",
            "SHIPPED",
            "DAMAGED",
            "QUARANTINED",
            "RETURN_INSPECTION",
        }:
            raise ValueError(
                f"Insufficient inventory balance for state '{inventory_state}': "
                f"resulting quantity {new_quantity} cannot be negative."
            )
        balance = InventoryBalance(
            seller_id=seller_id,
            product_id=product_id,
            warehouse_id=warehouse_id,
            location_id=location_id,
            inventory_state=inventory_state,
            quantity=new_quantity,
            version=1,
        )
        session.add(balance)
    else:
        new_quantity = balance.quantity + quantity_delta
        if new_quantity < Decimal("0.00") and inventory_state in {
            "AVAILABLE",
            "RESERVED",
            "PICKED",
            "PACKED",
            "SHIPPED",
            "DAMAGED",
            "QUARANTINED",
            "RETURN_INSPECTION",
        }:
            raise ValueError(
                f"Insufficient inventory balance for state '{inventory_state}': "
                f"current {balance.quantity} + delta {quantity_delta} = {new_quantity} cannot be negative."
            )
        balance.quantity = new_quantity
        balance.version = balance.version + 1

    await session.flush()
    await session.refresh(balance)
    return balance


async def apply_movement(
    session: AsyncSession,
    movement: InventoryMovement,
) -> tuple[InventoryMovement, InventoryBalance]:
    """Atomically record an inventory movement and update the balance projection."""
    persisted_movement = await record_movement(session, movement)
    balance = await update_balance_projection(
        session,
        seller_id=movement.seller_id,
        product_id=movement.product_id,
        warehouse_id=movement.warehouse_id,
        location_id=movement.location_id,
        inventory_state=movement.inventory_state,
        quantity_delta=movement.quantity_delta,
    )
    return persisted_movement, balance


async def apply_state_transfer(
    session: AsyncSession,
    *,
    seller_id: UUID,
    product_id: UUID,
    from_warehouse_id: UUID,
    to_warehouse_id: UUID | None = None,
    from_location_id: UUID | None = None,
    to_location_id: UUID | None = None,
    from_state: str,
    to_state: str,
    quantity: Decimal,
    movement_type: str,
    source_type: str,
    source_id: UUID,
    source_line_id: UUID | None = None,
    idempotency_prefix: str,
    reason_code: str | None = None,
    reason_text: str | None = None,
    actor_user_id: UUID | None = None,
) -> tuple[InventoryMovement, InventoryMovement]:
    """Atomically transfer inventory between buckets/states in a double-entry debit/credit."""
    dest_wh = to_warehouse_id if to_warehouse_id is not None else from_warehouse_id
    m_out = InventoryMovement(
        seller_id=seller_id,
        product_id=product_id,
        warehouse_id=from_warehouse_id,
        location_id=from_location_id,
        inventory_state=from_state,
        quantity_delta=-quantity,
        movement_type=movement_type,
        source_type=source_type,
        source_id=source_id,
        source_line_id=source_line_id,
        idempotency_key=f"{idempotency_prefix}-{from_state}-OUT",
        reason_code=reason_code,
        reason_text=reason_text,
        actor_user_id=actor_user_id,
    )
    await apply_movement(session, m_out)

    m_in = InventoryMovement(
        seller_id=seller_id,
        product_id=product_id,
        warehouse_id=dest_wh,
        location_id=to_location_id,
        inventory_state=to_state,
        quantity_delta=quantity,
        movement_type=movement_type,
        source_type=source_type,
        source_id=source_id,
        source_line_id=source_line_id,
        idempotency_key=f"{idempotency_prefix}-{to_state}-IN",
        reason_code=reason_code,
        reason_text=reason_text,
        actor_user_id=actor_user_id,
    )
    await apply_movement(session, m_in)

    return m_out, m_in


async def list_balances(
    session: AsyncSession,
    *,
    seller_id: UUID | None = None,
    seller_ids: Sequence[UUID] | None = None,
    warehouse_id: UUID | None = None,
    location_id: UUID | None = None,
    product_id: UUID | None = None,
    inventory_state: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[InventoryBalance]:
    """
    Query operational inventory balances with optional filters.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        seller_id: Optional seller filter.
        seller_ids: Optional seller scope filter.
        warehouse_id: Optional warehouse filter.
        location_id: Optional location filter.
        product_id: Optional product filter.
        inventory_state: Optional state filter.
        limit: Page size.
        offset: Offset.

    Returns:
        Sequence[InventoryBalance]: Matching balance rows.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If query fails.
    """
    logger.debug("Listing balances limit=%s offset=%s", limit, offset)
    stmt = (
        select(InventoryBalance)
        .order_by(InventoryBalance.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if seller_id is not None:
        stmt = stmt.where(InventoryBalance.seller_id == seller_id)
    elif seller_ids is not None:
        stmt = stmt.where(InventoryBalance.seller_id.in_(seller_ids))
    if warehouse_id is not None:
        stmt = stmt.where(InventoryBalance.warehouse_id == warehouse_id)
    if location_id is not None:
        stmt = stmt.where(InventoryBalance.location_id == location_id)
    if product_id is not None:
        stmt = stmt.where(InventoryBalance.product_id == product_id)
    if inventory_state is not None:
        stmt = stmt.where(InventoryBalance.inventory_state == inventory_state)

    result = await session.execute(stmt)
    return result.scalars().all()


async def list_movements(
    session: AsyncSession,
    *,
    seller_id: UUID | None = None,
    warehouse_id: UUID | None = None,
    product_id: UUID | None = None,
    movement_type: str | None = None,
    source_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[InventoryMovement]:
    """
    Query append-only inventory movements with optional filters.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        seller_id: Optional seller filter.
        warehouse_id: Optional warehouse filter.
        product_id: Optional product filter.
        movement_type: Optional movement category filter.
        source_id: Optional source entity UUID filter.
        limit: Page size.
        offset: Offset.

    Returns:
        Sequence[InventoryMovement]: Matching movement rows.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If query fails.
    """
    logger.debug("Listing movements limit=%s offset=%s", limit, offset)
    stmt = (
        select(InventoryMovement)
        .order_by(InventoryMovement.recorded_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if seller_id is not None:
        stmt = stmt.where(InventoryMovement.seller_id == seller_id)
    if warehouse_id is not None:
        stmt = stmt.where(InventoryMovement.warehouse_id == warehouse_id)
    if product_id is not None:
        stmt = stmt.where(InventoryMovement.product_id == product_id)
    if movement_type is not None:
        stmt = stmt.where(InventoryMovement.movement_type == movement_type)
    if source_id is not None:
        stmt = stmt.where(InventoryMovement.source_id == source_id)

    result = await session.execute(stmt)
    return result.scalars().all()


async def compute_ledger_sums(
    session: AsyncSession,
    *,
    warehouse_id: UUID,
    seller_id: UUID | None = None,
) -> Decimal:
    """
    Compute total sum of movement quantity deltas for a warehouse/seller scope.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        warehouse_id: Target warehouse UUID.
        seller_id: Optional target seller UUID.

    Returns:
        Decimal: Total sum of movement quantity deltas.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If query fails.
    """
    stmt = select(
        func.coalesce(func.sum(InventoryMovement.quantity_delta), Decimal("0.00"))
    ).where(InventoryMovement.warehouse_id == warehouse_id)
    if seller_id is not None:
        stmt = stmt.where(InventoryMovement.seller_id == seller_id)
    result = await session.execute(stmt)
    return result.scalar_one()


async def compute_balance_sums(
    session: AsyncSession,
    *,
    warehouse_id: UUID,
    seller_id: UUID | None = None,
) -> Decimal:
    """
    Compute total sum of balance quantities for a warehouse/seller scope.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        warehouse_id: Target warehouse UUID.
        seller_id: Optional target seller UUID.

    Returns:
        Decimal: Total sum of balance quantities.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If query fails.
    """
    stmt = select(func.coalesce(func.sum(InventoryBalance.quantity), Decimal("0.00"))).where(
        InventoryBalance.warehouse_id == warehouse_id
    )
    if seller_id is not None:
        stmt = stmt.where(InventoryBalance.seller_id == seller_id)
    result = await session.execute(stmt)
    return result.scalar_one()


async def create_reconciliation(
    session: AsyncSession,
    reconciliation: InventoryReconciliation,
) -> InventoryReconciliation:
    """
    Persist an inventory reconciliation record.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        reconciliation: Unsaved InventoryReconciliation model.

    Returns:
        InventoryReconciliation: Persisted record.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If insert fails.
    """
    logger.debug("Creating reconciliation warehouse=%s", reconciliation.warehouse_id)
    session.add(reconciliation)
    await session.flush()
    await session.refresh(reconciliation)
    return reconciliation


async def rebuild_ledger_balances(
    session: AsyncSession,
    *,
    warehouse_id: UUID | None = None,
    seller_id: UUID | None = None,
) -> list[dict[str, Any]]:
    """
    Rebuild exact inventory balances from authoritative append-only movements.

    Groups all movement quantity_deltas by seller_id, warehouse_id, product_id,
    location_id, and inventory_state.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        warehouse_id: Optional target warehouse UUID filter.
        seller_id: Optional target seller UUID filter.

    Returns:
        list[dict[str, Any]]: Grouped balance records rebuilt directly from movement ledger.
    """
    stmt = (
        select(
            InventoryMovement.seller_id,
            InventoryMovement.warehouse_id,
            InventoryMovement.product_id,
            InventoryMovement.location_id,
            InventoryMovement.inventory_state,
            func.sum(InventoryMovement.quantity_delta).label("rebuilt_quantity"),
        )
        .group_by(
            InventoryMovement.seller_id,
            InventoryMovement.warehouse_id,
            InventoryMovement.product_id,
            InventoryMovement.location_id,
            InventoryMovement.inventory_state,
        )
    )

    if warehouse_id is not None:
        stmt = stmt.where(InventoryMovement.warehouse_id == warehouse_id)
    if seller_id is not None:
        stmt = stmt.where(InventoryMovement.seller_id == seller_id)

    result = await session.execute(stmt)
    rows = result.all()

    return [
        {
            "seller_id": str(row.seller_id),
            "warehouse_id": str(row.warehouse_id),
            "product_id": str(row.product_id),
            "location_id": str(row.location_id) if row.location_id else None,
            "inventory_state": str(row.inventory_state),
            "rebuilt_quantity": Decimal(str(row.rebuilt_quantity)),
        }
        for row in rows
    ]
