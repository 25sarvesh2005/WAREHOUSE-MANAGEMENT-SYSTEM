"""
FastAPI HTTP endpoints for customer order ingestion and policy reservations.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from common.logger import get_logger
from common.pagination import normalize_pagination
from common.warehouse_scope import get_warehouse_scope
from core.apis.schemas.requests.order_request import OrderCreateRequest, OrderReserveRequest
from core.apis.schemas.responses.order_response import OrderResponse
from core.controllers.order_controller import order_controller

logger = get_logger(__name__)
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
    """Ingest a new customer order draft with line items.

    Validates seller ownership, snapshots fulfilment policy, and creates order lines.
    """
    try:
        logger.info("Calling POST /v1/orders endpoint")
        response = await order_controller.create_order(request.model_dump(), scope)
        return OrderResponse.model_validate(response)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/orders endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


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
    """List customer orders matching filter parameters.

    Automatically scopes results to the requester's authorised sellers and warehouses.
    """
    try:
        logger.info("Calling GET /v1/orders endpoint")
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
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in GET /v1/orders endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


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
    """Retrieve an order record with line items and reservations.

    Enforces seller and warehouse scope access before returning the record.
    """
    try:
        logger.info(f"Calling GET /v1/orders/{order_id} endpoint")
        order = await order_controller.get_order(order_id, scope)
        return OrderResponse.model_validate(order)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in GET /v1/orders/{order_id} endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


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
    """Reserve available inventory for all lines in the order.

    Uses SELECT FOR UPDATE row locking to prevent double allocation.
    """
    try:
        logger.info(f"Calling POST /v1/orders/{order_id}/reserve endpoint")
        response = await order_controller.reserve_order(order_id, scope)
        return OrderResponse.model_validate(response)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/orders/{order_id}/reserve endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


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
    """Cancel an unfulfilled order and release active inventory reservations.

    Transitions all ACTIVE reservations to RELEASED and reverts stock to AVAILABLE.
    """
    try:
        logger.info(f"Calling POST /v1/orders/{order_id}/cancel endpoint")
        response = await order_controller.cancel_order(order_id, scope)
        return OrderResponse.model_validate(response)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/orders/{order_id}/cancel endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )
