"""
FastAPI HTTP endpoints for read-only seller portal views.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from common.logger import get_logger
from common.warehouse_scope import get_warehouse_scope
from core.apis.schemas.responses.fulfillment_response import ShipmentResponse
from core.apis.schemas.responses.inventory_response import InventoryBalanceResponse
from core.apis.schemas.responses.order_response import OrderResponse
from core.apis.schemas.responses.receiving_response import ReceiptResponse
from core.apis.schemas.responses.return_response import ReturnResponse
from core.apis.schemas.responses.transfer_response import TransferResponse
from core.controllers.seller_portal_controller import seller_portal_controller

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/seller", tags=["Seller Portal"])


@router.get(
    "/inventory",
    response_model=list[InventoryBalanceResponse],
    status_code=status.HTTP_200_OK,
    summary="List seller inventory balances",
)
async def list_seller_inventory(
    scope: Annotated[dict, Depends(get_warehouse_scope)],
    seller_id: UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[InventoryBalanceResponse]:
    """List inventory balances scoped strictly to authenticated seller.

    Returns only AVAILABLE, RESERVED, and DAMAGED balances owned by the seller.
    """
    try:
        logger.info("Calling GET /v1/seller/inventory endpoint")
        balances = await seller_portal_controller.list_seller_inventory(
            scope,
            seller_id=seller_id,
            limit=limit,
            offset=offset,
        )
        return [InventoryBalanceResponse.model_validate(b) for b in balances]
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in GET /v1/seller/inventory endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.get(
    "/orders",
    response_model=list[OrderResponse],
    status_code=status.HTTP_200_OK,
    summary="List seller customer orders",
)
async def list_seller_orders(
    scope: Annotated[dict, Depends(get_warehouse_scope)],
    seller_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[OrderResponse]:
    """List customer orders scoped strictly to authenticated seller.

    Returns orders placed under the seller's tenancy across all warehouses.
    """
    try:
        logger.info("Calling GET /v1/seller/orders endpoint")
        orders = await seller_portal_controller.list_seller_orders(
            scope,
            seller_id=seller_id,
            limit=limit,
            offset=offset,
        )
        return [OrderResponse.model_validate(o) for o in orders]
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in GET /v1/seller/orders endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.get(
    "/receipts",
    response_model=list[ReceiptResponse],
    status_code=status.HTTP_200_OK,
    summary="List seller inbound receipts",
)
async def list_seller_receipts(
    scope: Annotated[dict, Depends(get_warehouse_scope)],
    seller_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[ReceiptResponse]:
    """List inbound receiving receipts scoped strictly to authenticated seller.

    Returns receipt headers with associated line items for the seller's stock.
    """
    try:
        logger.info("Calling GET /v1/seller/receipts endpoint")
        receipts = await seller_portal_controller.list_seller_receipts(
            scope,
            seller_id=seller_id,
            limit=limit,
            offset=offset,
        )
        return [ReceiptResponse.model_validate(r) for r in receipts]
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in GET /v1/seller/receipts endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.get(
    "/shipments",
    response_model=list[ShipmentResponse],
    status_code=status.HTTP_200_OK,
    summary="List seller outbound shipments",
)
async def list_seller_shipments(
    scope: Annotated[dict, Depends(get_warehouse_scope)],
    seller_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[ShipmentResponse]:
    """List outbound shipments scoped strictly to authenticated seller.

    Returns shipment records for orders belonging to the seller's tenancy.
    """
    try:
        logger.info("Calling GET /v1/seller/shipments endpoint")
        shipments = await seller_portal_controller.list_seller_shipments(
            scope,
            seller_id=seller_id,
            limit=limit,
            offset=offset,
        )
        return [ShipmentResponse.model_validate(s) for s in shipments]
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in GET /v1/seller/shipments endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.get(
    "/returns",
    response_model=list[ReturnResponse],
    status_code=status.HTTP_200_OK,
    summary="List seller customer returns",
)
async def list_seller_returns(
    scope: Annotated[dict, Depends(get_warehouse_scope)],
    seller_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[ReturnResponse]:
    """List customer returns scoped strictly to authenticated seller.

    Returns return records in all lifecycle states for the seller's products.
    """
    try:
        logger.info("Calling GET /v1/seller/returns endpoint")
        returns = await seller_portal_controller.list_seller_returns(
            scope,
            seller_id=seller_id,
            limit=limit,
            offset=offset,
        )
        return [ReturnResponse.model_validate(ret) for ret in returns]
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in GET /v1/seller/returns endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.get(
    "/transfers",
    response_model=list[TransferResponse],
    status_code=status.HTTP_200_OK,
    summary="List seller stock transfers",
)
async def list_seller_transfers(
    scope: Annotated[dict, Depends(get_warehouse_scope)],
    seller_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[TransferResponse]:
    """List stock transfers scoped strictly to authenticated seller.

    Returns all inter-warehouse transfers for stock owned by the seller.
    """
    try:
        logger.info("Calling GET /v1/seller/transfers endpoint")
        transfers = await seller_portal_controller.list_seller_transfers(
            scope,
            seller_id=seller_id,
            limit=limit,
            offset=offset,
        )
        return [TransferResponse.model_validate(t) for t in transfers]
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in GET /v1/seller/transfers endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )
