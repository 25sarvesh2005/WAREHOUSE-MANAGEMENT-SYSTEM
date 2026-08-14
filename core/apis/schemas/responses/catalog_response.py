"""
--------------------------------------------------------------------------------
File        : core/apis/schemas/responses/catalog_response.py
Purpose     : Define catalog and policy response schemas.

Responsibilities:
    - Serialize product, identifier, location, and policy records.
    - Preserve API response contracts independent of SQLAlchemy models.

Flow:
    Controller response data
        ->
    Pydantic response schema
        ->
    FastAPI serialized JSON

Used By:
    - core/apis/routes/catalog_routes.py

Returns:
    BaseModel instances - Serialized catalog responses.

Raises:
    pydantic.ValidationError: When controller payloads do not match contracts.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProductResponse(BaseModel):
    """Public product response."""

    id: UUID
    seller_id: UUID
    sku: str
    name: str
    description: str | None
    unit_of_measure: str
    weight: Decimal | None
    length: Decimal | None
    width: Decimal | None
    height: Decimal | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductIdentifierResponse(BaseModel):
    """Public product identifier response."""

    id: UUID
    product_id: UUID
    identifier_type: str
    identifier_value: str
    is_primary: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WarehouseLocationResponse(BaseModel):
    """Public warehouse location response."""

    id: UUID
    warehouse_id: UUID
    code: str
    location_type: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SellerOrderPolicyResponse(BaseModel):
    """Public seller order policy response."""

    id: UUID
    seller_id: UUID
    allow_backorder: bool
    allow_partial_fulfillment: bool
    reservation_expiry_minutes: int
    allocation_strategy: str
    cancellation_policy: str | None
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
