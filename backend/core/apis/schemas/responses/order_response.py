"""
--------------------------------------------------------------------------------
File        : core/apis/schemas/responses/order_response.py
Purpose     : Response schemas for customer orders and reservations.

Responsibilities:
    - Serialize Order, OrderLine, and InventoryReservation records to JSON.

Used By:
    - core/apis/routes/order_routes.py

Returns:
    Pydantic Response Schemas.

Raises:
    pydantic.ValidationError: On serialization failures.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InventoryReservationResponse(BaseModel):
    """Serialized inventory reservation record."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_line_id: UUID
    warehouse_id: UUID
    product_id: UUID
    quantity: Decimal
    status: str
    reserved_at: datetime
    expires_at: datetime | None = None
    released_at: datetime | None = None


class OrderLineResponse(BaseModel):
    """Serialized order line item breakdown."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    product_id: UUID
    ordered_quantity: Decimal
    reserved_quantity: Decimal
    picked_quantity: Decimal
    shipped_quantity: Decimal
    backordered_quantity: Decimal
    cancelled_quantity: Decimal
    reservations: list[InventoryReservationResponse] = Field(default_factory=list)


class OrderResponse(BaseModel):
    """Serialized order header model response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    seller_id: UUID
    seller_order_number: str
    warehouse_id: UUID
    channel: str
    status: str
    policy_snapshot: dict[str, Any] | None = None
    customer_name: str | None = None
    shipping_address_line1: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    created_at: datetime
    updated_at: datetime
    lines: list[OrderLineResponse] = Field(default_factory=list)
