"""
--------------------------------------------------------------------------------
File        : core/apis/schemas/requests/receiving_request.py
Purpose     : Define receiving request schemas.

Responsibilities:
    - Validate receipt creation, line update, completion, and duplicate override.

Flow:
    HTTP request body -> Pydantic request schema

Used By:
    - core/apis/routes/receiving_routes.py

Returns:
    BaseModel instances - Validated request payloads.

Raises:
    pydantic.ValidationError: When validation fails.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.constants import ReceiptSourceType


class ReceiptCreateRequest(BaseModel):
    """Request body to create a new receiving receipt draft."""

    seller_id: UUID = Field(description="Seller tenant UUID.")
    warehouse_id: UUID = Field(description="Warehouse facility UUID.")
    source_type: ReceiptSourceType = Field(description="Receiving source type.")
    source_reference: str = Field(
        min_length=1, max_length=255, description="Source tracking reference."
    )
    client_draft_id: str | None = Field(
        default=None, max_length=255, description="Client draft ID for offline sync."
    )
    expected_arrival_at: datetime | None = Field(
        default=None, description="Expected arrival timestamp."
    )

    model_config = ConfigDict(use_enum_values=True)


class ReceiptLineSaveRequest(BaseModel):
    """Request body to add or update a line item on a receiving receipt."""

    product_id: UUID = Field(description="Product SKU UUID.")
    expected_quantity: Decimal = Field(
        default=Decimal("0.00"), ge=Decimal("0.00"), description="Expected quantity."
    )
    sellable_quantity: Decimal = Field(
        default=Decimal("0.00"), ge=Decimal("0.00"), description="Sellable quantity."
    )
    damaged_quantity: Decimal = Field(
        default=Decimal("0.00"), ge=Decimal("0.00"), description="Damaged quantity."
    )
    quarantined_quantity: Decimal = Field(
        default=Decimal("0.00"), ge=Decimal("0.00"), description="Quarantined quantity."
    )
    notes: str | None = Field(default=None, max_length=500, description="Condition notes.")


class DuplicateOverrideRequest(BaseModel):
    """Request body to override a duplicate receipt error."""

    original_receipt_id: UUID = Field(description="Original completed receipt UUID.")
    override_reason: str = Field(min_length=5, max_length=500, description="Reason for override.")


class ReceiptCompleteRequest(BaseModel):
    """Request body to complete a receiving receipt."""

    notes: str | None = Field(default=None, max_length=500, description="Completion notes.")
