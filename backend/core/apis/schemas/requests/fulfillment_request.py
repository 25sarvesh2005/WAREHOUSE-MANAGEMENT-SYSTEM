"""
--------------------------------------------------------------------------------
File        : core/apis/schemas/requests/fulfillment_request.py
Purpose     : Request validation schemas for pick tasks, packages, and shipments.

Responsibilities:
    - Validate pick task creation and execution completion payloads.
    - Validate package measurements and manual shipment tracking parameters.

Used By:
    - core/apis/routes/fulfillment_routes.py
    - core/controllers/fulfillment_controller.py

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


class PickTaskCreateRequest(BaseModel):
    """Payload to create a pick task for a reserved order."""

    model_config = ConfigDict(extra="forbid")

    order_id: UUID = Field(description="Reserved order UUID")
    assigned_user_id: UUID | None = Field(default=None, description="Optional worker user UUID")
    priority: int = Field(default=1, ge=1, le=10, description="Pick task priority (1-10)")


class PickTaskLineCompletionItem(BaseModel):
    """Execution line result for a pick task."""

    model_config = ConfigDict(extra="forbid")

    pick_task_line_id: UUID = Field(description="Pick task line UUID")
    picked_quantity: Decimal = Field(ge=Decimal("0.00"), description="Quantity picked")
    short_quantity: Decimal = Field(
        default=Decimal("0.00"), ge=Decimal("0.00"), description="Shortage quantity"
    )


class PickTaskCompleteRequest(BaseModel):
    """Payload when a warehouse worker completes a pick task."""

    model_config = ConfigDict(extra="forbid")

    lines: list[PickTaskLineCompletionItem] = Field(
        min_length=1, description="Picked line item quantities"
    )


class PackageItemRequest(BaseModel):
    """Package dimension item within a shipment creation request."""

    model_config = ConfigDict(extra="forbid")

    box_type: str = Field(default="CUSTOM", max_length=50, description="Package box type")
    weight_lbs: Decimal | None = Field(
        default=None, ge=Decimal("0.00"), description="Weight in lbs"
    )
    length_in: Decimal | None = Field(
        default=None, ge=Decimal("0.00"), description="Length in inches"
    )
    width_in: Decimal | None = Field(
        default=None, ge=Decimal("0.00"), description="Width in inches"
    )
    height_in: Decimal | None = Field(
        default=None, ge=Decimal("0.00"), description="Height in inches"
    )


class ShipmentCreateRequest(BaseModel):
    """Manual shipment dispatch request payload."""

    model_config = ConfigDict(extra="forbid")

    order_id: UUID = Field(description="Packed order UUID")
    warehouse_id: UUID = Field(description="Warehouse facility UUID")
    carrier: str = Field(
        default="MANUAL_CARRIER", max_length=50, description="Shipping carrier name"
    )
    service_level: str = Field(
        default="GROUND", max_length=50, description="Shipping service level"
    )
    tracking_number: str = Field(
        min_length=1, max_length=100, description="Tracking number string"
    )
    packages: list[PackageItemRequest] = Field(
        default_factory=list, description="Packages attached to shipment"
    )
