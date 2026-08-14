"""
--------------------------------------------------------------------------------
File        : core/apis/schemas/requests/order_request.py
Purpose     : Request validation schemas for order creation and reservation endpoints.

Responsibilities:
    - Validate seller order header and line item creation payloads.
    - Enforce positive ordered quantities.
    - Validate order reservation request parameters.

Used By:
    - core/apis/routes/order_routes.py
    - core/controllers/order_controller.py

Returns:
    Pydantic Request Schemas.

Raises:
    pydantic.ValidationError: On invalid request payloads.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OrderLineCreateRequest(BaseModel):
    """Line item itemization inside an order creation request."""

    model_config = ConfigDict(extra="forbid")

    product_id: UUID = Field(description="Product SKU UUID")
    ordered_quantity: Decimal = Field(gt=Decimal("0.00"), description="Quantity ordered")


class OrderCreateRequest(BaseModel):
    """Customer order creation payload."""

    model_config = ConfigDict(extra="forbid")

    seller_id: UUID = Field(description="Seller tenant UUID")
    seller_order_number: str = Field(
        min_length=1, max_length=100, description="External seller order number"
    )
    warehouse_id: UUID = Field(description="Assigned warehouse facility UUID")
    channel: str = Field(default="DIRECT", max_length=50, description="Order sales channel")
    customer_name: str | None = Field(
        default=None, max_length=200, description="Customer recipient name"
    )
    shipping_address_line1: str | None = Field(
        default=None, max_length=255, description="Street address line"
    )
    city: str | None = Field(default=None, max_length=100, description="City")
    state: str | None = Field(default=None, max_length=100, description="State/Province")
    postal_code: str | None = Field(default=None, max_length=30, description="Postal zip code")
    lines: list[OrderLineCreateRequest] = Field(min_length=1, description="Order line items")


class OrderReserveRequest(BaseModel):
    """Optional payload when triggering inventory reservation."""

    model_config = ConfigDict(extra="forbid")

    notes: str | None = Field(default=None, max_length=500, description="Reservation notes")
