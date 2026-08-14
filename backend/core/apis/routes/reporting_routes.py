"""
--------------------------------------------------------------------------------
File        : core/apis/routes/reporting_routes.py
Purpose     : Expose manager operational dashboard, exception queue, and reconciliation APIs.

Responsibilities:
    - Route requests to ReportingController.
    - Authorize manager & administrator access.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Any
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
    warehouse_id: UUID | None = Query(default=None),
    scope: dict = Depends(get_warehouse_scope),
) -> dict[str, Any]:
    """Fetch aggregate warehouse operational metrics."""
    try:
        logger.info("Calling GET /v1/manager/dashboard endpoint")
        return await reporting_controller.get_manager_dashboard(scope, warehouse_id=warehouse_id)
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in GET /v1/manager/dashboard: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.get(
    "/v1/manager/exceptions",
    status_code=status.HTTP_200_OK,
    summary="Get active operational exception queues",
)
async def get_manager_exceptions(
    warehouse_id: UUID | None = Query(default=None),
    scope: dict = Depends(get_warehouse_scope),
) -> dict[str, Any]:
    """Fetch operational exception items requiring manager intervention."""
    try:
        logger.info("Calling GET /v1/manager/exceptions endpoint")
        return await reporting_controller.get_manager_exceptions(scope, warehouse_id=warehouse_id)
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in GET /v1/manager/exceptions: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.get(
    "/v1/reports/inventory-reconciliation",
    status_code=status.HTTP_200_OK,
    summary="Get inventory ledger vs balance reconciliation report",
)
async def get_reconciliation_report(
    warehouse_id: UUID | None = Query(default=None),
    scope: dict = Depends(get_warehouse_scope),
) -> dict[str, Any]:
    """Execute inventory balance projection vs movement ledger reconciliation audit."""
    try:
        logger.info("Calling GET /v1/reports/inventory-reconciliation endpoint")
        return await reporting_controller.get_reconciliation_report(
            scope,
            warehouse_id=warehouse_id,
        )
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in GET /v1/reports/inventory-reconciliation: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error
