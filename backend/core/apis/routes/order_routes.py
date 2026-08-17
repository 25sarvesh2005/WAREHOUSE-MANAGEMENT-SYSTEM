"""
FastAPI HTTP endpoints for customer order ingestion and policy reservations.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from common.pagination import normalize_pagination
from common.warehouse_scope import get_warehouse_scope
from core.apis.schemas.requests.order_request import OrderCreateRequest, OrderReserveRequest
from core.apis.schemas.responses.order_response import OrderResponse
from core.controllers.order_controller import order_controller

router = APIRouter(prefix="/v1/orders", tags=["Orders & Reservations"])


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
    response = await order_controller.create_order(request.model_dump(), scope)
    return OrderResponse.model_validate(response)


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
    """Retrieve an order record with line items and reservations."""
    order = await order_controller.get_order_by_id(order_id, scope)
    return OrderResponse.model_validate(order)


@router.post(
    "/{order_id}/reserve",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute inventory reservation against order",
)
async def reserve_order(
    order_id: UUID,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
    request: OrderReserveRequest | None = None,
) -> OrderResponse:
    """Reserve available inventory for all lines in the order."""
    response = await order_controller.reserve_order(order_id, scope)
    return OrderResponse.model_validate(response)


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
    """Cancel an unfulfilled order and release active inventory reservations."""
    response = await order_controller.cancel_order(order_id, scope)
    return OrderResponse.model_validate(response)
