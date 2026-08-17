"""
Return controller orchestrating customer/seller return workflows and quality disposition.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, status

from common.logger import get_logger
from common.warehouse_scope import assert_seller_access, assert_warehouse_access, require_roles
from core.constants import AuditActionType, InventoryMovementType, InventoryState, ReturnDispositionState, ReturnStatus, UserRole
from core.cruds import audit_crud, inventory_crud, return_crud
from core.database.database import transaction_session
from core.models.inventory_model import InventoryMovement
from core.models.return_model import Return

logger = get_logger(__name__)


class ReturnController:
    """Orchestrates customer / seller returns and inspection dispositions."""

    async def create_return(self, data: dict[str, Any], scope: dict[str, Any]) -> Return:
        """
        Create a new inbound return header (expected RMA or unidentified).

        Args:
            data: Payload containing seller_id, warehouse_id, order_id, rma_number,
                  inbound_tracking_number, notes, and lines.
            scope: Security context.

        Returns:
            Return: Created return entity.
        """
        seller_id = UUID(str(data["seller_id"]))
        wh_id = UUID(str(data["warehouse_id"]))

        assert_seller_access(scope, seller_id)
        assert_warehouse_access(scope, wh_id)

        actor_id = UUID(str(scope["user_id"]))
        return_number = f"RET-{datetime.now(UTC).strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"

        init_status = (
            ReturnStatus.UNIDENTIFIED.value
            if data.get("is_unidentified")
            else ReturnStatus.EXPECTED.value
        )

        order_id = UUID(str(data["order_id"])) if data.get("order_id") else None

        async with transaction_session() as session:
            ret = await return_crud.create_return(
                session,
                return_number=return_number,
                seller_id=seller_id,
                warehouse_id=wh_id,
                order_id=order_id,
                rma_number=data.get("rma_number"),
                inbound_tracking_number=data.get("inbound_tracking_number"),
                status=init_status,
                notes=data.get("notes"),
                lines_data=data.get("lines", []),
            )

            await audit_crud.create_audit_event(
                session,
                actor_user_id=actor_id,
                action_type=AuditActionType.RETURN_CREATED.value,
                source_record_type="returns",
                source_record_id=ret.id,
                metadata_json={"return_number": return_number, "status": ret.status},
            )

            reloaded = await return_crud.get_return_by_id(session, ret.id)
            logger.info("Return %s created successfully", ret.id)
            return reloaded or ret

    async def receive_return(
        self, return_id: UUID, data: dict[str, Any], scope: dict[str, Any]
    ) -> Return:
        """
        Register physical receipt of return parcel into RETURN_INSPECTION stock.

        Args:
            return_id: Return UUID.
            data: Payload with received line quantities.
            scope: Security context.

        Returns:
            Return: Return entity updated to INSPECTION status.

        Raises:
            HTTPException: 404 if missing, 409 if invalid state.
        """
        actor_id = UUID(str(scope["user_id"]))

        async with transaction_session() as session:
            ret = await return_crud.get_return_by_id(session, return_id)
            if ret is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Return {return_id} not found.",
                )

            assert_warehouse_access(scope, ret.warehouse_id)

            if ret.status not in (ReturnStatus.EXPECTED.value, ReturnStatus.UNIDENTIFIED.value):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot receive return in {ret.status} status.",
                )

            now = datetime.now(UTC)
            line_updates = {str(item["line_id"]): item for item in data.get("lines", [])}

            for line in ret.lines:
                update_item = line_updates.get(str(line.id), {})
                rcv_qty = Decimal(str(update_item.get("received_quantity", line.expected_quantity)))
                line.received_quantity = rcv_qty

                if rcv_qty > Decimal("0.00") and line.product_id is not None:
                    # Place stock strictly into RETURN_INSPECTION state (never AVAILABLE)
                    m_ins = InventoryMovement(
                        seller_id=ret.seller_id,
                        product_id=line.product_id,
                        warehouse_id=ret.warehouse_id,
                        inventory_state=InventoryState.RETURN_INSPECTION.value,
                        quantity_delta=rcv_qty,
                        movement_type=InventoryMovementType.RETURN_INSPECTION.value,
                        source_type="returns",
                        source_id=ret.id,
                        source_line_id=line.id,
                        idempotency_key=f"ret-rcv-{ret.id}-{line.id}",
                        actor_user_id=actor_id,
                        occurred_at=now,
                    )
                    await inventory_crud.apply_movement(session, m_ins)

            ret.status = ReturnStatus.INSPECTION.value
            ret.received_at = now

            await audit_crud.create_audit_event(
                session,
                actor_user_id=actor_id,
                action_type=AuditActionType.RETURN_RECEIVED.value,
                source_record_type="returns",
                source_record_id=ret.id,
                metadata_json={"status": ret.status},
            )

            reloaded = await return_crud.get_return_by_id(session, ret.id)
            logger.info("Return %s received for inspection", ret.id)
            return reloaded or ret

    async def inspect_and_dispose_return(
        self, return_id: UUID, data: dict[str, Any], scope: dict[str, Any]
    ) -> Return:
        """
        Record inspection results and post inventory dispositions out of RETURN_INSPECTION.

        Args:
            return_id: Return UUID.
            data: Disposition list payload (return_line_id, disposition_state, quantity).
            scope: Security context.

        Returns:
            Return: Completed return entity.

        Raises:
            HTTPException: 404 if missing, 409 if status is not INSPECTION.
        """
        require_roles(
            scope,
            [
                UserRole.ADMINISTRATOR,
                UserRole.WAREHOUSE_MANAGER,
                UserRole.RECEIVER,
            ],
        )
        actor_id = UUID(str(scope["user_id"]))

        async with transaction_session() as session:
            ret = await return_crud.get_return_by_id(session, return_id)
            if ret is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Return {return_id} not found.",
                )

            assert_warehouse_access(scope, ret.warehouse_id)

            if ret.status != ReturnStatus.INSPECTION.value:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot inspect return in {ret.status} status; must be in INSPECTION.",
                )

            now = datetime.now(UTC)
            dispositions_payload = data.get("dispositions", [])

            for disp_item in dispositions_payload:
                line_id = UUID(str(disp_item["return_line_id"]))
                disp_state = str(disp_item["disposition_state"])
                qty = Decimal(str(disp_item["quantity"]))
                dest_loc_id = UUID(str(disp_item["destination_location_id"])) if disp_item.get("destination_location_id") else None

                # Find line
                target_line = next((l for l in ret.lines if l.id == line_id), None)
                if target_line is None or target_line.product_id is None:
                    continue

                # Create disposition audit row
                await return_crud.create_return_disposition(
                    session,
                    return_line_id=line_id,
                    disposition_state=disp_state,
                    quantity=qty,
                    destination_location_id=dest_loc_id,
                    notes=disp_item.get("notes"),
                )

                # Map disposition state string to operational InventoryState
                target_inv_state = (
                    InventoryState.AVAILABLE.value
                    if disp_state in (ReturnDispositionState.AVAILABLE.value, ReturnDispositionState.RESTOCKED.value)
                    else (
                        InventoryState.DAMAGED.value
                        if disp_state == ReturnDispositionState.DAMAGED.value
                        else InventoryState.QUARANTINED.value
                    )
                )

                # Transfer stock from RETURN_INSPECTION to target disposition state
                await inventory_crud.apply_state_transfer(
                    session,
                    seller_id=ret.seller_id,
                    product_id=target_line.product_id,
                    from_warehouse_id=ret.warehouse_id,
                    to_location_id=dest_loc_id,
                    from_state=InventoryState.RETURN_INSPECTION.value,
                    to_state=target_inv_state,
                    quantity=qty,
                    movement_type=InventoryMovementType.RETURN_DISPOSITION.value,
                    source_type="returns",
                    source_id=ret.id,
                    source_line_id=line_id,
                    idempotency_prefix=f"ret-disp-{ret.id}-{line_id}-{str(uuid4())[:8]}",
                    actor_user_id=actor_id,
                )

            ret.status = ReturnStatus.COMPLETED.value
            ret.completed_at = now

            await audit_crud.create_audit_event(
                session,
                actor_user_id=actor_id,
                action_type=AuditActionType.RETURN_COMPLETED.value,
                source_record_type="returns",
                source_record_id=ret.id,
                metadata_json={"status": ret.status},
            )

            reloaded = await return_crud.get_return_by_id(session, ret.id)
            logger.info("Return %s completed with dispositions", ret.id)
            return reloaded or ret

    async def get_return(self, return_id: UUID, scope: dict[str, Any]) -> Return:
        """Retrieve single return details."""
        async with transaction_session() as session:
            ret = await return_crud.get_return_by_id(session, return_id)
            if ret is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Return {return_id} not found.",
                )
            assert_seller_access(scope, ret.seller_id)
            return ret

    async def list_returns(
        self,
        scope: dict[str, Any],
        *,
        seller_id: UUID | None = None,
        warehouse_id: UUID | None = None,
        status_val: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Return], int]:
        """List returns with tenant security filtering."""
        async with transaction_session() as session:
            returns, total = await return_crud.list_returns(
                session,
                seller_id=seller_id,
                warehouse_id=warehouse_id,
                status=status_val,
                limit=limit,
                offset=offset,
            )
            return list(returns), total


return_controller = ReturnController()
