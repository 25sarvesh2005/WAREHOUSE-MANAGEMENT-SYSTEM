"""
--------------------------------------------------------------------------------
File        : core/apis/schemas/responses/receiving_response.py
Purpose     : Define receiving response schemas.

Responsibilities:
    - Serialize receipt headers, line items, and audit events.

Flow:
    Controller data -> Pydantic response schema -> FastAPI JSON

Used By:
    - core/apis/routes/receiving_routes.py

Returns:
    BaseModel instances - Serialized response payloads.

Raises:
    pydantic.ValidationError: When payload does not match contract.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReceiptLineResponse(BaseModel):
    """Public receiving receipt line item response."""

    id: UUID
    receipt_id: UUID
    product_id: UUID
    expected_quantity: Decimal
    sellable_quantity: Decimal
    damaged_quantity: Decimal
    quarantined_quantity: Decimal
    shortage_quantity: Decimal
    overage_quantity: Decimal
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReceiptEventResponse(BaseModel):
    """Public receiving event log response."""

    id: UUID
    receipt_id: UUID
    event_type: str
    actor_user_id: UUID | None
    details: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReceiptResponse(BaseModel):
    """Public receiving receipt header response."""

    id: UUID
    receipt_number: str
    seller_id: UUID
    warehouse_id: UUID
    source_type: str
    source_reference: str
    client_draft_id: str | None
    status: str
    expected_arrival_at: datetime | None
    actual_arrival_at: datetime | None
    started_by_user_id: UUID | None
    completed_by_user_id: UUID | None
    completed_at: datetime | None
    is_duplicate_override: bool
    original_receipt_id: UUID | None
    override_reason: str | None
    lines: list[ReceiptLineResponse] = []
    events: list[ReceiptEventResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
