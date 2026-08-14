"""
Return Request Schemas.

Pydantic schemas validating API request bodies for return creation, receipt, and inspection.
"""

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class ReturnLineRequest(BaseModel):
    """Return line item request payload."""

    product_id: UUID | None = Field(None, description="Product SKU UUID (optional if unidentified)")
    expected_quantity: Decimal = Field(Decimal("0.00"), ge=Decimal("0.00"))
    received_quantity: Decimal = Field(Decimal("0.00"), ge=Decimal("0.00"))
    reason_code: str | None = Field(None, max_length=50)
    inspection_notes: str | None = Field(None, max_length=500)


class ReturnCreateRequest(BaseModel):
    """Payload for creating a return header."""

    seller_id: UUID = Field(..., description="Seller tenant UUID")
    warehouse_id: UUID = Field(..., description="Receiving warehouse UUID")
    order_id: UUID | None = Field(None, description="Optional customer order reference")
    rma_number: str | None = Field(None, max_length=100)
    inbound_tracking_number: str | None = Field(None, max_length=100)
    is_unidentified: bool = Field(False, description="True if unannounced/unidentified package")
    notes: str | None = Field(None, max_length=500)
    lines: list[ReturnLineRequest] = Field(..., min_length=1)


class ReturnReceiveLineRequest(BaseModel):
    """Received quantity update per return line."""

    line_id: UUID = Field(..., description="ReturnLine UUID")
    received_quantity: Decimal = Field(..., gt=Decimal("0.00"))


class ReturnReceiveRequest(BaseModel):
    """Payload for receiving return parcel at warehouse."""

    lines: list[ReturnReceiveLineRequest] = Field(..., min_length=1)


class ReturnDispositionRequestItem(BaseModel):
    """Inspection disposition outcome item."""

    return_line_id: UUID = Field(...)
    disposition_state: str = Field(..., description="Target bucket state (AVAILABLE, DAMAGED, etc.)")
    quantity: Decimal = Field(..., gt=Decimal("0.00"))
    destination_location_id: UUID | None = Field(None)
    notes: str | None = Field(None, max_length=500)


class ReturnInspectRequest(BaseModel):
    """Payload for logging inspection dispositions."""

    dispositions: list[ReturnDispositionRequestItem] = Field(..., min_length=1)
