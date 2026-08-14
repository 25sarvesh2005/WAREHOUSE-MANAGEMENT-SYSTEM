"""
--------------------------------------------------------------------------------
File        : core/apis/schemas/responses/fulfillment_response.py
Purpose     : Response schemas for pick tasks, packages, and shipments.

Responsibilities:
    - Serialize PickTask, PickTaskLine, Package, and Shipment records to JSON.

Used By:
    - core/apis/routes/fulfillment_routes.py

Returns:
    Pydantic Response Schemas.

Raises:
    pydantic.ValidationError: On serialization failures.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PickTaskLineResponse(BaseModel):
    """Serialized pick task line item."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pick_task_id: UUID
    order_line_id: UUID
    product_id: UUID
    location_id: UUID | None = None
    requested_quantity: Decimal
    picked_quantity: Decimal
    short_quantity: Decimal


class PickTaskResponse(BaseModel):
    """Serialized warehouse pick task header."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    warehouse_id: UUID
    assigned_user_id: UUID | None = None
    status: str
    priority: int
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    lines: list[PickTaskLineResponse] = Field(default_factory=list)


class PackageResponse(BaseModel):
    """Serialized package dimension record."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    shipment_id: UUID | None = None
    box_type: str
    weight_lbs: Decimal | None = None
    length_in: Decimal | None = None
    width_in: Decimal | None = None
    height_in: Decimal | None = None


class ShipmentEventResponse(BaseModel):
    """Serialized shipment event entry."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    shipment_id: UUID
    event_type: str
    details: str | None = None
    created_at: datetime


class ShipmentResponse(BaseModel):
    """Serialized manual shipment dispatch record."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    warehouse_id: UUID
    carrier: str
    service_level: str
    tracking_number: str
    status: str
    shipped_at: datetime
    created_at: datetime
    updated_at: datetime
    packages: list[PackageResponse] = Field(default_factory=list)
    events: list[ShipmentEventResponse] = Field(default_factory=list)
