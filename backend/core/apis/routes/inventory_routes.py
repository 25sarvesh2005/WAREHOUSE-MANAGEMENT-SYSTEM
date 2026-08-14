"""
--------------------------------------------------------------------------------
File        : core/apis/routes/inventory_routes.py
Purpose     : Expose inventory balance, ledger, and reconciliation API endpoints.

Responsibilities:
    - Validate inventory request parameters and scope authorization.
    - Delegate inventory queries and reconciliation to InventoryController.

Flow:
    HTTP request -> Route validates -> InventoryController -> Response schema

Used By:
    - core/apis/api.py

Returns:
    APIRouter - Registered inventory API routes.

Raises:
    HTTPException: For route-level and controller errors.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from common.logger import get_logger
from common.warehouse_scope import get_warehouse_scope
from core.apis.schemas.requests.inventory_request import ReconciliationRequest
from core.apis.schemas.responses.inventory_response import (
    InventoryBalanceResponse,
    InventoryMovementResponse,
    ReconciliationResponse,
)
from core.controllers.inventory_controller import inventory_controller

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/inventory", tags=["Inventory"])


@router.get(
    "/balances",
    response_model=list[InventoryBalanceResponse],
    status_code=status.HTTP_200_OK,
    summary="List inventory balances",
)
async def list_balances(
    seller_id: UUID | None = Query(default=None),
    warehouse_id: UUID | None = Query(default=None),
    location_id: UUID | None = Query(default=None),
    product_id: UUID | None = Query(default=None),
    inventory_state: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    scope: dict = Depends(get_warehouse_scope),
) -> list[InventoryBalanceResponse]:
    """
    List operational inventory balances visible to the requester.

    Args:
        seller_id: Optional seller UUID filter.
        warehouse_id: Optional warehouse UUID filter.
        location_id: Optional location UUID filter.
        product_id: Optional product UUID filter.
        inventory_state: Optional inventory state filter.
        limit: Max rows.
        offset: Offset.
        scope: Authenticated warehouse scope dependency.

    Returns:
        list[InventoryBalanceResponse]: Matching balance rows.

    Raises:
        HTTPException: For access denial or server errors.
    """
    try:
        logger.info("Calling GET /v1/inventory/balances endpoint")
        response = await inventory_controller.list_balances(
            scope,
            seller_id=seller_id,
            warehouse_id=warehouse_id,
            location_id=location_id,
            product_id=product_id,
            inventory_state=inventory_state,
            limit=limit,
            offset=offset,
        )
        return [InventoryBalanceResponse.model_validate(b) for b in response]
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in GET /v1/inventory/balances endpoint: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.get(
    "/movements",
    response_model=list[InventoryMovementResponse],
    status_code=status.HTTP_200_OK,
    summary="List inventory movements",
)
async def list_movements(
    seller_id: UUID | None = Query(default=None),
    warehouse_id: UUID | None = Query(default=None),
    product_id: UUID | None = Query(default=None),
    movement_type: str | None = Query(default=None),
    source_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    scope: dict = Depends(get_warehouse_scope),
) -> list[InventoryMovementResponse]:
    """
    List append-only inventory movement ledger records visible to requester.

    Args:
        seller_id: Optional seller UUID filter.
        warehouse_id: Optional warehouse UUID filter.
        product_id: Optional product UUID filter.
        movement_type: Optional movement category filter.
        source_id: Optional source entity UUID filter.
        limit: Max rows.
        offset: Offset.
        scope: Authenticated warehouse scope dependency.

    Returns:
        list[InventoryMovementResponse]: Matching movement ledger records.

    Raises:
        HTTPException: For access denial or server errors.
    """
    try:
        logger.info("Calling GET /v1/inventory/movements endpoint")
        response = await inventory_controller.list_movements(
            scope,
            seller_id=seller_id,
            warehouse_id=warehouse_id,
            product_id=product_id,
            movement_type=movement_type,
            source_id=source_id,
            limit=limit,
            offset=offset,
        )
        return [InventoryMovementResponse.model_validate(m) for m in response]
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in GET /v1/inventory/movements endpoint: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.post(
    "/reconcile",
    response_model=ReconciliationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger inventory reconciliation",
)
async def reconcile(
    request: ReconciliationRequest,
    scope: dict = Depends(get_warehouse_scope),
) -> ReconciliationResponse:
    """
    Trigger an inventory reconciliation to compare movement ledger sums vs balances.

    Args:
        request: Reconciliation parameters.
        scope: Authenticated warehouse scope dependency.

    Returns:
        ReconciliationResponse: Created reconciliation record.

    Raises:
        HTTPException: For permission or server errors.
    """
    try:
        logger.info("Calling POST /v1/inventory/reconcile endpoint")
        response = await inventory_controller.reconcile(request.model_dump(mode="json"), scope)
        return ReconciliationResponse.model_validate(response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in POST /v1/inventory/reconcile endpoint: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error
