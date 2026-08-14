"""
Transfer Request Schemas.

Pydantic schemas validating API request bodies for transfer creation, approval, dispatch, and receipt.
"""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class TransferLineRequest(BaseModel):
    """Line item payload for transfer creation."""

    product_id: UUID = Field(..., description="Product SKU UUID")
    requested_quantity: Decimal = Field(..., gt=Decimal("0.00"), description="Transfer quantity requested")
    notes: str | None = Field(None, max_length=500, description="Optional line comments")


class TransferCreateRequest(BaseModel):
    """Payload for creating a multi-warehouse transfer."""

    seller_id: UUID = Field(..., description="Seller tenant UUID")
    origin_warehouse_id: UUID = Field(..., description="Origin dispatch warehouse UUID")
    destination_warehouse_id: UUID = Field(..., description="Destination receiving warehouse UUID")
    notes: str | None = Field(None, max_length=500, description="Optional transfer notes")
    lines: list[TransferLineRequest] = Field(..., min_length=1, description="Transfer line items")


class TransferReceiveLineRequest(BaseModel):
    """Line item receipt breakdown for transfers."""

    line_id: UUID = Field(..., description="Transfer line UUID")
    received_good_quantity: Decimal = Field(Decimal("0.00"), ge=Decimal("0.00"))
    received_damaged_quantity: Decimal = Field(Decimal("0.00"), ge=Decimal("0.00"))


class TransferReceiveRequest(BaseModel):
    """Payload for receiving a transfer at destination warehouse."""

    lines: list[TransferReceiveLineRequest] = Field(..., min_length=1)


class TransferResolveDiscrepancyRequest(BaseModel):
    """Payload for manager discrepancy resolution."""

    notes: str = Field(..., min_length=1, max_length=500, description="Discrepancy resolution reason")
