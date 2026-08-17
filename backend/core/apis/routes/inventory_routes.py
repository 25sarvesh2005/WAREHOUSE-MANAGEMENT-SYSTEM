"""
FastAPI HTTP endpoints for inventory balance, ledger, and reconciliation.
"""

from __future__ import annotations

from typing import Annotated
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
    scope: Annotated[dict, Depends(get_warehouse_scope)],
    seller_id: UUID | None = Query(default=None),
    warehouse_id: UUID | None = Query(default=None),
    location_id: UUID | None = Query(default=None),
    product_id: UUID | None = Query(default=None),
    inventory_state: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[InventoryBalanceResponse]:
    """List operational inventory balances visible to the requester.

    Scopes results to the authenticated requester's accessible sellers and warehouses.
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
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in GET /v1/inventory/balances endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.get(
    "/movements",
    response_model=list[InventoryMovementResponse],
    status_code=status.HTTP_200_OK,
    summary="List inventory movements",
)
async def list_movements(
    scope: Annotated[dict, Depends(get_warehouse_scope)],
    seller_id: UUID | None = Query(default=None),
    warehouse_id: UUID | None = Query(default=None),
    product_id: UUID | None = Query(default=None),
    movement_type: str | None = Query(default=None),
    source_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[InventoryMovementResponse]:
    """List append-only inventory movement ledger records visible to requester.

    Returns immutable movement events ordered by occurrence for audit purposes.
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
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in GET /v1/inventory/movements endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.post(
    "/reconcile",
    response_model=ReconciliationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger inventory reconciliation",
)
async def reconcile(
    request: ReconciliationRequest,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> ReconciliationResponse:
    """Trigger an inventory reconciliation comparing movement ledger sums vs balances.

    Produces a discrepancy report and optionally corrects balance records.
    """
    try:
        logger.info("Calling POST /v1/inventory/reconcile endpoint")
        response = await inventory_controller.reconcile(request.model_dump(mode="json"), scope)
        return ReconciliationResponse.model_validate(response)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/inventory/reconcile endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )
