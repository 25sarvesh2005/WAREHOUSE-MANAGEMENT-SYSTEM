"""
FastAPI HTTP endpoints for read-only seller portal views.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from common.warehouse_scope import get_warehouse_scope
from core.apis.schemas.responses.fulfillment_response import ShipmentResponse
from core.apis.schemas.responses.inventory_response import InventoryBalanceResponse
from core.apis.schemas.responses.order_response import OrderResponse
from core.apis.schemas.responses.receiving_response import ReceiptResponse
from core.apis.schemas.responses.return_response import ReturnResponse
from core.apis.schemas.responses.transfer_response import TransferResponse
from core.controllers.seller_portal_controller import seller_portal_controller

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
    """List inventory balances scoped strictly to authenticated seller."""
    balances = await seller_portal_controller.list_seller_inventory(
        scope,
        seller_id=seller_id,
        limit=limit,
        offset=offset,
    )
    return [InventoryBalanceResponse.model_validate(b) for b in balances]


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
    """List customer orders scoped strictly to authenticated seller."""
    orders = await seller_portal_controller.list_seller_orders(
        scope,
        seller_id=seller_id,
        limit=limit,
        offset=offset,
    )
    return [OrderResponse.model_validate(o) for o in orders]


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
    """List inbound receiving receipts scoped strictly to authenticated seller."""
    receipts = await seller_portal_controller.list_seller_receipts(
        scope,
        seller_id=seller_id,
        limit=limit,
        offset=offset,
    )
    return [ReceiptResponse.model_validate(r) for r in receipts]


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
    """List outbound shipments scoped strictly to authenticated seller."""
    shipments = await seller_portal_controller.list_seller_shipments(
        scope,
        seller_id=seller_id,
        limit=limit,
        offset=offset,
    )
    return [ShipmentResponse.model_validate(s) for s in shipments]


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
    """List customer returns scoped strictly to authenticated seller."""
    returns = await seller_portal_controller.list_seller_returns(
        scope,
        seller_id=seller_id,
        limit=limit,
        offset=offset,
    )
    return [ReturnResponse.model_validate(ret) for ret in returns]


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
    """List stock transfers scoped strictly to authenticated seller."""
    transfers = await seller_portal_controller.list_seller_transfers(
        scope,
        seller_id=seller_id,
        limit=limit,
        offset=offset,
    )
    return [TransferResponse.model_validate(t) for t in transfers]

