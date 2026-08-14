"""
--------------------------------------------------------------------------------
File        : core/apis/routes/seller_routes.py
Purpose     : Expose read-only seller portal API endpoints.

Responsibilities:
    - Authorize seller portal queries.
    - Delegate requests to SellerPortalController.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

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
    seller_id: UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    scope: dict = Depends(get_warehouse_scope),
) -> list[InventoryBalanceResponse]:
    """List inventory balances scoped strictly to authenticated seller."""
    try:
        logger.info("Calling GET /v1/seller/inventory endpoint")
        balances = await seller_portal_controller.list_seller_inventory(
            scope,
            seller_id=seller_id,
            limit=limit,
            offset=offset,
        )
        return [InventoryBalanceResponse.model_validate(b) for b in balances]
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in GET /v1/seller/inventory: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.get(
    "/orders",
    response_model=list[OrderResponse],
    status_code=status.HTTP_200_OK,
    summary="List seller customer orders",
)
async def list_seller_orders(
    seller_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    scope: dict = Depends(get_warehouse_scope),
) -> list[OrderResponse]:
    """List customer orders scoped strictly to authenticated seller."""
    try:
        logger.info("Calling GET /v1/seller/orders endpoint")
        orders = await seller_portal_controller.list_seller_orders(
            scope,
            seller_id=seller_id,
            limit=limit,
            offset=offset,
        )
        return [OrderResponse.model_validate(o) for o in orders]
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in GET /v1/seller/orders: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.get(
    "/receipts",
    response_model=list[ReceiptResponse],
    status_code=status.HTTP_200_OK,
    summary="List seller inbound receipts",
)
async def list_seller_receipts(
    seller_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    scope: dict = Depends(get_warehouse_scope),
) -> list[ReceiptResponse]:
    """List inbound receiving receipts scoped strictly to authenticated seller."""
    try:
        logger.info("Calling GET /v1/seller/receipts endpoint")
        receipts = await seller_portal_controller.list_seller_receipts(
            scope,
            seller_id=seller_id,
            limit=limit,
            offset=offset,
        )
        return [ReceiptResponse.model_validate(r) for r in receipts]
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in GET /v1/seller/receipts: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.get(
    "/shipments",
    response_model=list[ShipmentResponse],
    status_code=status.HTTP_200_OK,
    summary="List seller outbound shipments",
)
async def list_seller_shipments(
    seller_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    scope: dict = Depends(get_warehouse_scope),
) -> list[ShipmentResponse]:
    """List outbound shipments scoped strictly to authenticated seller."""
    try:
        logger.info("Calling GET /v1/seller/shipments endpoint")
        shipments = await seller_portal_controller.list_seller_shipments(
            scope,
            seller_id=seller_id,
            limit=limit,
            offset=offset,
        )
        return [ShipmentResponse.model_validate(s) for s in shipments]
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in GET /v1/seller/shipments: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.get(
    "/returns",
    response_model=list[ReturnResponse],
    status_code=status.HTTP_200_OK,
    summary="List seller customer returns",
)
async def list_seller_returns(
    seller_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    scope: dict = Depends(get_warehouse_scope),
) -> list[ReturnResponse]:
    """List customer returns scoped strictly to authenticated seller."""
    try:
        logger.info("Calling GET /v1/seller/returns endpoint")
        returns = await seller_portal_controller.list_seller_returns(
            scope,
            seller_id=seller_id,
            limit=limit,
            offset=offset,
        )
        return [ReturnResponse.model_validate(ret) for ret in returns]
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in GET /v1/seller/returns: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.get(
    "/transfers",
    response_model=list[TransferResponse],
    status_code=status.HTTP_200_OK,
    summary="List seller stock transfers",
)
async def list_seller_transfers(
    seller_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    scope: dict = Depends(get_warehouse_scope),
) -> list[TransferResponse]:
    """List stock transfers scoped strictly to authenticated seller."""
    try:
        logger.info("Calling GET /v1/seller/transfers endpoint")
        transfers = await seller_portal_controller.list_seller_transfers(
            scope,
            seller_id=seller_id,
            limit=limit,
            offset=offset,
        )
        return [TransferResponse.model_validate(t) for t in transfers]
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in GET /v1/seller/transfers: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error
