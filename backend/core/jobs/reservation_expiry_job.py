"""
Background job releasing expired inventory reservations back to available stock.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from common.logger import get_logger
from core.constants import InventoryMovementType, InventoryState, OrderStatus
from core.cruds import inventory_crud
from core.models.inventory_model import InventoryMovement
from core.models.order_model import InventoryReservation, Order, OrderLine

logger = get_logger(__name__)


async def release_expired_reservations(session: AsyncSession) -> dict[str, Any]:
    """Release expired inventory reservations back to available stock."""
    now = datetime.now(UTC)
    logger.info("Executing release_expired_reservations job at %s", now.isoformat())

    stmt = (
        select(InventoryReservation)
        .options(
            selectinload(InventoryReservation.order_line)
            .selectinload(OrderLine.order)
            .selectinload(Order.lines)
        )
        .where(
            InventoryReservation.status == "ACTIVE",
            InventoryReservation.expires_at.is_not(None),
            InventoryReservation.expires_at <= now,
        )
    )

    result = await session.execute(stmt)
    reservations = result.scalars().all()

    released_count = 0
    released_quantity_total = Decimal("0.00")

    for res in reservations:
        order_line = res.order_line
        if order_line is None or order_line.order is None:
            continue

        order = order_line.order

        # Skip orders already in physical fulfillment
        if order.status in {
            OrderStatus.PICKING.value,
            OrderStatus.PACKED.value,
            OrderStatus.SHIPPED.value,
            OrderStatus.CANCELLED.value,
            OrderStatus.CLOSED.value,
        }:
            logger.debug(
                "Skipping expired reservation %s for order %s in status %s",
                res.id,
                order.id,
                order.status,
            )
            continue

        res_bal = await inventory_crud.get_balance_for_update(
            session,
            seller_id=order.seller_id,
            product_id=res.product_id,
            warehouse_id=res.warehouse_id,
            inventory_state=InventoryState.RESERVED.value,
        )
        avail_res_qty = res_bal.quantity if res_bal is not None else Decimal("0.00")
        rel_qty = min(res.quantity, avail_res_qty)

        if rel_qty <= Decimal("0.00"):
            res.status = "EXPIRED"
            res.released_at = now
            continue

        # Post ledger movement: RESERVED -> AVAILABLE
        await inventory_crud.apply_state_transfer(
            session,
            seller_id=order.seller_id,
            product_id=res.product_id,
            from_warehouse_id=res.warehouse_id,
            from_state=InventoryState.RESERVED.value,
            to_state=InventoryState.AVAILABLE.value,
            quantity=rel_qty,
            movement_type=InventoryMovementType.RESERVATION_RELEASE.value,
            source_type="RESERVATION_EXPIRY",
            source_id=res.id,
            source_line_id=order_line.id,
            idempotency_prefix=f"EXP-{res.id}",
            actor_user_id=None,
        )

        res.status = "EXPIRED"
        res.released_at = now

        order_line.reserved_quantity = max(Decimal("0.00"), order_line.reserved_quantity - rel_qty)
        order_line.backordered_quantity += rel_qty

        # Re-evaluate order status
        has_any_reserved = any(l.reserved_quantity > Decimal("0.00") for l in order.lines)
        if not has_any_reserved:
            order.status = OrderStatus.BACKORDERED.value
        else:
            order.status = OrderStatus.PARTIALLY_RESERVED.value

        order.updated_at = now
        released_count += 1
        released_quantity_total += rel_qty

    logger.info(
        "Finished release_expired_reservations: released %d reservations (%s units)",
        released_count,
        released_quantity_total,
    )
    return {
        "released_reservations_count": released_count,
        "released_quantity_total": float(released_quantity_total),
    }
