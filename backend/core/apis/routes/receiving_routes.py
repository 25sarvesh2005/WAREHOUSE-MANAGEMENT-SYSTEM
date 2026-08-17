"""
FastAPI HTTP endpoints for receiving receipts and inbound workflow lifecycle.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from common.warehouse_scope import get_warehouse_scope
from core.apis.schemas.requests.receiving_request import (
    DuplicateOverrideRequest,
    ReceiptCompleteRequest,
    ReceiptCreateRequest,
    ReceiptLineSaveRequest,
)
from core.apis.schemas.responses.receiving_response import ReceiptLineResponse, ReceiptResponse
from core.controllers.receiving_controller import receiving_controller

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
    """Create a receiving receipt draft or sync an offline client draft."""
    response = await receiving_controller.create_receipt(request.model_dump(mode="json"), scope)
    return ReceiptResponse.model_validate(response)


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
    """List receiving receipts visible to the requester."""
    response = await receiving_controller.list_receipts(
        scope,
        seller_id=seller_id,
        warehouse_id=warehouse_id,
        receipt_status=receipt_status,
        limit=limit,
        offset=offset,
    )
    return [ReceiptResponse.model_validate(r) for r in response]


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
    """Fetch a receiving receipt by ID with line items and event log."""
    response = await receiving_controller.get_receipt(receipt_id, scope)
    return ReceiptResponse.model_validate(response)


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
    """Add or update a product line item breakdown on an active receipt."""
    response = await receiving_controller.save_line_item(
        receipt_id, request.model_dump(mode="json"), scope
    )
    return ReceiptLineResponse.model_validate(response)


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
    """Atomically complete a receiving receipt and post inventory ledger movements."""
    response = await receiving_controller.complete_receipt(
        receipt_id, scope, request.model_dump(mode="json")
    )
    return ReceiptResponse.model_validate(response)


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
    """Flag a receipt as a manager-approved duplicate override."""
    response = await receiving_controller.override_duplicate(
        receipt_id, request.model_dump(mode="json"), scope
    )
    return ReceiptResponse.model_validate(response)


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
    """Cancel an incomplete receiving receipt draft."""
    response = await receiving_controller.cancel_receipt(receipt_id, scope)
    return ReceiptResponse.model_validate(response)

