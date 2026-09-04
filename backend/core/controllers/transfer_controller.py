"""
Transfer controller orchestrating multi-warehouse inventory transfer workflows.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, status

from common.logger import get_logger
from common.warehouse_scope import assert_seller_access, assert_warehouse_access, require_roles
from core.constants import (
    AuditActionType,
    InventoryMovementType,
    InventoryState,
    OutboxEventType,
    TransferStatus,
    UserRole,
)
from core.cruds import audit_crud, inventory_crud, outbox_crud, transfer_crud
from core.database.database import transaction_session
from core.models.inventory_model import InventoryMovement
from core.models.transfer_model import Transfer

logger = get_logger(__name__)


class TransferController:
    """Orchestrates multi-warehouse transfer operations with atomic ledger postings."""

    async def create_transfer(self, data: dict[str, Any], scope: dict[str, Any]) -> Transfer:
        """
        Create a new multi-warehouse transfer draft or request.

        Args:
            data: Transfer payload containing seller_id, origin_warehouse_id,
                  destination_warehouse_id, notes, and lines.
            scope: Authenticated user security context.

        Returns:
            Transfer: Newly created transfer model.

        Raises:
            HTTPException: 400 if origin equals destination, 403 on scope denial.
        """
        seller_id = UUID(str(data["seller_id"]))
        origin_wh_id = UUID(str(data["origin_warehouse_id"]))
        dest_wh_id = UUID(str(data["destination_warehouse_id"]))

        if origin_wh_id == dest_wh_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Origin and destination warehouses must be different.",
            )

        assert_seller_access(scope, seller_id)
        assert_warehouse_access(scope, origin_wh_id)

        actor_id = UUID(str(scope["user_id"]))
        transfer_number = f"TRF-{datetime.now(UTC).strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"

        async with transaction_session() as session:
            transfer = await transfer_crud.create_transfer(
                session,
                transfer_number=transfer_number,
                seller_id=seller_id,
                origin_warehouse_id=origin_wh_id,
                destination_warehouse_id=dest_wh_id,
                created_by_user_id=actor_id,
                status=TransferStatus.PENDING_APPROVAL.value,
                notes=data.get("notes"),
                lines_data=data.get("lines", []),
            )

            await audit_crud.create_audit_event(
                session,
                actor_user_id=actor_id,
                action_type=AuditActionType.TRANSFER_CREATED.value,
                source_record_type="transfers",
                source_record_id=transfer.id,
                metadata_json={"transfer_number": transfer_number, "status": transfer.status},
            )
            await outbox_crud.create_outbox_event(
                session,
                event_type=OutboxEventType.TRANSFER_CREATED.value,
                payload={
                    "transfer_id": str(transfer.id),
                    "transfer_number": transfer.transfer_number,
                    "seller_id": str(transfer.seller_id),
                    "origin_warehouse_id": str(transfer.origin_warehouse_id),
                    "destination_warehouse_id": str(transfer.destination_warehouse_id),
                    "status": transfer.status,
                },
            )

            reloaded = await transfer_crud.get_transfer_by_id(session, transfer.id)
            logger.info("Transfer %s created successfully", transfer.id)
            return reloaded or transfer

    async def approve_transfer(self, transfer_id: UUID, scope: dict[str, Any]) -> Transfer:
        """
        Approve transfer request enforcing segregation of duties.

        Args:
            transfer_id: Transfer UUID.
            scope: Security context.

        Returns:
            Transfer: Approved transfer entity.

        Raises:
            HTTPException: 404 if missing, 403 on permission or self-approval violation.
        """
        require_roles(
            scope,
            [
                UserRole.ADMINISTRATOR,
                UserRole.WAREHOUSE_MANAGER,
            ],
        )
        actor_id = UUID(str(scope["user_id"]))

        async with transaction_session() as session:
            transfer = await transfer_crud.get_transfer_by_id(session, transfer_id)
            if transfer is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Transfer {transfer_id} not found.",
                )

            assert_warehouse_access(scope, transfer.origin_warehouse_id)

            # Segregation of duties: Creator cannot approve unless Administrator
            if transfer.created_by_user_id == actor_id and scope.get("role") != UserRole.ADMINISTRATOR.value:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Segregation of duties violation: Transfer creator cannot self-approve.",
                )

            transfer.status = TransferStatus.APPROVED.value
            transfer.approved_by_user_id = actor_id

            # Approve line item quantities
            for line in transfer.lines:
                line.approved_quantity = line.requested_quantity

            await audit_crud.create_audit_event(
                session,
                actor_user_id=actor_id,
                action_type=AuditActionType.TRANSFER_APPROVED.value,
                source_record_type="transfers",
                source_record_id=transfer.id,
                metadata_json={"status": transfer.status},
            )
            await outbox_crud.create_outbox_event(
                session,
                event_type=OutboxEventType.TRANSFER_APPROVED.value,
                payload={
                    "transfer_id": str(transfer.id),
                    "transfer_number": transfer.transfer_number,
                    "seller_id": str(transfer.seller_id),
                    "status": transfer.status,
                },
            )

            reloaded = await transfer_crud.get_transfer_by_id(session, transfer.id)
            logger.info("Transfer %s approved by %s", transfer.id, actor_id)
            return reloaded or transfer

    async def dispatch_transfer(self, transfer_id: UUID, scope: dict[str, Any]) -> Transfer:
        """
        Dispatch transfer, moving origin AVAILABLE inventory into IN_TRANSIT.

        Args:
            transfer_id: Transfer UUID.
            scope: Security context.

        Returns:
            Transfer: Dispatched transfer entity.

        Raises:
            HTTPException: 404 if missing, 409 if insufficient stock or invalid status.
        """
        actor_id = UUID(str(scope["user_id"]))

        async with transaction_session() as session:
            transfer = await transfer_crud.get_transfer_by_id(session, transfer_id)
            if transfer is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Transfer {transfer_id} not found.",
                )

            assert_warehouse_access(scope, transfer.origin_warehouse_id)

            if transfer.status not in (TransferStatus.APPROVED.value, TransferStatus.PENDING_APPROVAL.value):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot dispatch transfer in {transfer.status} status.",
                )

            now = datetime.now(UTC)
            for line in transfer.lines:
                qty = line.approved_quantity if line.approved_quantity > Decimal("0.00") else line.requested_quantity

                # Lock and check AVAILABLE inventory balance at origin warehouse
                balance = await inventory_crud.get_balance_for_update(
                    session,
                    seller_id=transfer.seller_id,
                    product_id=line.product_id,
                    warehouse_id=transfer.origin_warehouse_id,
                    inventory_state=InventoryState.AVAILABLE.value,
                )
                avail_qty = balance.quantity if balance is not None else Decimal("0.00")

                if avail_qty < qty:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Insufficient available stock at origin for product {line.product_id}. Requested={qty}, Available={avail_qty}",
                    )

                await inventory_crud.apply_state_transfer(
                    session,
                    seller_id=transfer.seller_id,
                    product_id=line.product_id,
                    from_warehouse_id=transfer.origin_warehouse_id,
                    to_warehouse_id=transfer.destination_warehouse_id,
                    from_state=InventoryState.AVAILABLE.value,
                    to_state=InventoryState.IN_TRANSIT.value,
                    quantity=qty,
                    movement_type=InventoryMovementType.TRANSFER_DISPATCH.value,
                    source_type="transfers",
                    source_id=transfer.id,
                    source_line_id=line.id,
                    idempotency_prefix=f"trf-dispatch-{transfer.id}-{line.id}",
                    actor_user_id=actor_id,
                )
                line.dispatched_quantity = qty

            transfer.status = TransferStatus.DISPATCHED.value
            transfer.dispatched_at = now

            await audit_crud.create_audit_event(
                session,
                actor_user_id=actor_id,
                action_type=AuditActionType.TRANSFER_DISPATCHED.value,
                source_record_type="transfers",
                source_record_id=transfer.id,
                metadata_json={"status": transfer.status},
            )
            await outbox_crud.create_outbox_event(
                session,
                event_type=OutboxEventType.TRANSFER_DISPATCHED.value,
                payload={
                    "transfer_id": str(transfer.id),
                    "transfer_number": transfer.transfer_number,
                    "seller_id": str(transfer.seller_id),
                    "origin_warehouse_id": str(transfer.origin_warehouse_id),
                    "destination_warehouse_id": str(transfer.destination_warehouse_id),
                    "status": transfer.status,
                },
            )

            reloaded = await transfer_crud.get_transfer_by_id(session, transfer.id)
            logger.info("Transfer %s dispatched successfully", transfer.id)
            return reloaded or transfer

    async def receive_transfer(
        self, transfer_id: UUID, data: dict[str, Any], scope: dict[str, Any]
    ) -> Transfer:
        """
        Receive transfer at destination warehouse, converting IN_TRANSIT stock.

        Args:
            transfer_id: Transfer UUID.
            data: Payload containing received lines breakdown.
            scope: Security context.

        Returns:
            Transfer: Received or discrepancy-flagged transfer entity.

        Raises:
            HTTPException: 404 if missing, 409 on invalid state.
        """
        actor_id = UUID(str(scope["user_id"]))

        async with transaction_session() as session:
            transfer = await transfer_crud.get_transfer_by_id(session, transfer_id)
            if transfer is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Transfer {transfer_id} not found.",
                )

            assert_warehouse_access(scope, transfer.destination_warehouse_id)

            if transfer.status not in (TransferStatus.DISPATCHED.value, TransferStatus.PARTIALLY_RECEIVED.value):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot receive transfer in {transfer.status} status.",
                )

            now = datetime.now(UTC)
            line_updates = {str(item["line_id"]): item for item in data.get("lines", [])}
            has_discrepancy = False

            for line in transfer.lines:
                update_item = line_updates.get(str(line.id), {})
                good_qty = Decimal(str(update_item.get("received_good_quantity", line.dispatched_quantity)))
                damaged_qty = Decimal(str(update_item.get("received_damaged_quantity", "0.00")))
                dispatched_qty = line.dispatched_quantity

                # Deduct IN_TRANSIT stock
                m_transit_out = InventoryMovement(
                    seller_id=transfer.seller_id,
                    product_id=line.product_id,
                    warehouse_id=transfer.destination_warehouse_id,
                    inventory_state=InventoryState.IN_TRANSIT.value,
                    quantity_delta=-dispatched_qty,
                    movement_type=InventoryMovementType.TRANSFER_RECEIPT.value,
                    source_type="transfers",
                    source_id=transfer.id,
                    source_line_id=line.id,
                    idempotency_key=f"trf-rcv-out-{transfer.id}-{line.id}",
                    actor_user_id=actor_id,
                    occurred_at=now,
                )
                await inventory_crud.apply_movement(session, m_transit_out)

                # Add good qty to destination AVAILABLE
                if good_qty > Decimal("0.00"):
                    m_avail_in = InventoryMovement(
                        seller_id=transfer.seller_id,
                        product_id=line.product_id,
                        warehouse_id=transfer.destination_warehouse_id,
                        inventory_state=InventoryState.AVAILABLE.value,
                        quantity_delta=good_qty,
                        movement_type=InventoryMovementType.TRANSFER_RECEIPT.value,
                        source_type="transfers",
                        source_id=transfer.id,
                        source_line_id=line.id,
                        idempotency_key=f"trf-rcv-avail-{transfer.id}-{line.id}",
                        actor_user_id=actor_id,
                        occurred_at=now,
                    )
                    await inventory_crud.apply_movement(session, m_avail_in)

                # Add damaged qty to destination DAMAGED state
                if damaged_qty > Decimal("0.00"):
                    m_dmg_in = InventoryMovement(
                        seller_id=transfer.seller_id,
                        product_id=line.product_id,
                        warehouse_id=transfer.destination_warehouse_id,
                        inventory_state=InventoryState.DAMAGED.value,
                        quantity_delta=damaged_qty,
                        movement_type=InventoryMovementType.TRANSFER_RECEIPT.value,
                        source_type="transfers",
                        source_id=transfer.id,
                        source_line_id=line.id,
                        idempotency_key=f"trf-rcv-dmg-{transfer.id}-{line.id}",
                        actor_user_id=actor_id,
                        occurred_at=now,
                    )
                    await inventory_crud.apply_movement(session, m_dmg_in)

                line.received_good_quantity = good_qty
                line.received_damaged_quantity = damaged_qty

                # Variance detection & ledger tracking
                total_received = good_qty + damaged_qty
                if total_received < dispatched_qty:
                    missing_qty = dispatched_qty - total_received
                    line.missing_quantity = missing_qty
                    has_discrepancy = True
                    m_shrinkage = InventoryMovement(
                        seller_id=transfer.seller_id,
                        product_id=line.product_id,
                        warehouse_id=transfer.destination_warehouse_id,
                        inventory_state=InventoryState.IN_TRANSIT.value,
                        quantity_delta=Decimal("0.00"),
                        movement_type=InventoryMovementType.ADJUSTMENT.value,
                        source_type="transfers",
                        source_id=transfer.id,
                        source_line_id=line.id,
                        idempotency_key=f"trf-shrinkage-{transfer.id}-{line.id}",
                        reason_code="TRANSFER_MISSING_IN_TRANSIT",
                        reason_text=f"Transit shortage: dispatched {dispatched_qty}, received {total_received}, missing {missing_qty}",
                        actor_user_id=actor_id,
                        occurred_at=now,
                    )
                    session.add(m_shrinkage)
                elif total_received > dispatched_qty:
                    line.overage_quantity = total_received - dispatched_qty
                    has_discrepancy = True

            transfer.status = (
                TransferStatus.DISCREPANCY_REVIEW.value
                if has_discrepancy
                else TransferStatus.RECEIVED.value
            )
            transfer.received_at = now

            await audit_crud.create_audit_event(
                session,
                actor_user_id=actor_id,
                action_type=AuditActionType.TRANSFER_RECEIVED.value,
                source_record_type="transfers",
                source_record_id=transfer.id,
                metadata_json={"status": transfer.status, "has_discrepancy": has_discrepancy},
            )
            await outbox_crud.create_outbox_event(
                session,
                event_type=(
                    OutboxEventType.TRANSFER_DISCREPANCY_RECORDED.value
                    if has_discrepancy
                    else OutboxEventType.TRANSFER_RECEIVED.value
                ),
                payload={
                    "transfer_id": str(transfer.id),
                    "transfer_number": transfer.transfer_number,
                    "seller_id": str(transfer.seller_id),
                    "destination_warehouse_id": str(transfer.destination_warehouse_id),
                    "status": transfer.status,
                    "has_discrepancy": has_discrepancy,
                },
            )

            reloaded = await transfer_crud.get_transfer_by_id(session, transfer.id)
            logger.info("Transfer %s received with status %s", transfer.id, transfer.status)
            return reloaded or transfer

    async def resolve_discrepancy(
        self, transfer_id: UUID, data: dict[str, Any], scope: dict[str, Any]
    ) -> Transfer:
        """
        Resolve transfer discrepancy variances.

        Args:
            transfer_id: Transfer UUID.
            data: Resolution notes payload.
            scope: Security context.

        Returns:
            Transfer: Resolved transfer entity with status RECEIVED.
        """
        require_roles(
            scope,
            {
                UserRole.ADMINISTRATOR,
                UserRole.WAREHOUSE_MANAGER,
            },
        )
        actor_id = UUID(str(scope["user_id"]))

        async with transaction_session() as session:
            transfer = await transfer_crud.get_transfer_by_id(session, transfer_id)
            if transfer is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Transfer {transfer_id} not found.",
                )

            assert_warehouse_access(scope, transfer.destination_warehouse_id)

            transfer.status = TransferStatus.RECEIVED.value
            if data.get("notes"):
                transfer.notes = (
                    f"{transfer.notes or ''} [Discrepancy Resolved: {data.get('notes')}]"
                )

            await audit_crud.create_audit_event(
                session,
                actor_user_id=actor_id,
                action_type=AuditActionType.TRANSFER_DISCREPANCY_RESOLVED.value,
                source_record_type="transfers",
                source_record_id=transfer.id,
                metadata_json={"status": transfer.status},
            )

            reloaded = await transfer_crud.get_transfer_by_id(session, transfer.id)
            logger.info("Transfer %s discrepancy resolved", transfer.id)
            return reloaded or transfer

    async def get_transfer(self, transfer_id: UUID, scope: dict[str, Any]) -> Transfer:
        """Retrieve single transfer details."""
        async with transaction_session() as session:
            transfer = await transfer_crud.get_transfer_by_id(session, transfer_id)
            if transfer is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Transfer {transfer_id} not found.",
                )
            assert_seller_access(scope, transfer.seller_id)
            return transfer

    async def list_transfers(
        self,
        scope: dict[str, Any],
        *,
        q: str | None = None,
        seller_id: UUID | None = None,
        origin_warehouse_id: UUID | None = None,
        destination_warehouse_id: UUID | None = None,
        status_val: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Transfer], int]:
        """
        List transfers with tenant security filtering and server-backed search.

        Retrieves transfer records matching query filters and scope restrictions.

        Args:
            scope: Requester security context containing accessible tenants and facilities.
            q: Optional case-insensitive text search string.
            seller_id: Optional seller filter.
            origin_warehouse_id: Optional origin warehouse filter.
            destination_warehouse_id: Optional destination warehouse filter.
            status_val: Optional transfer status string.
            limit: Maximum records to return.
            offset: Number of records to skip.

        Returns:
            tuple[list[Transfer], int]: Tuple containing transfer entities and total record count.
        """
        logger.info("Executing TransferController.list_transfers")
        async with transaction_session() as session:
            transfers, total = await transfer_crud.list_transfers(
                session,
                q=q,
                seller_id=seller_id,
                origin_warehouse_id=origin_warehouse_id,
                destination_warehouse_id=destination_warehouse_id,
                status=status_val,
                limit=limit,
                offset=offset,
            )
            return list(transfers), total


transfer_controller = TransferController()
