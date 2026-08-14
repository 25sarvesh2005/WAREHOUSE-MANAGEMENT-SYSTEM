"""
--------------------------------------------------------------------------------
File        : core/apis/routes/receiving_routes.py
Purpose     : Expose receiving receipt and workflow API endpoints.

Responsibilities:
    - Validate receiving payload schemas and scope dependencies.
    - Delegate receipt operations to ReceivingController.

Flow:
    HTTP request -> Route validates -> ReceivingController -> Response schema

Used By:
    - core/apis/api.py

Returns:
    APIRouter - Registered receiving API routes.

Raises:
    HTTPException: For route-level and controller errors.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

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
    scope: dict = Depends(get_warehouse_scope),
) -> ReceiptResponse:
    """
    Create a receiving receipt draft or sync an offline client draft.

    Args:
        request: Receipt creation request payload.
        scope: Authenticated warehouse scope dependency.

    Returns:
        ReceiptResponse: Created receipt draft record.

    Raises:
        HTTPException: For duplicate, permission, or server errors.
    """
    try:
        logger.info("Calling POST /v1/receipts endpoint")
        response = await receiving_controller.create_receipt(
            request.model_dump(mode="json"), scope
        )
        return ReceiptResponse.model_validate(response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in POST /v1/receipts endpoint: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.get(
    "",
    response_model=list[ReceiptResponse],
    status_code=status.HTTP_200_OK,
    summary="List receiving receipts",
)
async def list_receipts(
    seller_id: UUID | None = Query(default=None),
    warehouse_id: UUID | None = Query(default=None),
    receipt_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    scope: dict = Depends(get_warehouse_scope),
) -> list[ReceiptResponse]:
    """
    List receiving receipts visible to the requester.

    Args:
        seller_id: Optional seller filter.
        warehouse_id: Optional warehouse filter.
        receipt_status: Optional status filter.
        limit: Max rows.
        offset: Offset.
        scope: Authenticated warehouse scope dependency.

    Returns:
        list[ReceiptResponse]: Matching receipt records.

    Raises:
        HTTPException: For access denial or server errors.
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
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in GET /v1/receipts endpoint: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.get(
    "/{receipt_id}",
    response_model=ReceiptResponse,
    status_code=status.HTTP_200_OK,
    summary="Get receiving receipt details",
)
async def get_receipt(
    receipt_id: UUID,
    scope: dict = Depends(get_warehouse_scope),
) -> ReceiptResponse:
    """
    Fetch a receiving receipt by ID with line items and event log.

    Args:
        receipt_id: Receipt UUID.
        scope: Authenticated warehouse scope dependency.

    Returns:
        ReceiptResponse: Detailed receipt record.

    Raises:
        HTTPException: For not-found, permission, or server errors.
    """
    try:
        logger.info("Calling GET /v1/receipts/%s endpoint", receipt_id)
        response = await receiving_controller.get_receipt(receipt_id, scope)
        return ReceiptResponse.model_validate(response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in GET /v1/receipts/%s endpoint: %s", receipt_id, error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.post(
    "/{receipt_id}/lines",
    response_model=ReceiptLineResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add or update a line item on a receipt",
)
async def save_line_item(
    receipt_id: UUID,
    request: ReceiptLineSaveRequest,
    scope: dict = Depends(get_warehouse_scope),
) -> ReceiptLineResponse:
    """
    Add or update a product line item breakdown on an active receipt.

    Args:
        receipt_id: Receipt UUID.
        request: Line item save payload.
        scope: Authenticated warehouse scope dependency.

    Returns:
        ReceiptLineResponse: Saved line item record.

    Raises:
        HTTPException: For invalid state, not-found, or server errors.
    """
    try:
        logger.info("Calling POST /v1/receipts/%s/lines endpoint", receipt_id)
        response = await receiving_controller.save_line_item(
            receipt_id, request.model_dump(mode="json"), scope
        )
        return ReceiptLineResponse.model_validate(response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error(
            "Error in POST /v1/receipts/%s/lines endpoint: %s", receipt_id, error, exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.post(
    "/{receipt_id}/complete",
    response_model=ReceiptResponse,
    status_code=status.HTTP_200_OK,
    summary="Complete a receiving receipt",
)
async def complete_receipt(
    receipt_id: UUID,
    request: ReceiptCompleteRequest,
    scope: dict = Depends(get_warehouse_scope),
) -> ReceiptResponse:
    """
    Atomically complete a receiving receipt and post inventory ledger movements.

    Args:
        receipt_id: Receipt UUID.
        request: Completion payload.
        scope: Authenticated warehouse scope dependency.

    Returns:
        ReceiptResponse: Completed receipt record.

    Raises:
        HTTPException: For invalid state, empty lines, duplicate, or server errors.
    """
    try:
        logger.info("Calling POST /v1/receipts/%s/complete endpoint", receipt_id)
        response = await receiving_controller.complete_receipt(
            receipt_id, scope, request.model_dump(mode="json")
        )
        return ReceiptResponse.model_validate(response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error(
            "Error in POST /v1/receipts/%s/complete endpoint: %s", receipt_id, error, exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.post(
    "/{receipt_id}/override-duplicate",
    response_model=ReceiptResponse,
    status_code=status.HTTP_200_OK,
    summary="Override duplicate receipt protection",
)
async def override_duplicate(
    receipt_id: UUID,
    request: DuplicateOverrideRequest,
    scope: dict = Depends(get_warehouse_scope),
) -> ReceiptResponse:
    """
    Flag a receipt as a manager-approved duplicate override.

    Args:
        receipt_id: Receipt UUID.
        request: Duplicate override payload.
        scope: Authenticated warehouse scope dependency.

    Returns:
        ReceiptResponse: Updated receipt record.

    Raises:
        HTTPException: For permission, not-found, or server errors.
    """
    try:
        logger.info("Calling POST /v1/receipts/%s/override-duplicate endpoint", receipt_id)
        response = await receiving_controller.override_duplicate(
            receipt_id, request.model_dump(mode="json"), scope
        )
        return ReceiptResponse.model_validate(response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error(
            "Error in POST /v1/receipts/%s/override-duplicate endpoint: %s",
            receipt_id,
            error,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.post(
    "/{receipt_id}/cancel",
    response_model=ReceiptResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel a receiving receipt draft",
)
async def cancel_receipt(
    receipt_id: UUID,
    scope: dict = Depends(get_warehouse_scope),
) -> ReceiptResponse:
    """
    Cancel an incomplete receiving receipt draft.

    Args:
        receipt_id: Receipt UUID.
        scope: Authenticated warehouse scope dependency.

    Returns:
        ReceiptResponse: Cancelled receipt record.

    Raises:
        HTTPException: For invalid state, permission, or server errors.
    """
    try:
        logger.info("Calling POST /v1/receipts/%s/cancel endpoint", receipt_id)
        response = await receiving_controller.cancel_receipt(receipt_id, scope)
        return ReceiptResponse.model_validate(response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error(
            "Error in POST /v1/receipts/%s/cancel endpoint: %s", receipt_id, error, exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal Server Error") from error
