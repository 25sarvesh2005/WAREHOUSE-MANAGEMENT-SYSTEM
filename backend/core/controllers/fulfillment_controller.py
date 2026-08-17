"""
Fulfillment controller owning picking tasks, packaging, and shipment dispatch.
"""

from __future__ import annotations

from datetime import UTC, datetime
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
    PickTaskStatus,
    UserRole,
)
from core.cruds import audit_crud, fulfillment_crud, inventory_crud, order_crud
from core.database.database import transaction_session
from core.models.fulfillment_model import Package, PickTask, PickTaskLine, Shipment, ShipmentEvent
from core.models.inventory_model import InventoryMovement

logger = get_logger(__name__)


class FulfillmentController:
    """Controller owning warehouse fulfillment execution and manual shipment dispatch."""

    async def create_pick_task(self, task_data: dict[str, Any], scope: dict[str, Any]) -> PickTask:
        """
        Create a warehouse worker pick task for a reserved order.

        Args:
            task_data: Validated pick task creation dictionary.
            scope: Authenticated requester scope.

        Returns:
            PickTask: Created pick task model instance.

        Raises:
            HTTPException: If order not found, not reserved, or forbidden scope.
        """
        logger.info(
            "Executing FulfillmentController.create_pick_task for order %s", task_data["order_id"]
        )
        require_roles(
            scope,
            {UserRole.ADMINISTRATOR, UserRole.WAREHOUSE_MANAGER, UserRole.PICKER_PACKER},
        )
        order_id = UUID(str(task_data["order_id"]))
        actor_id = UUID(str(scope["user_id"]))
        assigned_id = (
            UUID(str(task_data["assigned_user_id"])) if task_data.get("assigned_user_id") else None
        )

        async with transaction_session() as session:
            order = await order_crud.get_order_by_id(session, order_id)
            if order is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
                )

            assert_warehouse_access(scope, str(order.warehouse_id))

            if order.status not in {
                OrderStatus.RESERVED.value,
                OrderStatus.PARTIALLY_RESERVED.value,
            }:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot create pick task for order in {order.status} state",
                )

            now = datetime.now(UTC)
            pick_task = PickTask(
                order_id=order.id,
                warehouse_id=order.warehouse_id,
                assigned_user_id=assigned_id,
                status=PickTaskStatus.ASSIGNED.value,
                priority=int(task_data.get("priority", 1)),
                created_at=now,
                updated_at=now,
            )

            for line in order.lines:
                if line.reserved_quantity > Decimal("0.00"):
                    pick_task.lines.append(
                        PickTaskLine(
                            order_line_id=line.id,
                            product_id=line.product_id,
                            location_id=None,
                            requested_quantity=line.reserved_quantity,
                            picked_quantity=Decimal("0.00"),
                            short_quantity=Decimal("0.00"),
                            created_at=now,
                            updated_at=now,
                        )
                    )

            if not pick_task.lines:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Order has no reserved quantities to pick",
                )

            order.status = OrderStatus.PICKING.value
            order.updated_at = now

            saved_task = await fulfillment_crud.create_pick_task(session, pick_task)
            await audit_crud.create_audit_event(
                session,
                actor_user_id=actor_id,
                action_type=AuditActionType.PICK_TASK_CREATED.value,
                source_record_type="pick_tasks",
                source_record_id=saved_task.id,
                metadata_json={"order_id": str(order.id)},
            )
            await session.refresh(saved_task)
            logger.info("Pick task created successfully %s", saved_task.id)
            return saved_task

    async def get_pick_task(self, pick_task_id: UUID, scope: dict[str, Any]) -> PickTask:
        """
        Retrieve a pick task by ID with scope authorization.

        Args:
            pick_task_id: Pick task UUID.
            scope: Authenticated requester scope.

        Returns:
            PickTask: Pick task model instance.

        Raises:
            HTTPException: If pick task missing or forbidden.
        """
        require_roles(
            scope,
            {UserRole.ADMINISTRATOR, UserRole.WAREHOUSE_MANAGER, UserRole.PICKER_PACKER},
        )

        async with transaction_session() as session:
            task = await fulfillment_crud.get_pick_task_by_id(session, pick_task_id)
            if task is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Pick task not found"
                )

            assert_warehouse_access(scope, str(task.warehouse_id))
            return task

    async def list_pick_tasks(
        self,
        scope: dict[str, Any],
        warehouse_id: UUID | None = None,
        assigned_user_id: UUID | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PickTask]:
        """
        List warehouse pick tasks filtered by warehouse, worker assignment, or status.

        Args:
            scope: Authenticated requester scope.
            warehouse_id: Optional warehouse UUID filter.
            assigned_user_id: Optional worker UUID filter.
            status: Optional status filter.
            limit: Page limit.
            offset: Page offset.

        Returns:
            list[PickTask]: Matching pick task models.
        """
        require_roles(
            scope,
            {UserRole.ADMINISTRATOR, UserRole.WAREHOUSE_MANAGER, UserRole.PICKER_PACKER},
        )
        if warehouse_id is not None:
            assert_warehouse_access(scope, str(warehouse_id))

        warehouse_scope: list[UUID] | None = None
        if warehouse_id is None and scope.get("role") in {
            UserRole.PICKER_PACKER.value,
            UserRole.WAREHOUSE_MANAGER.value,
            UserRole.RECEIVER.value,
        }:
            warehouse_scope = [UUID(str(value)) for value in scope.get("warehouse_ids", [])]

        async with transaction_session() as session:
            tasks = await fulfillment_crud.list_pick_tasks(
                session,
                warehouse_id=warehouse_id,
                warehouse_ids=warehouse_scope,
                assigned_user_id=assigned_user_id,
                status=status,
                limit=limit,
                offset=offset,
            )
            return list(tasks)

    async def complete_pick_task(
        self,
        pick_task_id: UUID,
        completion_data: dict[str, Any],
        scope: dict[str, Any],
    ) -> PickTask:
        """
        Execute worker pick task completion, handling normal picks and short-pick exceptions.

        Args:
            pick_task_id: Pick task UUID.
            completion_data: Validated line item pick results payload.
            scope: Authenticated requester scope.

        Returns:
            PickTask: Completed pick task model.

        Raises:
            HTTPException: If task missing, already finished, or forbidden.
        """
        logger.info("Executing FulfillmentController.complete_pick_task %s", pick_task_id)
        require_roles(
            scope,
            {UserRole.ADMINISTRATOR, UserRole.WAREHOUSE_MANAGER, UserRole.PICKER_PACKER},
        )
        actor_id = UUID(str(scope["user_id"]))

        async with transaction_session() as session:
            task = await fulfillment_crud.get_pick_task_by_id(session, pick_task_id)
            if task is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Pick task not found"
                )

            assert_warehouse_access(scope, str(task.warehouse_id))

            if task.status in {
                PickTaskStatus.COMPLETED.value,
                PickTaskStatus.SHORT_PICK_EXCEPTION.value,
            }:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Pick task is already in {task.status} status",
                )

            order = await order_crud.get_order_by_id(session, task.order_id)
            if order is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
                )

            now = datetime.now(UTC)
            has_short_pick = False
            line_map = {line.id: line for line in task.lines}

            for line_item in completion_data["lines"]:
                line_id = UUID(str(line_item["pick_task_line_id"]))
                picked_qty = Decimal(str(line_item["picked_quantity"]))
                short_qty = Decimal(str(line_item.get("short_quantity", "0.00")))

                task_line = line_map.get(line_id)
                if task_line is None:
                    continue

                task_line.picked_quantity = picked_qty
                task_line.short_quantity = short_qty

                # Find matching order line
                for ol in order.lines:
                    if ol.id == task_line.order_line_id:
                        ol.picked_quantity += picked_qty
                        if short_qty > Decimal("0.00"):
                            has_short_pick = True
                            ol.reserved_quantity -= short_qty
                            ol.backordered_quantity += short_qty
                            await inventory_crud.apply_state_transfer(
                                session,
                                seller_id=order.seller_id,
                                product_id=ol.product_id,
                                from_warehouse_id=order.warehouse_id,
                                from_location_id=task_line.location_id,
                                to_location_id=task_line.location_id,
                                from_state=InventoryState.RESERVED.value,
                                to_state=InventoryState.QUARANTINED.value,
                                quantity=short_qty,
                                movement_type=InventoryMovementType.SHORT_PICK_CORRECTION.value,
                                source_type="SHORT_PICK",
                                source_id=task.id,
                                source_line_id=task_line.id,
                                idempotency_prefix=f"SHORT-{task.id}-{task_line.id}",
                                reason_code="SHORT_PICK_MISSING_STOCK",
                                reason_text="Physical item missing from bin during picking; moved to quarantine for cycle count",
                                actor_user_id=actor_id,
                            )

            if has_short_pick:
                task.status = PickTaskStatus.SHORT_PICK_EXCEPTION.value
                order.status = OrderStatus.PARTIALLY_RESERVED.value
            else:
                task.status = PickTaskStatus.COMPLETED.value
                order.status = OrderStatus.PACKED.value

            task.completed_at = now
            task.updated_at = now
            order.updated_at = now

            await audit_crud.create_audit_event(
                session,
                actor_user_id=actor_id,
                action_type=AuditActionType.PICK_TASK_COMPLETED.value,
                source_record_type="pick_tasks",
                source_record_id=task.id,
                metadata_json={"status": task.status, "has_short_pick": has_short_pick},
            )
            await session.refresh(task)
            logger.info("Pick task %s completed with status %s", task.id, task.status)
            return task

    async def create_shipment(self, ship_data: dict[str, Any], scope: dict[str, Any]) -> Shipment:
        """
        Create a manual order shipment dispatch record and post SHIPPED inventory movements.

        Args:
            ship_data: Validated shipment creation dictionary.
            scope: Authenticated requester scope.

        Returns:
            Shipment: Created shipment model instance.

        Raises:
            HTTPException: If order not found, not packed, or duplicate tracking number.
        """
        logger.info(
            "Executing FulfillmentController.create_shipment for order %s", ship_data["order_id"]
        )
        require_roles(
            scope,
            {UserRole.ADMINISTRATOR, UserRole.WAREHOUSE_MANAGER, UserRole.PICKER_PACKER},
        )
        order_id = UUID(str(ship_data["order_id"]))
        warehouse_id = UUID(str(ship_data["warehouse_id"]))
        tracking_number = str(ship_data["tracking_number"]).strip()
        actor_id = UUID(str(scope["user_id"]))

        assert_warehouse_access(scope, str(warehouse_id))

        async with transaction_session() as session:
            order = await order_crud.get_order_by_id(session, order_id)
            if order is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
                )

            if order.warehouse_id != warehouse_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Shipment warehouse must match order warehouse",
                )

            assert_warehouse_access(scope, str(order.warehouse_id))

            if order.status not in {
                OrderStatus.PACKED.value,
                OrderStatus.PICKING.value,
                OrderStatus.RESERVED.value,
            }:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot ship order in {order.status} state",
                )

            now = datetime.now(UTC)

            shipment = Shipment(
                order_id=order.id,
                warehouse_id=warehouse_id,
                carrier=ship_data.get("carrier", "MANUAL_CARRIER"),
                service_level=ship_data.get("service_level", "GROUND"),
                tracking_number=tracking_number,
                status="SHIPPED",
                shipped_at=now,
                created_at=now,
                updated_at=now,
            )

            # Attach packages if provided
            for pkg_item in ship_data.get("packages", []):
                shipment.packages.append(
                    Package(
                        order_id=order.id,
                        box_type=pkg_item.get("box_type", "CUSTOM"),
                        weight_lbs=(
                            Decimal(str(pkg_item["weight_lbs"]))
                            if pkg_item.get("weight_lbs")
                            else None
                        ),
                        length_in=(
                            Decimal(str(pkg_item["length_in"]))
                            if pkg_item.get("length_in")
                            else None
                        ),
                        width_in=(
                            Decimal(str(pkg_item["width_in"]))
                            if pkg_item.get("width_in")
                            else None
                        ),
                        height_in=(
                            Decimal(str(pkg_item["height_in"]))
                            if pkg_item.get("height_in")
                            else None
                        ),
                    )
                )

            # Post SHIPPED inventory movements for each order line item
            for line in order.lines:
                ship_qty = (
                    line.picked_quantity
                    if line.picked_quantity > Decimal("0.00")
                    else line.reserved_quantity
                )
                if ship_qty > Decimal("0.00"):
                    await inventory_crud.apply_state_transfer(
                        session,
                        seller_id=order.seller_id,
                        product_id=line.product_id,
                        from_warehouse_id=warehouse_id,
                        from_state=InventoryState.RESERVED.value,
                        to_state=InventoryState.SHIPPED.value,
                        quantity=ship_qty,
                        movement_type=InventoryMovementType.SHIPMENT.value,
                        source_type="SHIPMENT",
                        source_id=order.id,
                        source_line_id=line.id,
                        idempotency_prefix=f"SHP-{order.id}-{line.id}",
                        actor_user_id=actor_id,
                    )
                    line.shipped_quantity += ship_qty
                    line.reserved_quantity = Decimal("0.00")

            order.status = OrderStatus.SHIPPED.value
            order.updated_at = now

            saved_shipment = await fulfillment_crud.create_shipment(session, shipment)

            event = ShipmentEvent(
                shipment_id=saved_shipment.id,
                event_type="DISPATCHED",
                details=f"Order dispatched via {saved_shipment.carrier} tracking {tracking_number}",
            )
            await fulfillment_crud.add_shipment_event(session, event)

            await audit_crud.create_audit_event(
                session,
                actor_user_id=actor_id,
                action_type=AuditActionType.SHIPMENT_DISPATCHED.value,
                source_record_type="shipments",
                source_record_id=saved_shipment.id,
                metadata_json={
                    "tracking_number": tracking_number,
                    "carrier": saved_shipment.carrier,
                },
            )
            reloaded_shipment = await fulfillment_crud.get_shipment_by_id(
                session, saved_shipment.id
            )
            logger.info(
                "Shipment created successfully %s tracking %s", saved_shipment.id, tracking_number
            )
            return reloaded_shipment or saved_shipment

    async def get_shipment(self, shipment_id: UUID, scope: dict[str, Any]) -> Shipment:
        """
        Retrieve shipment details by ID.

        Args:
            shipment_id: Shipment UUID.
            scope: Authenticated requester scope.

        Returns:
            Shipment: Shipment model instance.

        Raises:
            HTTPException: If shipment missing or forbidden.
        """
        async with transaction_session() as session:
            shipment = await fulfillment_crud.get_shipment_by_id(session, shipment_id)
            if shipment is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found"
                )

            order = await order_crud.get_order_by_id(session, shipment.order_id)
            if order is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Shipment order not found",
                )
            assert_seller_access(scope, str(order.seller_id))
            if scope.get("role") != UserRole.SELLER.value:
                assert_warehouse_access(scope, str(shipment.warehouse_id))
            return shipment

    async def list_shipments(
        self,
        scope: dict[str, Any],
        order_id: UUID | None = None,
        warehouse_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Shipment]:
        """
        List shipments filtered by order or warehouse facility.

        Args:
            scope: Authenticated requester scope.
            order_id: Optional order UUID filter.
            warehouse_id: Optional warehouse UUID filter.
            limit: Page limit.
            offset: Page offset.

        Returns:
            list[Shipment]: Matching shipment model records.
        """
        if warehouse_id is not None and scope.get("role") != UserRole.SELLER.value:
            assert_warehouse_access(scope, str(warehouse_id))

        seller_scope: list[UUID] | None = None
        warehouse_scope: list[UUID] | None = None
        if scope.get("role") == UserRole.SELLER.value:
            seller_scope = [UUID(str(value)) for value in scope.get("seller_ids", [])]
        elif warehouse_id is None and scope.get("role") in {
            UserRole.PICKER_PACKER.value,
            UserRole.WAREHOUSE_MANAGER.value,
            UserRole.RECEIVER.value,
        }:
            warehouse_scope = [UUID(str(value)) for value in scope.get("warehouse_ids", [])]

        async with transaction_session() as session:
            if order_id is not None:
                order = await order_crud.get_order_by_id(session, order_id)
                if order is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
                    )
                assert_seller_access(scope, str(order.seller_id))
                if scope.get("role") != UserRole.SELLER.value:
                    assert_warehouse_access(scope, str(order.warehouse_id))
            shipments = await fulfillment_crud.list_shipments(
                session,
                order_id=order_id,
                seller_ids=seller_scope,
                warehouse_id=warehouse_id,
                warehouse_ids=warehouse_scope,
                limit=limit,
                offset=offset,
            )
            return list(shipments)


fulfillment_controller = FulfillmentController()
