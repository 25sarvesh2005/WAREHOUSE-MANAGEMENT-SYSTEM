"""
Receiving controller managing inbound shipment workflows and quality disposition.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Sequence
from uuid import UUID

from fastapi import HTTPException, status

from common.logger import get_logger
from common.pagination import normalize_pagination
from common.warehouse_scope import assert_seller_access, assert_warehouse_access, require_roles
from core.constants import (
    AuditActionType,
    InventoryMovementType,
    InventoryState,
    ReceiptStatus,
    UserRole,
)
from core.cruds import audit_crud, catalog_crud, identity_crud, inventory_crud, receiving_crud
from core.database.database import transaction_session
from core.models.inventory_model import InventoryMovement
from core.models.receiving_model import Receipt, ReceiptEvent, ReceiptLine

logger = get_logger(__name__)


class ReceivingController:
    """Controller for receiving receipt lifecycle and ledger movement generation."""

    async def create_receipt(
        self,
        receipt_data: dict[str, Any],
        scope: dict[str, Any],
    ) -> Receipt:
        """
        Create a new receiving receipt draft or sync an offline client draft.

        Args:
            receipt_data: Validated receipt payload.
            scope: Authenticated requester scope.

        Returns:
            Receipt: Persisted receipt model.

        Raises:
            HTTPException: If unauthorized, duplicate receipt exists, or entities missing.
        """
        logger.info("Executing ReceivingController.create_receipt")
        require_roles(
            scope,
            {UserRole.ADMINISTRATOR, UserRole.WAREHOUSE_MANAGER, UserRole.RECEIVER},
        )
        actor_id = UUID(str(scope["user_id"]))
        seller_id = UUID(str(receipt_data["seller_id"]))
        warehouse_id = UUID(str(receipt_data["warehouse_id"]))

        assert_seller_access(scope, str(seller_id))
        assert_warehouse_access(scope, str(warehouse_id))

        client_draft_id = receipt_data.get("client_draft_id")
        source_type = str(receipt_data["source_type"])
        source_ref = str(receipt_data["source_reference"]).strip()

        async with transaction_session() as session:
            # Check for offline draft idempotency
            if client_draft_id:
                existing_draft = await receiving_crud.get_receipt_by_client_draft_id(
                    session, client_draft_id
                )
                if existing_draft is not None:
                    logger.info("Returning existing client draft receipt %s", existing_draft.id)
                    return existing_draft

            # Check duplicate completed receipt
            duplicate = await receiving_crud.find_existing_completed_receipt(
                session,
                warehouse_id=warehouse_id,
                source_type=source_type,
                source_reference=source_ref,
            )
            if duplicate is not None:
                logger.warning("Duplicate completed receipt detected for ref %s", source_ref)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A completed receipt with this tracking/source reference already exists",
                )

            seller = await identity_crud.get_seller_by_id(session, seller_id)
            if seller is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Seller not found"
                )

            warehouse = await identity_crud.get_warehouse_by_id(session, warehouse_id)
            if warehouse is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found"
                )

            receipt = Receipt(
                receipt_number=receiving_crud.generate_receipt_number(),
                seller_id=seller_id,
                warehouse_id=warehouse_id,
                source_type=source_type,
                source_reference=source_ref,
                client_draft_id=client_draft_id,
                status=ReceiptStatus.DRAFT.value,
                started_by_user_id=actor_id,
                actual_arrival_at=datetime.now(UTC),
            )
            await receiving_crud.create_receipt(session, receipt)

            event = ReceiptEvent(
                receipt_id=receipt.id,
                event_type="CREATED",
                actor_user_id=actor_id,
                details=f"Receipt draft created for source {source_ref}",
            )
            await receiving_crud.add_receipt_event(session, event)

            await audit_crud.create_audit_event(
                session,
                actor_user_id=actor_id,
                action_type=AuditActionType.RECEIPT_CREATED.value,
                source_record_type="receipts",
                source_record_id=receipt.id,
                metadata_json={"receipt_number": receipt.receipt_number},
            )
            logger.info("Receipt draft created successfully %s", receipt.id)
            return receipt

    async def get_receipt(self, receipt_id: UUID, scope: dict[str, Any]) -> Receipt:
        """
        Fetch receipt details by ID.

        Args:
            receipt_id: Receipt UUID.
            scope: Authenticated requester scope.

        Returns:
            Receipt: Matching receipt model.

        Raises:
            HTTPException: If not found or access denied.
        """
        async with transaction_session() as session:
            receipt = await receiving_crud.get_receipt_by_id(session, receipt_id)
            if receipt is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found"
                )
            assert_seller_access(scope, str(receipt.seller_id))
            assert_warehouse_access(scope, str(receipt.warehouse_id))
            return receipt

    async def list_receipts(
        self,
        scope: dict[str, Any],
        *,
        seller_id: UUID | None,
        warehouse_id: UUID | None,
        receipt_status: str | None,
        limit: int,
        offset: int,
    ) -> Sequence[Receipt]:
        """
        List receiving receipts scoped to requester permissions.

        Args:
            scope: Authenticated requester scope.
            seller_id: Optional seller filter.
            warehouse_id: Optional warehouse filter.
            receipt_status: Optional status filter.
            limit: Page size.
            offset: Offset.

        Returns:
            Sequence[Receipt]: Matching receipt records.

        Raises:
            HTTPException: If scope access is denied.
        """
        normalized_limit, normalized_offset = normalize_pagination(limit, offset)
        if seller_id is not None:
            assert_seller_access(scope, str(seller_id))
        if warehouse_id is not None:
            assert_warehouse_access(scope, str(warehouse_id))

        async with transaction_session() as session:
            return await receiving_crud.list_receipts(
                session,
                seller_id=seller_id,
                warehouse_id=warehouse_id,
                status=receipt_status,
                limit=normalized_limit,
                offset=normalized_offset,
            )

    async def save_line_item(
        self,
        receipt_id: UUID,
        line_data: dict[str, Any],
        scope: dict[str, Any],
    ) -> ReceiptLine:
        """
        Add or update a line item on an active receipt.

        Args:
            receipt_id: Target receipt UUID.
            line_data: Validated line item payload.
            scope: Authenticated requester scope.

        Returns:
            ReceiptLine: Persisted line item.

        Raises:
            HTTPException: If receipt is completed/cancelled or product not found.
        """
        require_roles(
            scope,
            {UserRole.ADMINISTRATOR, UserRole.WAREHOUSE_MANAGER, UserRole.RECEIVER},
        )
        actor_id = UUID(str(scope["user_id"]))
        product_id = UUID(str(line_data["product_id"]))

        async with transaction_session() as session:
            receipt = await receiving_crud.get_receipt_by_id(session, receipt_id)
            if receipt is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found"
                )

            if receipt.status in {ReceiptStatus.COMPLETED.value, ReceiptStatus.CANCELLED.value}:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot modify line items on a {receipt.status} receipt",
                )

            assert_seller_access(scope, str(receipt.seller_id))
            assert_warehouse_access(scope, str(receipt.warehouse_id))

            product = await catalog_crud.get_product_by_id(session, product_id)
            if product is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
                )

            if product.seller_id != receipt.seller_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Product SKU does not belong to the receipt seller",
                )

            exp_qty = Decimal(str(line_data.get("expected_quantity", "0.00")))
            sell_qty = Decimal(str(line_data.get("sellable_quantity", "0.00")))
            dam_qty = Decimal(str(line_data.get("damaged_quantity", "0.00")))
            quar_qty = Decimal(str(line_data.get("quarantined_quantity", "0.00")))

            received_total = sell_qty + dam_qty + quar_qty
            shortage = (
                max(Decimal("0.00"), exp_qty - received_total)
                if exp_qty > Decimal("0.00")
                else Decimal("0.00")
            )
            overage = (
                max(Decimal("0.00"), received_total - exp_qty)
                if exp_qty > Decimal("0.00")
                else Decimal("0.00")
            )

            # Check if line already exists on receipt
            existing_line = next((l for l in receipt.lines if l.product_id == product_id), None)
            if existing_line is None:
                line = ReceiptLine(
                    receipt_id=receipt_id,
                    product_id=product_id,
                    expected_quantity=exp_qty,
                    sellable_quantity=sell_qty,
                    damaged_quantity=dam_qty,
                    quarantined_quantity=quar_qty,
                    shortage_quantity=shortage,
                    overage_quantity=overage,
                    notes=line_data.get("notes"),
                )
            else:
                line = existing_line
                line.expected_quantity = exp_qty
                line.sellable_quantity = sell_qty
                line.damaged_quantity = dam_qty
                line.quarantined_quantity = quar_qty
                line.shortage_quantity = shortage
                line.overage_quantity = overage
                line.notes = line_data.get("notes")

            await receiving_crud.upsert_receipt_line(session, line)

            if receipt.status == ReceiptStatus.DRAFT.value:
                receipt.status = ReceiptStatus.IN_PROGRESS.value

            event = ReceiptEvent(
                receipt_id=receipt_id,
                event_type="LINE_UPDATED",
                actor_user_id=actor_id,
                details=(
                    f"Line updated for product {product.sku}: "
                    f"sellable={sell_qty}, damaged={dam_qty}, quar={quar_qty}"
                ),
            )
            await receiving_crud.add_receipt_event(session, event)
            logger.info(
                "Saved receipt line item for receipt %s product %s", receipt_id, product_id
            )
            return line

    async def complete_receipt(
        self,
        receipt_id: UUID,
        scope: dict[str, Any],
        complete_data: dict[str, Any],
    ) -> Receipt:
        """
        Atomically complete a receiving receipt and generate inventory movements.

        Movements are posted per line item:
        - AVAILABLE state for sellable_quantity
        - DAMAGED state for damaged_quantity
        - QUARANTINED state for quarantined_quantity

        Args:
            receipt_id: Receipt UUID.
            scope: Authenticated requester scope.
            complete_data: Additional completion notes payload.

        Returns:
            Receipt: Completed receipt model.

        Raises:
            HTTPException: If receipt has no lines, is already completed/cancelled, or duplicate.
        """
        logger.info("Executing ReceivingController.complete_receipt %s", receipt_id)
        require_roles(
            scope,
            {UserRole.ADMINISTRATOR, UserRole.WAREHOUSE_MANAGER, UserRole.RECEIVER},
        )
        actor_id = UUID(str(scope["user_id"]))

        async with transaction_session() as session:
            receipt = await receiving_crud.get_receipt_by_id(session, receipt_id)
            if receipt is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found"
                )

            if receipt.status == ReceiptStatus.COMPLETED.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Receipt is already completed",
                )

            if receipt.status == ReceiptStatus.CANCELLED.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot complete a cancelled receipt",
                )

            if not receipt.lines:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Receipt has no line items to complete",
                )

            assert_seller_access(scope, str(receipt.seller_id))
            assert_warehouse_access(scope, str(receipt.warehouse_id))

            # Duplicate protection check (unless override flag is set)
            if not receipt.is_duplicate_override:
                duplicate = await receiving_crud.find_existing_completed_receipt(
                    session,
                    warehouse_id=receipt.warehouse_id,
                    source_type=receipt.source_type,
                    source_reference=receipt.source_reference,
                )
                if duplicate is not None and duplicate.id != receipt.id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            "A completed receipt with this tracking/source reference "
                            "already exists"
                        ),
                    )

            now = datetime.now(UTC)
            receipt.status = ReceiptStatus.COMPLETED.value
            receipt.completed_by_user_id = actor_id
            receipt.completed_at = now
            receipt.updated_at = now

            # Generate inventory movements & update balance projections for each line
            for line in receipt.lines:
                # 1. Sellable -> AVAILABLE
                if line.sellable_quantity > Decimal("0.00"):
                    m_sellable = InventoryMovement(
                        seller_id=receipt.seller_id,
                        product_id=line.product_id,
                        warehouse_id=receipt.warehouse_id,
                        location_id=None,
                        inventory_state=InventoryState.AVAILABLE.value,
                        quantity_delta=line.sellable_quantity,
                        movement_type=InventoryMovementType.RECEIPT.value,
                        source_type="RECEIPT",
                        source_id=receipt.id,
                        source_line_id=line.id,
                        idempotency_key=f"RCV-{receipt.id}-{line.id}-AVAILABLE",
                        actor_user_id=actor_id,
                    )
                    await inventory_crud.apply_movement(session, m_sellable)

                # 2. Damaged -> DAMAGED
                if line.damaged_quantity > Decimal("0.00"):
                    m_damaged = InventoryMovement(
                        seller_id=receipt.seller_id,
                        product_id=line.product_id,
                        warehouse_id=receipt.warehouse_id,
                        location_id=None,
                        inventory_state=InventoryState.DAMAGED.value,
                        quantity_delta=line.damaged_quantity,
                        movement_type=InventoryMovementType.RECEIPT.value,
                        source_type="RECEIPT",
                        source_id=receipt.id,
                        source_line_id=line.id,
                        idempotency_key=f"RCV-{receipt.id}-{line.id}-DAMAGED",
                        actor_user_id=actor_id,
                    )
                    await inventory_crud.apply_movement(session, m_damaged)

                # 3. Quarantined -> QUARANTINED
                if line.quarantined_quantity > Decimal("0.00"):
                    m_quar = InventoryMovement(
                        seller_id=receipt.seller_id,
                        product_id=line.product_id,
                        warehouse_id=receipt.warehouse_id,
                        location_id=None,
                        inventory_state=InventoryState.QUARANTINED.value,
                        quantity_delta=line.quarantined_quantity,
                        movement_type=InventoryMovementType.RECEIPT.value,
                        source_type="RECEIPT",
                        source_id=receipt.id,
                        source_line_id=line.id,
                        idempotency_key=f"RCV-{receipt.id}-{line.id}-QUARANTINED",
                        actor_user_id=actor_id,
                    )
                    await inventory_crud.apply_movement(session, m_quar)

            event = ReceiptEvent(
                receipt_id=receipt.id,
                event_type="COMPLETED",
                actor_user_id=actor_id,
                details=complete_data.get(
                    "notes", "Receipt completed and inventory movements posted"
                ),
            )
            await receiving_crud.add_receipt_event(session, event)

            await audit_crud.create_audit_event(
                session,
                actor_user_id=actor_id,
                action_type=AuditActionType.RECEIPT_COMPLETED.value,
                source_record_type="receipts",
                source_record_id=receipt.id,
                metadata_json={"receipt_number": receipt.receipt_number},
            )
            await session.refresh(receipt)
            logger.info("Receipt completed successfully %s", receipt.id)
            return receipt

    async def override_duplicate(
        self,
        receipt_id: UUID,
        override_data: dict[str, Any],
        scope: dict[str, Any],
    ) -> Receipt:
        """
        Flag a receipt as a manager-approved duplicate override.

        Args:
            receipt_id: Receipt UUID.
            override_data: Validated override payload.
            scope: Authenticated requester scope.

        Returns:
            Receipt: Updated receipt model.

        Raises:
            HTTPException: If unauthorized or receipt missing.
        """
        require_roles(scope, {UserRole.ADMINISTRATOR, UserRole.WAREHOUSE_MANAGER})
        actor_id = UUID(str(scope["user_id"]))
        orig_id = UUID(str(override_data["original_receipt_id"]))
        reason = str(override_data["override_reason"]).strip()

        async with transaction_session() as session:
            receipt = await receiving_crud.get_receipt_by_id(session, receipt_id)
            if receipt is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found"
                )

            orig_receipt = await receiving_crud.get_receipt_by_id(session, orig_id)
            if orig_receipt is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Original receipt not found"
                )

            now = datetime.now(UTC)
            receipt.is_duplicate_override = True
            receipt.original_receipt_id = orig_id
            receipt.overridden_by_user_id = actor_id
            receipt.override_reason = reason
            receipt.updated_at = now

            event = ReceiptEvent(
                receipt_id=receipt.id,
                event_type="OVERRIDDEN",
                actor_user_id=actor_id,
                details=f"Duplicate override approved for original receipt {orig_id}: {reason}",
            )
            await receiving_crud.add_receipt_event(session, event)
            await audit_crud.create_audit_event(
                session,
                actor_user_id=actor_id,
                action_type=AuditActionType.RECEIPT_OVERRIDDEN.value,
                source_record_type="receipts",
                source_record_id=receipt.id,
                metadata_json={"original_receipt_id": str(orig_id), "reason": reason},
            )
            await session.refresh(receipt)
            logger.info("Duplicate receipt overridden successfully %s", receipt.id)
            return receipt

    async def cancel_receipt(self, receipt_id: UUID, scope: dict[str, Any]) -> Receipt:
        """
        Cancel an incomplete receiving receipt draft.

        Args:
            receipt_id: Receipt UUID.
            scope: Authenticated requester scope.

        Returns:
            Receipt: Cancelled receipt model.

        Raises:
            HTTPException: If receipt is already completed or cancelled.
        """
        require_roles(
            scope,
            {UserRole.ADMINISTRATOR, UserRole.WAREHOUSE_MANAGER, UserRole.RECEIVER},
        )
        actor_id = UUID(str(scope["user_id"]))

        async with transaction_session() as session:
            receipt = await receiving_crud.get_receipt_by_id(session, receipt_id)
            if receipt is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found"
                )

            if receipt.status == ReceiptStatus.COMPLETED.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot cancel a completed receipt",
                )

            now = datetime.now(UTC)
            receipt.status = ReceiptStatus.CANCELLED.value
            receipt.updated_at = now

            event = ReceiptEvent(
                receipt_id=receipt.id,
                event_type="CANCELLED",
                actor_user_id=actor_id,
                details="Receipt cancelled",
            )
            await receiving_crud.add_receipt_event(session, event)
            await audit_crud.create_audit_event(
                session,
                actor_user_id=actor_id,
                action_type=AuditActionType.RECEIPT_CANCELLED.value,
                source_record_type="receipts",
                source_record_id=receipt.id,
                metadata_json={"receipt_number": receipt.receipt_number},
            )
            await session.refresh(receipt)
            logger.info("Receipt cancelled successfully %s", receipt.id)
            return receipt


receiving_controller = ReceivingController()
