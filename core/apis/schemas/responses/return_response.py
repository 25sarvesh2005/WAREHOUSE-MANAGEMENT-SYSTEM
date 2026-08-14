"""
Return Response Schemas.

Pydantic schemas serializing return response models.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReturnDispositionResponse(BaseModel):
    """Inspection outcome log item."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    return_line_id: UUID
    disposition_state: str
    quantity: Decimal
    destination_location_id: UUID | None = None
    notes: str | None = None
    created_at: datetime


class ReturnLineResponse(BaseModel):
    """Return line item representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    return_id: UUID
    product_id: UUID | None = None
    expected_quantity: Decimal
    received_quantity: Decimal
    reason_code: str | None = None
    inspection_notes: str | None = None
    dispositions: list[ReturnDispositionResponse] = []


class ReturnResponse(BaseModel):
    """Return header representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    return_number: str
    seller_id: UUID
    warehouse_id: UUID
    order_id: UUID | None = None
    rma_number: str | None = None
    inbound_tracking_number: str | None = None
    status: str
    received_at: datetime | None = None
    completed_at: datetime | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    lines: list[ReturnLineResponse] = []


class ReturnListResponse(BaseModel):
    """Paginated list response for returns."""

    items: list[ReturnResponse]
    total: int
    limit: int
    offset: int
