"""
FastAPI HTTP endpoints for operational dashboards, exception queues, and reports.
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from common.logger import get_logger
from common.warehouse_scope import get_warehouse_scope
from core.controllers.reporting_controller import reporting_controller

logger = get_logger(__name__)
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
    """Fetch aggregate warehouse operational metrics.

    Returns KPIs for receipts, orders, pick tasks, and inventory across the warehouse.
    """
    try:
        logger.info("Calling GET /v1/manager/dashboard endpoint")
        return await reporting_controller.get_manager_dashboard(scope, warehouse_id=warehouse_id)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in GET /v1/manager/dashboard endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.get(
    "/v1/manager/exceptions",
    status_code=status.HTTP_200_OK,
    summary="Get active operational exception queues",
)
async def get_manager_exceptions(
    scope: Annotated[dict, Depends(get_warehouse_scope)],
    warehouse_id: UUID | None = Query(default=None),
) -> dict[str, Any]:
    """Fetch operational exception items requiring manager intervention.

    Surfaces flagged receipts, short picks, and unresolved transfer discrepancies.
    """
    try:
        logger.info("Calling GET /v1/manager/exceptions endpoint")
        return await reporting_controller.get_manager_exceptions(scope, warehouse_id=warehouse_id)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in GET /v1/manager/exceptions endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.get(
    "/v1/reports/inventory-reconciliation",
    status_code=status.HTTP_200_OK,
    summary="Get inventory ledger vs balance reconciliation report",
)
async def get_reconciliation_report(
    scope: Annotated[dict, Depends(get_warehouse_scope)],
    warehouse_id: UUID | None = Query(default=None),
) -> dict[str, Any]:
    """Execute inventory balance projection vs movement ledger reconciliation audit.

    Compares summed ledger movements against current balance records to detect drift.
    """
    try:
        logger.info("Calling GET /v1/reports/inventory-reconciliation endpoint")
        return await reporting_controller.get_reconciliation_report(
            scope,
            warehouse_id=warehouse_id,
        )
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in GET /v1/reports/inventory-reconciliation endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )
