"""
FastAPI HTTP endpoints for receiving receipts and inbound workflow lifecycle.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from common.logger import get_logger
from common.warehouse_scope import get_warehouse_scope
from core.apis.schemas.requests.receiving_request import (
    DuplicateOverrideRequest,
    ReceiptCompleteRequest,
    ReceiptCreateRequest,
    ReceiptLineSaveRequest,
)
from core.apis.schemas.responses.receiving_response import ReceiptLineResponse, ReceiptResponse
from core.controllers.receiving_controller import receiving_controller

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/receipts", tags=["Receiving"])


@router.post(
    "",
    response_model=ReceiptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a receiving receipt draft",
)
async def create_receipt(
    request: ReceiptCreateRequest,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> ReceiptResponse:
    """Create a receiving receipt draft or sync an offline client draft.

    Validates supplier, warehouse scope, and duplicate ASN protection before persisting.
    """
    try:
        logger.info("Calling POST /v1/receipts endpoint")
        response = await receiving_controller.create_receipt(request.model_dump(mode="json"), scope)
        return ReceiptResponse.model_validate(response)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/receipts endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.get(
    "",
    response_model=list[ReceiptResponse],
    status_code=status.HTTP_200_OK,
    summary="List receiving receipts",
)
async def list_receipts(
    scope: Annotated[dict, Depends(get_warehouse_scope)],
    seller_id: UUID | None = Query(default=None),
    warehouse_id: UUID | None = Query(default=None),
    receipt_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[ReceiptResponse]:
    """List receiving receipts visible to the requester.

    Scopes results to the authenticated requester's accessible sellers and warehouses.
    """
    try:
        logger.info("Calling GET /v1/receipts endpoint")
        response = await receiving_controller.list_receipts(
            scope,
            seller_id=seller_id,
            warehouse_id=warehouse_id,
            receipt_status=receipt_status,
            limit=limit,
            offset=offset,
        )
        return [ReceiptResponse.model_validate(r) for r in response]
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in GET /v1/receipts endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.get(
    "/{receipt_id}",
    response_model=ReceiptResponse,
    status_code=status.HTTP_200_OK,
    summary="Get receiving receipt details",
)
async def get_receipt(
    receipt_id: UUID,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> ReceiptResponse:
    """Fetch a receiving receipt by ID with line items and event log.

    Enforces warehouse and seller scope access before returning the record.
    """
    try:
        logger.info(f"Calling GET /v1/receipts/{receipt_id} endpoint")
        response = await receiving_controller.get_receipt(receipt_id, scope)
        return ReceiptResponse.model_validate(response)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in GET /v1/receipts/{receipt_id} endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.post(
    "/{receipt_id}/lines",
    response_model=ReceiptLineResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add or update a line item on a receipt",
)
async def save_line_item(
    receipt_id: UUID,
    request: ReceiptLineSaveRequest,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> ReceiptLineResponse:
    """Add or update a product line item breakdown on an active receipt.

    Upserts a receipt line by product, accepting quantity and condition overrides.
    """
    try:
        logger.info(f"Calling POST /v1/receipts/{receipt_id}/lines endpoint")
        response = await receiving_controller.save_line_item(
            receipt_id, request.model_dump(mode="json"), scope
        )
        return ReceiptLineResponse.model_validate(response)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/receipts/{receipt_id}/lines endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.post(
    "/{receipt_id}/complete",
    response_model=ReceiptResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete a receiving receipt",
)
async def complete_receipt(
    receipt_id: UUID,
    request: ReceiptCompleteRequest,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> ReceiptResponse:
    """Atomically complete a receiving receipt and post inventory ledger movements.

    Validates all lines, posts RECEIVED movements, and transitions receipt to COMPLETED.
    """
    try:
        logger.info(f"Calling POST /v1/receipts/{receipt_id}/complete endpoint")
        response = await receiving_controller.complete_receipt(
            receipt_id, scope, request.model_dump(mode="json")
        )
        return ReceiptResponse.model_validate(response)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/receipts/{receipt_id}/complete endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.post(
    "/{receipt_id}/override-duplicate",
    response_model=ReceiptResponse,
    status_code=status.HTTP_200_OK,
    summary="Override duplicate receipt protection",
)
async def override_duplicate(
    receipt_id: UUID,
    request: DuplicateOverrideRequest,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> ReceiptResponse:
    """Flag a receipt as a manager-approved duplicate override.

    Requires WAREHOUSE_MANAGER role and a justification note before clearing the flag.
    """
    try:
        logger.info(f"Calling POST /v1/receipts/{receipt_id}/override-duplicate endpoint")
        response = await receiving_controller.override_duplicate(
            receipt_id, request.model_dump(mode="json"), scope
        )
        return ReceiptResponse.model_validate(response)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(
            f"Error in POST /v1/receipts/{receipt_id}/override-duplicate endpoint: {error}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )


@router.post(
    "/{receipt_id}/cancel",
    response_model=ReceiptResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel a receiving receipt draft",
)
async def cancel_receipt(
    receipt_id: UUID,
    scope: Annotated[dict, Depends(get_warehouse_scope)],
) -> ReceiptResponse:
    """Cancel an incomplete receiving receipt draft.

    Only DRAFT or FLAGGED receipts can be cancelled; COMPLETED receipts are immutable.
    """
    try:
        logger.info(f"Calling POST /v1/receipts/{receipt_id}/cancel endpoint")
        response = await receiving_controller.cancel_receipt(receipt_id, scope)
        return ReceiptResponse.model_validate(response)
    except HTTPException as http_error:
        raise http_error
    except Exception as error:
        logger.error(f"Error in POST /v1/receipts/{receipt_id}/cancel endpoint: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        )
