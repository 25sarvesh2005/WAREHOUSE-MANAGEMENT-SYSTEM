"""
Transfer Response Schemas.

Pydantic schemas serializing transfer response models.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TransferLineResponse(BaseModel):
    """Transfer line item representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transfer_id: UUID
    product_id: UUID
    requested_quantity: Decimal
    approved_quantity: Decimal
    dispatched_quantity: Decimal
    received_good_quantity: Decimal
    received_damaged_quantity: Decimal
    missing_quantity: Decimal
    overage_quantity: Decimal
    notes: str | None = None


class TransferResponse(BaseModel):
    """Transfer header representation."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transfer_number: str
    seller_id: UUID
    origin_warehouse_id: UUID
    destination_warehouse_id: UUID
    status: str
    created_by_user_id: UUID
    approved_by_user_id: UUID | None = None
    dispatched_at: datetime | None = None
    received_at: datetime | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    lines: list[TransferLineResponse] = []


class TransferListResponse(BaseModel):
    """Paginated list response for transfers."""

    items: list[TransferResponse]
    total: int
    limit: int
    offset: int
