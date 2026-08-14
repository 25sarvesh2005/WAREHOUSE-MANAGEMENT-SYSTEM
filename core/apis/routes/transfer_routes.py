"""
Transfer Routes.

FastAPI endpoints for multi-warehouse transfers:
    - POST /v1/transfers: Create transfer draft/request.
    - GET /v1/transfers: List transfers.
    - GET /v1/transfers/{transfer_id}: Retrieve single transfer.
    - POST /v1/transfers/{transfer_id}/approve: Approve transfer.
    - POST /v1/transfers/{transfer_id}/dispatch: Dispatch transfer.
    - POST /v1/transfers/{transfer_id}/receive: Receive transfer.
    - POST /v1/transfers/{transfer_id}/resolve-discrepancy: Resolve discrepancy.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from common.logger import get_logger
from common.warehouse_scope import get_warehouse_scope
from core.apis.schemas.requests.transfer_request import (
    TransferCreateRequest,
    TransferReceiveRequest,
    TransferResolveDiscrepancyRequest,
)
from core.apis.schemas.responses.transfer_response import TransferListResponse, TransferResponse
from core.controllers.transfer_controller import TransferController

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/transfers", tags=["Transfers"])
transfer_controller = TransferController()


@router.post(
    "",
    response_model=TransferResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Multi-Warehouse Transfer Request",
)
async def create_transfer(
    request: TransferCreateRequest,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> TransferResponse:
    """Create a new transfer request between warehouses."""
    logger.info("Calling POST /v1/transfers endpoint")
    transfer = await transfer_controller.create_transfer(request.model_dump(), scope)
    return TransferResponse.model_validate(transfer)


@router.get(
    "",
    response_model=TransferListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Multi-Warehouse Transfers",
)
async def list_transfers(
    scope: Annotated[dict, Depends(get_warehouse_scope)],
    seller_id: UUID | None = Query(None, description="Filter by seller tenant UUID"),
    origin_warehouse_id: UUID | None = Query(None, description="Filter by origin warehouse UUID"),
    destination_warehouse_id: UUID | None = Query(
        None, description="Filter by destination warehouse UUID"
    ),
    status_val: str | None = Query(None, alias="status", description="Filter by transfer status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> TransferListResponse:
    """List transfers with optional query filters."""
    logger.info("Calling GET /v1/transfers endpoint")
    transfers, total = await transfer_controller.list_transfers(
        scope,
        seller_id=seller_id,
        origin_warehouse_id=origin_warehouse_id,
        destination_warehouse_id=destination_warehouse_id,
        status_val=status_val,
        limit=limit,
        offset=offset,
    )
    items = [TransferResponse.model_validate(t) for t in transfers]
    return TransferListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get(
    "/{transfer_id}",
    response_model=TransferResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Transfer Details",
)
async def get_transfer(
    transfer_id: UUID,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> TransferResponse:
    """Retrieve single transfer details."""
    logger.info("Calling GET /v1/transfers/%s endpoint", transfer_id)
    transfer = await transfer_controller.get_transfer(transfer_id, scope)
    return TransferResponse.model_validate(transfer)


@router.post(
    "/{transfer_id}/approve",
    response_model=TransferResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve Transfer Request",
)
async def approve_transfer(
    transfer_id: UUID,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> TransferResponse:
    """Approve a transfer request enforcing segregation of duties."""
    logger.info("Calling POST /v1/transfers/%s/approve endpoint", transfer_id)
    transfer = await transfer_controller.approve_transfer(transfer_id, scope)
    return TransferResponse.model_validate(transfer)


@router.post(
    "/{transfer_id}/dispatch",
    response_model=TransferResponse,
    status_code=status.HTTP_200_OK,
    summary="Dispatch Transfer (Move Stock to IN_TRANSIT)",
)
async def dispatch_transfer(
    transfer_id: UUID,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> TransferResponse:
    """Dispatch transfer, deducting origin stock and posting to IN_TRANSIT."""
    logger.info("Calling POST /v1/transfers/%s/dispatch endpoint", transfer_id)
    transfer = await transfer_controller.dispatch_transfer(transfer_id, scope)
    return TransferResponse.model_validate(transfer)


@router.post(
    "/{transfer_id}/receive",
    response_model=TransferResponse,
    status_code=status.HTTP_200_OK,
    summary="Receive Transfer at Destination Warehouse",
)
async def receive_transfer(
    transfer_id: UUID,
    request: TransferReceiveRequest,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> TransferResponse:
    """Receive transfer, converting IN_TRANSIT into AVAILABLE or DAMAGED stock."""
    logger.info("Calling POST /v1/transfers/%s/receive endpoint", transfer_id)
    transfer = await transfer_controller.receive_transfer(transfer_id, request.model_dump(), scope)
    return TransferResponse.model_validate(transfer)


@router.post(
    "/{transfer_id}/resolve-discrepancy",
    response_model=TransferResponse,
    status_code=status.HTTP_200_OK,
    summary="Resolve Transfer Discrepancy",
)
async def resolve_discrepancy(
    transfer_id: UUID,
    request: TransferResolveDiscrepancyRequest,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> TransferResponse:
    """Resolve variance discrepancies for a received transfer."""
    logger.info("Calling POST /v1/transfers/%s/resolve-discrepancy endpoint", transfer_id)
    transfer = await transfer_controller.resolve_discrepancy(
        transfer_id, request.model_dump(), scope
    )
    return TransferResponse.model_validate(transfer)
