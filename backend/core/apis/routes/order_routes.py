"""
--------------------------------------------------------------------------------
File        : core/apis/routes/order_routes.py
Purpose     : FastAPI HTTP endpoints for customer order ingestion and policy reservations.

Responsibilities:
    - Expose order creation, lookup, policy reservation, and cancellation endpoints.
    - Validate authorization bearer tokens and requester scope.

Used By:
    - core/apis/api.py

Returns:
    JSON responses conforming to OrderResponse schemas.

Raises:
    fastapi.HTTPException: On validation or business rule failures.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from common.logger import get_logger
from common.pagination import normalize_pagination
from common.warehouse_scope import get_warehouse_scope
from core.apis.schemas.requests.order_request import OrderCreateRequest, OrderReserveRequest
from core.apis.schemas.responses.order_response import OrderResponse
from core.controllers.order_controller import OrderController

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/orders", tags=["Orders & Reservations"])
order_controller = OrderController()


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or import customer order",
)
async def create_order(
    request: OrderCreateRequest,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> OrderResponse:
    """Ingest a new customer order draft with line items."""
    logger.info("Calling POST /v1/orders endpoint")
    try:
        response = await order_controller.create_order(request.model_dump(), scope)
        return OrderResponse.model_validate(response)
    except Exception as exc:
        logger.error("Error in POST /v1/orders endpoint: %s", exc, exc_info=True)
        raise


@router.get(
    "",
    response_model=list[OrderResponse],
    status_code=status.HTTP_200_OK,
    summary="List customer orders",
)
async def list_orders(
    scope: Annotated[dict, Depends(get_warehouse_scope)],
    seller_id: UUID | None = Query(default=None, description="Filter by seller tenant UUID"),
    warehouse_id: UUID | None = Query(
        default=None, description="Filter by warehouse facility UUID"
    ),
    status_filter: str | None = Query(
        default=None, alias="status", description="Filter by order status"
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[OrderResponse]:
    """List customer orders matching filter parameters."""
    logger.info("Calling GET /v1/orders endpoint")
    try:
        norm_limit, norm_offset = normalize_pagination(limit, offset)
        orders = await order_controller.list_orders(
            scope,
            seller_id=seller_id,
            warehouse_id=warehouse_id,
            status=status_filter,
            limit=norm_limit,
            offset=norm_offset,
        )
        return [OrderResponse.model_validate(o) for o in orders]
    except Exception as exc:
        logger.error("Error in GET /v1/orders endpoint: %s", exc, exc_info=True)
        raise


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Get customer order by ID",
)
async def get_order(
    order_id: UUID,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> OrderResponse:
    """Retrieve an order by ID."""
    logger.info("Calling GET /v1/orders/%s endpoint", order_id)
    try:
        order = await order_controller.get_order(order_id, scope)
        return OrderResponse.model_validate(order)
    except Exception as exc:
        logger.error("Error in GET /v1/orders/%s endpoint: %s", order_id, exc, exc_info=True)
        raise


@router.post(
    "/{order_id}/reserve",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Reserve inventory for an order",
)
async def reserve_order(
    order_id: UUID,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
    request: OrderReserveRequest | None = None,
) -> OrderResponse:
    """Execute transactional inventory reservation for an order."""
    logger.info("Calling POST /v1/orders/%s/reserve endpoint", order_id)
    try:
        data = request.model_dump() if request else None
        order = await order_controller.reserve_order(order_id, scope, reserve_data=data)
        return OrderResponse.model_validate(order)
    except Exception as exc:
        logger.error(
            "Error in POST /v1/orders/%s/reserve endpoint: %s", order_id, exc, exc_info=True
        )
        raise


@router.post(
    "/{order_id}/cancel",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel order and release reservations",
)
async def cancel_order(
    order_id: UUID,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> OrderResponse:
    """Cancel an order and release active reservations."""
    logger.info("Calling POST /v1/orders/%s/cancel endpoint", order_id)
    try:
        order = await order_controller.cancel_order(order_id, scope)
        return OrderResponse.model_validate(order)
    except Exception as exc:
        logger.error(
            "Error in POST /v1/orders/%s/cancel endpoint: %s", order_id, exc, exc_info=True
        )
        raise
