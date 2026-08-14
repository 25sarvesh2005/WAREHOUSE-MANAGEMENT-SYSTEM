"""
--------------------------------------------------------------------------------
File        : core/controllers/reporting_controller.py
Purpose     : Domain controller powering manager dashboards and exception queues.

Responsibilities:
    - Aggregate real-time warehouse metrics across inventory states and queues.
    - Expose active operational exception queues (short picks, transfer discrepancies,
      unidentified returns, duplicate overrides).
    - Provide reconciliation report data.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from common.logger import get_logger
from common.warehouse_scope import assert_warehouse_access, require_roles
from core.constants import UserRole
from core.cruds import (
    fulfillment_crud,
    inventory_crud,
    reporting_crud,
    return_crud,
    transfer_crud,
)
from core.database.database import transaction_session

logger = get_logger(__name__)


class ReportingController:
    """Controller aggregating manager metrics, exception queues, and reports."""

    async def get_manager_dashboard(
        self, scope: dict[str, Any], warehouse_id: UUID | None = None
    ) -> dict[str, Any]:
        """Fetch aggregate operational dashboard metrics."""
        require_roles(scope, {UserRole.ADMINISTRATOR, UserRole.WAREHOUSE_MANAGER})
        if warehouse_id:
            assert_warehouse_access(scope, str(warehouse_id))

        async with transaction_session() as session:
            balances_by_state = await reporting_crud.get_balance_totals_by_state(
                session,
                warehouse_id=warehouse_id,
            )
            open_receipts = await reporting_crud.count_receipts_by_statuses(
                session,
                statuses=["DRAFT", "IN_PROGRESS"],
                warehouse_id=warehouse_id,
            )
            pending_picks = await reporting_crud.count_pick_tasks_by_statuses(
                session,
                statuses=["ASSIGNED", "IN_PROGRESS"],
                warehouse_id=warehouse_id,
            )
            active_transfers = await reporting_crud.count_transfers_by_statuses(
                session,
                statuses=["APPROVED", "DISPATCHED", "PARTIALLY_RECEIVED"],
                warehouse_id=warehouse_id,
            )
            uninspected_returns = await reporting_crud.count_returns_by_statuses(
                session,
                statuses=["EXPECTED", "UNIDENTIFIED", "INSPECTION"],
                warehouse_id=warehouse_id,
            )

            return {
                "balances_by_state": balances_by_state,
                "open_receipts_count": open_receipts,
                "pending_pick_tasks_count": pending_picks,
                "active_transfers_count": active_transfers,
                "uninspected_returns_count": uninspected_returns,
            }

    async def get_manager_exceptions(
        self, scope: dict[str, Any], warehouse_id: UUID | None = None
    ) -> dict[str, Any]:
        """Fetch active operational exception queue items requiring manager attention."""
        require_roles(scope, {UserRole.ADMINISTRATOR, UserRole.WAREHOUSE_MANAGER})
        if warehouse_id:
            assert_warehouse_access(scope, str(warehouse_id))

        async with transaction_session() as session:
            # 1. Short pick exceptions
            short_picks = await fulfillment_crud.list_pick_tasks(
                session, warehouse_id=warehouse_id, status="SHORT_PICK_EXCEPTION", limit=50
            )

            # 2. Transfer discrepancies
            trf_discrepancies, _ = await transfer_crud.list_transfers(
                session, origin_warehouse_id=warehouse_id, status="DISCREPANCY_REVIEW", limit=50
            )

            # 3. Unidentified returns
            unidentified_returns, _ = await return_crud.list_returns(
                session, warehouse_id=warehouse_id, status="UNIDENTIFIED", limit=50
            )

            return {
                "short_pick_exceptions": [
                    {
                        "id": str(t.id),
                        "order_id": str(t.order_id),
                        "warehouse_id": str(t.warehouse_id),
                        "status": t.status,
                        "created_at": t.created_at.isoformat() if t.created_at else None,
                    }
                    for t in short_picks
                ],
                "transfer_discrepancies": [
                    {
                        "id": str(tr.id),
                        "transfer_number": tr.transfer_number,
                        "origin_warehouse_id": str(tr.origin_warehouse_id),
                        "destination_warehouse_id": str(tr.destination_warehouse_id),
                        "status": tr.status,
                    }
                    for tr in trf_discrepancies
                ],
                "unidentified_returns": [
                    {
                        "id": str(r.id),
                        "return_number": r.return_number,
                        "warehouse_id": str(r.warehouse_id),
                        "inbound_tracking_number": r.inbound_tracking_number,
                        "status": r.status,
                    }
                    for r in unidentified_returns
                ],
            }

    async def get_reconciliation_report(
        self, scope: dict[str, Any], warehouse_id: UUID | None = None
    ) -> dict[str, Any]:
        """Execute inventory balance vs movement ledger reconciliation audit report."""
        require_roles(scope, {UserRole.ADMINISTRATOR, UserRole.WAREHOUSE_MANAGER})
        if warehouse_id:
            assert_warehouse_access(scope, str(warehouse_id))

        async with transaction_session() as session:
            projections = await inventory_crud.list_balances(
                session, warehouse_id=warehouse_id, limit=1000
            )
            proj_map = {
                (
                    str(p.seller_id),
                    str(p.warehouse_id),
                    str(p.product_id),
                    str(p.location_id) if p.location_id else "NONE",
                    str(p.inventory_state),
                ): p.quantity
                for p in projections
            }

            rebuild_rows = await inventory_crud.rebuild_ledger_balances(
                session, warehouse_id=warehouse_id
            )
            rebuild_map = {
                (
                    r["seller_id"],
                    r["warehouse_id"],
                    r["product_id"],
                    r["location_id"] if r["location_id"] else "NONE",
                    r["inventory_state"],
                ): r["rebuilt_quantity"]
                for r in rebuild_rows
            }

            all_keys = set(proj_map.keys()).union(set(rebuild_map.keys()))
            matches = 0
            variances = []

            for key in all_keys:
                p_qty = proj_map.get(key, Decimal("0.00"))
                r_qty = rebuild_map.get(key, Decimal("0.00"))
                diff = p_qty - r_qty
                if diff == Decimal("0.00"):
                    matches += 1
                else:
                    variances.append({
                        "seller_id": key[0],
                        "warehouse_id": key[1],
                        "product_id": key[2],
                        "inventory_state": key[4],
                        "projected_quantity": float(p_qty),
                        "rebuilt_quantity": float(r_qty),
                        "variance": float(diff),
                    })

            return {
                "total_balance_keys": len(all_keys),
                "matches": matches,
                "variances_count": len(variances),
                "is_clean": len(variances) == 0,
                "variances": variances,
            }


reporting_controller = ReportingController()
