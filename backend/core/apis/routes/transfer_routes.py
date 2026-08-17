"""
FastAPI HTTP endpoints for multi-warehouse transfers.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from common.logger import get_logger
from common.warehouse_scope import get_warehouse_scope
from core.apis.schemas.requests.transfer_request import (
    TransferCreateRequest,
    TransferReceiveRequest,
    TransferResolveDiscrepancyRequest,
)
from core.apis.schemas.responses.transfer_response import TransferListResponse, TransferResponse
from core.controllers.transfer_controller import transfer_controller

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/transfers", tags=["Transfers"])


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
    """Create a new transfer request between warehouses.

    Validates origin and destination warehouse access before creating the transfer record.
    """
    try:
        logger.info("Calling POST /v1/transfers endpoint")
        transfer = await transfer_controller.create_transfer(request.model_dump(), scope)
        return TransferResponse.model_validate(transfer)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/transfers endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


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
    """List transfers with optional query filters.

    Scopes results to accessible sellers and warehouses for the authenticated requester.
    """
    try:
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
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in GET /v1/transfers endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


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
    """Retrieve single transfer details.

    Enforces origin and destination warehouse scope access before returning the record.
    """
    try:
        logger.info("Calling GET /v1/transfers/%s endpoint", transfer_id)
        transfer = await transfer_controller.get_transfer(transfer_id, scope)
        return TransferResponse.model_validate(transfer)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in GET /v1/transfers/{transfer_id} endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


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
    """Approve a transfer request enforcing segregation of duties.

    Requires a different approver from the transfer creator per four-eyes policy.
    """
    try:
        logger.info("Calling POST /v1/transfers/%s/approve endpoint", transfer_id)
        transfer = await transfer_controller.approve_transfer(transfer_id, scope)
        return TransferResponse.model_validate(transfer)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/transfers/{transfer_id}/approve endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


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
    """Dispatch transfer, deducting origin stock and posting to IN_TRANSIT.

    Moves stock from AVAILABLE at origin to IN_TRANSIT and transitions status to DISPATCHED.
    """
    try:
        logger.info("Calling POST /v1/transfers/%s/dispatch endpoint", transfer_id)
        transfer = await transfer_controller.dispatch_transfer(transfer_id, scope)
        return TransferResponse.model_validate(transfer)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/transfers/{transfer_id}/dispatch endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


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
    """Receive transfer, converting IN_TRANSIT into AVAILABLE or DAMAGED stock.

    Posts RECEIVED movements at the destination and flags any quantity discrepancies.
    """
    try:
        logger.info("Calling POST /v1/transfers/%s/receive endpoint", transfer_id)
        transfer = await transfer_controller.receive_transfer(
            transfer_id, request.model_dump(), scope
        )
        return TransferResponse.model_validate(transfer)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/transfers/{transfer_id}/receive endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


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
    """Resolve variance discrepancies for a received transfer.

    Requires WAREHOUSE_MANAGER role and writes off or adjusts the discrepant quantities.
    """
    try:
        logger.info("Calling POST /v1/transfers/%s/resolve-discrepancy endpoint", transfer_id)
        transfer = await transfer_controller.resolve_discrepancy(
            transfer_id, request.model_dump(), scope
        )
        return TransferResponse.model_validate(transfer)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(
            f"Error in POST /v1/transfers/{transfer_id}/resolve-discrepancy endpoint: {error}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )
