"""
--------------------------------------------------------------------------------
File        : core/controllers/order_controller.py
Purpose     : Controller handling order ingestion, policy reservations, and cancellations.

Responsibilities:
    - Authorize order creation, reservation, and cancellation requests.
    - Snapshot applied seller order policies at confirmation time.
    - Execute transactional inventory reservation using SELECT FOR UPDATE concurrency safety.
    - Post ledger movements for AVAILABLE -> RESERVED stock allocation.
    - Support order cancellation with compensating reservation releases.

Flow:
    Route -> OrderController -> Transaction Session -> order_crud / inventory_crud -> Response

Used By:
    - core/apis/routes/order_routes.py

Returns:
    Order model instances or HTTPExceptions on failure.

Raises:
    fastapi.HTTPException: 400 (Bad Request), 403 (Forbidden), 404 (Not Found), 409 (Conflict).
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from common.logger import get_logger
from common.warehouse_scope import assert_seller_access, assert_warehouse_access, require_roles
from core.constants import (
    AuditActionType,
    InventoryMovementType,
    InventoryState,
    OrderStatus,
    UserRole,
)
from core.controllers import catalog_controller
from core.cruds import audit_crud, catalog_crud, identity_crud, inventory_crud, order_crud
from core.database.database import transaction_session
from core.models.audit_model import AuditEvent
from core.models.inventory_model import InventoryMovement
from core.models.order_model import InventoryReservation, Order, OrderLine

logger = get_logger(__name__)


class OrderController:
    """Controller owning order ingestion and transactional inventory reservation business rules."""

    async def create_order(self, order_data: dict[str, Any], scope: dict[str, Any]) -> Order:
        """
        Ingest a new customer order draft.

        Args:
            order_data: Validated order creation dictionary.
            scope: Authenticated requester scope.

        Returns:
            Order: Created order model instance.

        Raises:
            HTTPException: If unauthorized, duplicate seller order number, or invalid product.
        """
        logger.info(
            "Executing OrderController.create_order for seller %s", order_data["seller_id"]
        )
        require_roles(
            scope,
            {
                UserRole.ADMINISTRATOR,
                UserRole.WAREHOUSE_MANAGER,
                UserRole.SELLER,
                UserRole.SERVICE_ACCOUNT,
            },
        )

        seller_id = UUID(str(order_data["seller_id"]))
        warehouse_id = UUID(str(order_data["warehouse_id"]))
        seller_order_number = str(order_data["seller_order_number"]).strip()
        actor_id = UUID(str(scope["user_id"]))

        assert_seller_access(scope, str(seller_id))
        assert_warehouse_access(scope, str(warehouse_id))

        async with transaction_session() as session:
            # Check for existing seller order number duplicate
            existing = await order_crud.get_order_by_seller_and_number(
                session,
                seller_id=seller_id,
                seller_order_number=seller_order_number,
            )
            if existing is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Order number '{seller_order_number}' already exists for this seller",
                )

            # Snapshot seller order policy if present, or assign default snapshot
            policies = await catalog_crud.list_seller_order_policies(
                session, seller_id=seller_id, limit=1, offset=0
            )
            if policies:
                pol = policies[0]
                policy_snap = {
                    "policy_id": str(pol.id),
                    "allocation_strategy": pol.allocation_strategy,
                    "allow_backorder": pol.allow_backorder,
                    "allow_partial_fulfillment": pol.allow_partial_fulfillment,
                    "reservation_expiry_minutes": pol.reservation_expiry_minutes,
                }
            else:
                policy_snap = {
                    "policy_id": None,
                    "allocation_strategy": "FIFO",
                    "allow_backorder": True,
                    "allow_partial_fulfillment": True,
                    "reservation_expiry_minutes": 60,
                }

            now = datetime.now(UTC)
            order = Order(
                seller_id=seller_id,
                seller_order_number=seller_order_number,
                warehouse_id=warehouse_id,
                channel=order_data.get("channel", "DIRECT"),
                status=OrderStatus.DRAFT.value,
                policy_snapshot=policy_snap,
                customer_name=order_data.get("customer_name"),
                shipping_address_line1=order_data.get("shipping_address_line1"),
                city=order_data.get("city"),
                state=order_data.get("state"),
                postal_code=order_data.get("postal_code"),
                created_at=now,
                updated_at=now,
            )

            # Validate products and build order lines
            for line_data in order_data["lines"]:
                product_id = UUID(str(line_data["product_id"]))
                product = await catalog_crud.get_product_by_id(session, product_id)
                if product is None or product.seller_id != seller_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Product {product_id} is invalid or does not belong to seller",
                    )
                order.lines.append(
                    OrderLine(
                        product_id=product_id,
                        ordered_quantity=Decimal(str(line_data["ordered_quantity"])),
                        reserved_quantity=Decimal("0.00"),
                        picked_quantity=Decimal("0.00"),
                        shipped_quantity=Decimal("0.00"),
                        backordered_quantity=Decimal("0.00"),
                        cancelled_quantity=Decimal("0.00"),
                        created_at=now,
                        updated_at=now,
                    )
                )

            saved_order = await order_crud.create_order(session, order)
            await audit_crud.create_audit_event(
                session,
                actor_user_id=actor_id,
                action_type=AuditActionType.ORDER_CREATED.value,
                source_record_type="orders",
                source_record_id=saved_order.id,
                metadata_json={"seller_order_number": seller_order_number},
            )
            await session.refresh(saved_order)
            logger.info("Order created successfully %s", saved_order.id)
            return saved_order

    async def get_order(self, order_id: UUID, scope: dict[str, Any]) -> Order:
        """
        Retrieve an order by ID with scope validation.

        Args:
            order_id: Order UUID.
            scope: Authenticated requester scope.

        Returns:
            Order: Order model instance.

        Raises:
            HTTPException: If order not found or forbidden scope.
        """
        async with transaction_session() as session:
            order = await order_crud.get_order_by_id(session, order_id)
            if order is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
                )

            assert_seller_access(scope, str(order.seller_id))
            if scope.get("role") != UserRole.SELLER.value:
                assert_warehouse_access(scope, str(order.warehouse_id))
            return order

    async def list_orders(
        self,
        scope: dict[str, Any],
        seller_id: UUID | None = None,
        warehouse_id: UUID | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Order]:
        """
        List customer orders filtered by seller, warehouse, or status.

        Args:
            scope: Authenticated requester scope.
            seller_id: Optional seller UUID filter.
            warehouse_id: Optional warehouse UUID filter.
            status: Optional status filter.
            limit: Page limit.
            offset: Page offset.

        Returns:
            list[Order]: Matching order models.
        """
        if seller_id is not None:
            assert_seller_access(scope, str(seller_id))
        if warehouse_id is not None:
            assert_warehouse_access(scope, str(warehouse_id))

        seller_scope: list[UUID] | None = None
        warehouse_scope: list[UUID] | None = None
        if seller_id is None and scope.get("role") == UserRole.SELLER.value:
            seller_scope = [UUID(str(value)) for value in scope.get("seller_ids", [])]
        if (
            warehouse_id is None
            and scope.get("role")
            in {
                UserRole.RECEIVER.value,
                UserRole.PICKER_PACKER.value,
                UserRole.WAREHOUSE_MANAGER.value,
            }
        ):
            warehouse_scope = [UUID(str(value)) for value in scope.get("warehouse_ids", [])]

        async with transaction_session() as session:
            orders = await order_crud.list_orders(
                session,
                seller_id=seller_id,
                seller_ids=seller_scope,
                warehouse_id=warehouse_id,
                warehouse_ids=warehouse_scope,
                status=status,
                limit=limit,
                offset=offset,
            )
            return list(orders)

    async def reserve_order(
        self,
        order_id: UUID,
        scope: dict[str, Any],
        reserve_data: dict[str, Any] | None = None,
    ) -> Order:
        """
        Execute transactional inventory reservation for an order.

        Uses SELECT FOR UPDATE concurrency safety on operational inventory balances
        to prevent double allocation and overselling.

        Args:
            order_id: Order UUID.
            scope: Authenticated requester scope.
            reserve_data: Optional notes dictionary.

        Returns:
            Order: Updated order with reservation status.

        Raises:
            HTTPException: If order not found, already cancelled/shipped, or no available stock.
        """
        logger.info("Executing OrderController.reserve_order %s", order_id)
        require_roles(
            scope,
            {
                UserRole.ADMINISTRATOR,
                UserRole.WAREHOUSE_MANAGER,
                UserRole.SELLER,
                UserRole.SERVICE_ACCOUNT,
            },
        )
        actor_id = UUID(str(scope["user_id"]))

        async with transaction_session() as session:
            order = await order_crud.get_order_by_id(session, order_id)
            if order is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
                )

            assert_seller_access(scope, str(order.seller_id))
            assert_warehouse_access(scope, str(order.warehouse_id))

            if order.status in {
                OrderStatus.CANCELLED.value,
                OrderStatus.SHIPPED.value,
                OrderStatus.CLOSED.value,
            }:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot reserve an order in {order.status} state",
                )

            total_lines = len(order.lines)
            fully_reserved_count = 0
            any_reserved = False

            now = datetime.now(UTC)

            policy = order.policy_snapshot or {}
            allow_partial = policy.get("allow_partial_fulfillment", True)
            allow_backorder = policy.get("allow_backorder", True)
            expiry_mins = int(policy.get("reservation_expiry_minutes", 60))
            expires_at = now + timedelta(minutes=expiry_mins)

            # Sort order lines deterministically by product_id to prevent database deadlocks
            sorted_lines = sorted(order.lines, key=lambda l: str(l.product_id))

            # Pre-check partial fulfillment policy if strict (allow_partial_fulfillment=False)
            if not allow_partial:
                can_fulfill_all = True
                for line in sorted_lines:
                    needed = (
                        line.ordered_quantity
                        - line.reserved_quantity
                        - line.cancelled_quantity
                    )
                    if needed > Decimal("0.00"):
                        bal = await inventory_crud.get_balance_for_update(
                            session,
                            seller_id=order.seller_id,
                            product_id=line.product_id,
                            warehouse_id=order.warehouse_id,
                            inventory_state=InventoryState.AVAILABLE.value,
                        )
                        avail = bal.quantity if bal is not None else Decimal("0.00")
                        if avail < needed:
                            can_fulfill_all = False
                            break
                if not can_fulfill_all:
                    # Cancel or backorder all unfulfilled quantities according to allow_backorder
                    for line in sorted_lines:
                        needed = (
                            line.ordered_quantity
                            - line.reserved_quantity
                            - line.cancelled_quantity
                        )
                        if needed > Decimal("0.00"):
                            if allow_backorder:
                                line.backordered_quantity = needed
                            else:
                                line.cancelled_quantity = needed
                    order.status = (
                        OrderStatus.BACKORDERED.value
                        if allow_backorder
                        else OrderStatus.CANCELLED.value
                    )
                    order.updated_at = now
                    await audit_crud.create_audit_event(
                        session,
                        actor_user_id=actor_id,
                        action_type=AuditActionType.ORDER_RESERVED.value,
                        source_record_type="orders",
                        source_record_id=order.id,
                        metadata_json={
                            "status": order.status,
                            "reason": "Strict partial fulfillment policy rejected reservation",
                        },
                    )
                    return order

            for line in sorted_lines:
                needed = line.ordered_quantity - line.reserved_quantity - line.cancelled_quantity
                if needed <= Decimal("0.00"):
                    fully_reserved_count += 1
                    continue

                # Query AVAILABLE balance with row locking (for update)
                balance = await inventory_crud.get_balance_for_update(
                    session,
                    seller_id=order.seller_id,
                    product_id=line.product_id,
                    warehouse_id=order.warehouse_id,
                    inventory_state=InventoryState.AVAILABLE.value,
                )

                available_qty = balance.quantity if balance is not None else Decimal("0.00")
                allocatable = min(needed, available_qty)

                if allocatable > Decimal("0.00"):
                    any_reserved = True
                    # 1. Post ledger movement: AVAILABLE -> RESERVED
                    m_avail_out = InventoryMovement(
                        seller_id=order.seller_id,
                        product_id=line.product_id,
                        warehouse_id=order.warehouse_id,
                        location_id=None,
                        inventory_state=InventoryState.AVAILABLE.value,
                        quantity_delta=-allocatable,
                        movement_type=InventoryMovementType.RESERVATION.value,
                        source_type="ORDER_RESERVATION",
                        source_id=order.id,
                        source_line_id=line.id,
                        idempotency_key=f"RES-{order.id}-{line.id}-AVAILABLE-OUT",
                        actor_user_id=actor_id,
                    )
                    await inventory_crud.record_movement(session, m_avail_out)
                    await inventory_crud.update_balance_projection(
                        session,
                        seller_id=order.seller_id,
                        product_id=line.product_id,
                        warehouse_id=order.warehouse_id,
                        location_id=None,
                        inventory_state=InventoryState.AVAILABLE.value,
                        quantity_delta=-allocatable,
                    )

                    m_res_in = InventoryMovement(
                        seller_id=order.seller_id,
                        product_id=line.product_id,
                        warehouse_id=order.warehouse_id,
                        location_id=None,
                        inventory_state=InventoryState.RESERVED.value,
                        quantity_delta=allocatable,
                        movement_type=InventoryMovementType.RESERVATION.value,
                        source_type="ORDER_RESERVATION",
                        source_id=order.id,
                        source_line_id=line.id,
                        idempotency_key=f"RES-{order.id}-{line.id}-RESERVED-IN",
                        actor_user_id=actor_id,
                    )
                    await inventory_crud.record_movement(session, m_res_in)
                    await inventory_crud.update_balance_projection(
                        session,
                        seller_id=order.seller_id,
                        product_id=line.product_id,
                        warehouse_id=order.warehouse_id,
                        location_id=None,
                        inventory_state=InventoryState.RESERVED.value,
                        quantity_delta=allocatable,
                    )

                    # 2. Persist inventory reservation record
                    res_rec = InventoryReservation(
                        order_line_id=line.id,
                        warehouse_id=order.warehouse_id,
                        product_id=line.product_id,
                        quantity=allocatable,
                        status="ACTIVE",
                        reserved_at=now,
                        expires_at=expires_at,
                    )
                    await order_crud.create_reservation(session, res_rec)

                    line.reserved_quantity += allocatable

                remaining_quantity = (
                    line.ordered_quantity - line.reserved_quantity - line.cancelled_quantity
                )
                if remaining_quantity <= Decimal("0.00"):
                    line.backordered_quantity = Decimal("0.00")
                    fully_reserved_count += 1
                elif allow_backorder:
                    line.backordered_quantity = remaining_quantity
                else:
                    line.backordered_quantity = Decimal("0.00")
                    line.cancelled_quantity += remaining_quantity

            # Determine order header status outcome
            if fully_reserved_count == total_lines and total_lines > 0:
                order.status = OrderStatus.RESERVED.value
            elif any_reserved:
                order.status = OrderStatus.PARTIALLY_RESERVED.value
            else:
                order.status = (
                    OrderStatus.BACKORDERED.value
                    if allow_backorder
                    else OrderStatus.CANCELLED.value
                )

            order.updated_at = now
            await audit_crud.create_audit_event(
                session,
                actor_user_id=actor_id,
                action_type=AuditActionType.ORDER_RESERVED.value,
                source_record_type="orders",
                source_record_id=order.id,
                metadata_json={"status": order.status},
            )
            reloaded_order = await order_crud.get_order_by_id(session, order.id)
            logger.info("Order %s reservation completed with status %s", order.id, order.status)
            return reloaded_order or order

    async def cancel_order(self, order_id: UUID, scope: dict[str, Any]) -> Order:
        """
        Cancel an order and release active inventory reservations.

        Args:
            order_id: Order UUID.
            scope: Authenticated requester scope.

        Returns:
            Order: Cancelled order model instance.

        Raises:
            HTTPException: If order not found or already shipped.
        """
        logger.info("Executing OrderController.cancel_order %s", order_id)
        require_roles(
            scope,
            {UserRole.ADMINISTRATOR, UserRole.WAREHOUSE_MANAGER, UserRole.SELLER},
        )
        actor_id = UUID(str(scope["user_id"]))

        async with transaction_session() as session:
            order = await order_crud.get_order_by_id(session, order_id)
            if order is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
                )

            assert_seller_access(scope, str(order.seller_id))
            assert_warehouse_access(scope, str(order.warehouse_id))

            if order.status in {OrderStatus.SHIPPED.value, OrderStatus.CANCELLED.value}:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot cancel order in {order.status} status",
                )

            now = datetime.now(UTC)

            for line in order.lines:
                if line.reserved_quantity > Decimal("0.00"):
                    rel_qty = line.reserved_quantity
                    # Release RESERVED -> AVAILABLE
                    m_res_out = InventoryMovement(
                        seller_id=order.seller_id,
                        product_id=line.product_id,
                        warehouse_id=order.warehouse_id,
                        location_id=None,
                        inventory_state=InventoryState.RESERVED.value,
                        quantity_delta=-rel_qty,
                        movement_type=InventoryMovementType.RESERVATION_RELEASE.value,
                        source_type="ORDER_CANCEL",
                        source_id=order.id,
                        source_line_id=line.id,
                        idempotency_key=f"CNC-{order.id}-{line.id}-RESERVED-OUT",
                        actor_user_id=actor_id,
                    )
                    await inventory_crud.record_movement(session, m_res_out)
                    await inventory_crud.update_balance_projection(
                        session,
                        seller_id=order.seller_id,
                        product_id=line.product_id,
                        warehouse_id=order.warehouse_id,
                        location_id=None,
                        inventory_state=InventoryState.RESERVED.value,
                        quantity_delta=-rel_qty,
                    )

                    m_avail_in = InventoryMovement(
                        seller_id=order.seller_id,
                        product_id=line.product_id,
                        warehouse_id=order.warehouse_id,
                        location_id=None,
                        inventory_state=InventoryState.AVAILABLE.value,
                        quantity_delta=rel_qty,
                        movement_type=InventoryMovementType.RESERVATION_RELEASE.value,
                        source_type="ORDER_CANCEL",
                        source_id=order.id,
                        source_line_id=line.id,
                        idempotency_key=f"CNC-{order.id}-{line.id}-AVAILABLE-IN",
                        actor_user_id=actor_id,
                    )
                    await inventory_crud.record_movement(session, m_avail_in)
                    await inventory_crud.update_balance_projection(
                        session,
                        seller_id=order.seller_id,
                        product_id=line.product_id,
                        warehouse_id=order.warehouse_id,
                        location_id=None,
                        inventory_state=InventoryState.AVAILABLE.value,
                        quantity_delta=rel_qty,
                    )

                    line.cancelled_quantity += rel_qty
                    line.reserved_quantity = Decimal("0.00")

                for res in line.reservations:
                    if res.status == "ACTIVE":
                        res.status = "RELEASED"
                        res.released_at = now

            order.status = OrderStatus.CANCELLED.value
            order.updated_at = now
            await audit_crud.create_audit_event(
                session,
                actor_user_id=actor_id,
                action_type=AuditActionType.ORDER_CANCELLED.value,
                source_record_type="orders",
                source_record_id=order.id,
                metadata_json={"seller_order_number": order.seller_order_number},
            )
            reloaded_order = await order_crud.get_order_by_id(session, order.id)
            logger.info("Order %s cancelled successfully", order.id)
            return reloaded_order or order
