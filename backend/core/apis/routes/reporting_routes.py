"""
FastAPI HTTP endpoints for operational dashboards, exception queues, and reports.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from common.warehouse_scope import get_warehouse_scope
from core.controllers.reporting_controller import reporting_controller

router = APIRouter(tags=["Manager Dashboard & Reports"])


@router.get(
    "/v1/manager/dashboard",
    status_code=status.HTTP_200_OK,
    summary="Get manager operational dashboard metrics",
)
async def get_manager_dashboard(
    scope: Annotated[dict, Depends(get_warehouse_scope)],
    warehouse_id: UUID | None = Query(default=None),
) -> dict[str, Any]:
    """Fetch aggregate warehouse operational metrics."""
    return await reporting_controller.get_manager_dashboard(scope, warehouse_id=warehouse_id)


@router.get(
    "/v1/manager/exceptions",
    status_code=status.HTTP_200_OK,
    summary="Get active operational exception queues",
)
async def get_manager_exceptions(
    scope: Annotated[dict, Depends(get_warehouse_scope)],
    warehouse_id: UUID | None = Query(default=None),
) -> dict[str, Any]:
    """Fetch operational exception items requiring manager intervention."""
    return await reporting_controller.get_manager_exceptions(scope, warehouse_id=warehouse_id)


@router.get(
    "/v1/reports/inventory-reconciliation",
    status_code=status.HTTP_200_OK,
    summary="Get inventory ledger vs balance reconciliation report",
)
async def get_reconciliation_report(
    scope: Annotated[dict, Depends(get_warehouse_scope)],
    warehouse_id: UUID | None = Query(default=None),
) -> dict[str, Any]:
    """Execute inventory balance projection vs movement ledger reconciliation audit."""
    return await reporting_controller.get_reconciliation_report(
        scope,
        warehouse_id=warehouse_id,
    )

