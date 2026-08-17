"""
Inventory Controller.

Orchestrates inventory balances, movement ledger queries, and reconciliations.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Sequence
from uuid import UUID

from fastapi import HTTPException, status

from common.logger import get_logger
from common.pagination import normalize_pagination
from common.warehouse_scope import assert_seller_access, assert_warehouse_access, require_roles
from core.constants import AuditActionType, UserRole
from core.cruds import audit_crud, identity_crud, inventory_crud
from core.database.database import transaction_session
from core.models.inventory_model import (
    InventoryBalance,
    InventoryMovement,
    InventoryReconciliation,
)

logger = get_logger(__name__)


class InventoryController:
    """Controller for inventory balance, ledger, and reconciliation workflows."""

    async def list_balances(
        self,
        scope: dict[str, Any],
        *,
        seller_id: UUID | None,
        warehouse_id: UUID | None,
        location_id: UUID | None,
        product_id: UUID | None,
        inventory_state: str | None,
        limit: int,
        offset: int,
    ) -> Sequence[InventoryBalance]:
        """
        Query operational inventory balances scoped to requester permissions.

        Args:
            scope: Authenticated requester scope.
            seller_id: Optional seller filter.
            warehouse_id: Optional warehouse filter.
            location_id: Optional location filter.
            product_id: Optional product filter.
            inventory_state: Optional inventory state filter.
            limit: Requested limit.
            offset: Requested offset.

        Returns:
            Sequence[InventoryBalance]: Matching balance records.

        Raises:
            HTTPException: If scope access is denied.
        """
        logger.info("Executing InventoryController.list_balances")
        normalized_limit, normalized_offset = normalize_pagination(limit, offset)

        if seller_id is not None:
            assert_seller_access(scope, str(seller_id))
        elif scope.get("role") != UserRole.ADMINISTRATOR.value and scope.get("seller_ids"):
            seller_id = UUID(str(scope["seller_ids"][0]))

        if warehouse_id is not None:
            assert_warehouse_access(scope, str(warehouse_id))
        elif scope.get("role") != UserRole.ADMINISTRATOR.value and scope.get("warehouse_ids"):
            warehouse_id = UUID(str(scope["warehouse_ids"][0]))

        async with transaction_session() as session:
            return await inventory_crud.list_balances(
                session,
                seller_id=seller_id,
                warehouse_id=warehouse_id,
                location_id=location_id,
                product_id=product_id,
                inventory_state=inventory_state,
                limit=normalized_limit,
                offset=normalized_offset,
            )

    async def list_movements(
        self,
        scope: dict[str, Any],
        *,
        seller_id: UUID | None,
        warehouse_id: UUID | None,
        product_id: UUID | None,
        movement_type: str | None,
        source_id: UUID | None,
        limit: int,
        offset: int,
    ) -> Sequence[InventoryMovement]:
        """
        Query append-only inventory movement ledger scoped to requester permissions.

        Args:
            scope: Authenticated requester scope.
            seller_id: Optional seller filter.
            warehouse_id: Optional warehouse filter.
            product_id: Optional product filter.
            movement_type: Optional movement type filter.
            source_id: Optional source entity UUID filter.
            limit: Requested limit.
            offset: Requested offset.

        Returns:
            Sequence[InventoryMovement]: Matching movement ledger records.

        Raises:
            HTTPException: If scope access is denied.
        """
        logger.info("Executing InventoryController.list_movements")
        normalized_limit, normalized_offset = normalize_pagination(limit, offset)

        if seller_id is not None:
            assert_seller_access(scope, str(seller_id))
        elif scope.get("role") != UserRole.ADMINISTRATOR.value and scope.get("seller_ids"):
            seller_id = UUID(str(scope["seller_ids"][0]))

        if warehouse_id is not None:
            assert_warehouse_access(scope, str(warehouse_id))
        elif scope.get("role") != UserRole.ADMINISTRATOR.value and scope.get("warehouse_ids"):
            warehouse_id = UUID(str(scope["warehouse_ids"][0]))

        async with transaction_session() as session:
            return await inventory_crud.list_movements(
                session,
                seller_id=seller_id,
                warehouse_id=warehouse_id,
                product_id=product_id,
                movement_type=movement_type,
                source_id=source_id,
                limit=normalized_limit,
                offset=normalized_offset,
            )

    async def reconcile(
        self,
        reconciliation_data: dict[str, Any],
        scope: dict[str, Any],
    ) -> InventoryReconciliation:
        """
        Trigger an inventory reconciliation to compare ledger movements vs operational balances.

        Args:
            reconciliation_data: Validated reconciliation request parameters.
            scope: Authenticated requester scope.

        Returns:
            InventoryReconciliation: Created reconciliation snapshot.

        Raises:
            HTTPException: If unauthorized or target entities do not exist.
        """
        logger.info("Executing InventoryController.reconcile")
        require_roles(scope, {UserRole.ADMINISTRATOR, UserRole.WAREHOUSE_MANAGER})
        actor_id = UUID(str(scope["user_id"]))
        warehouse_id = UUID(str(reconciliation_data["warehouse_id"]))
        assert_warehouse_access(scope, str(warehouse_id))

        seller_id_raw = reconciliation_data.get("seller_id")
        seller_id = UUID(str(seller_id_raw)) if seller_id_raw is not None else None

        async with transaction_session() as session:
            warehouse = await identity_crud.get_warehouse_by_id(session, warehouse_id)
            if warehouse is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Warehouse not found"
                )

            ledger_sum = await inventory_crud.compute_ledger_sums(
                session, warehouse_id=warehouse_id, seller_id=seller_id
            )
            balance_sum = await inventory_crud.compute_balance_sums(
                session, warehouse_id=warehouse_id, seller_id=seller_id
            )
            variance = balance_sum - ledger_sum

            reconciliation = InventoryReconciliation(
                warehouse_id=warehouse_id,
                seller_id=seller_id,
                status="MATCH" if variance == Decimal("0.00") else "VARIANCE_DETECTED",
                total_ledger_quantity=ledger_sum,
                total_balance_quantity=balance_sum,
                variance_quantity=variance,
                investigated_by_user_id=actor_id,
                notes=reconciliation_data.get("notes"),
            )
            await inventory_crud.create_reconciliation(session, reconciliation)
            await audit_crud.create_audit_event(
                session,
                actor_user_id=actor_id,
                action_type=AuditActionType.INVENTORY_RECONCILED.value,
                source_record_type="inventory_reconciliations",
                source_record_id=reconciliation.id,
                metadata_json={
                    "warehouse_id": str(warehouse_id),
                    "variance": str(variance),
                },
            )
            logger.info("Reconciliation executed variance=%s", variance)
            return reconciliation


inventory_controller = InventoryController()
