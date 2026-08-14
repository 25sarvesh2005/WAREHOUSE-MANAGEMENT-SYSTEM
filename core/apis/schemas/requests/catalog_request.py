"""
--------------------------------------------------------------------------------
File        : core/apis/schemas/requests/catalog_request.py
Purpose     : Define catalog and policy request schemas.

Responsibilities:
    - Validate product, identifier, location, and seller policy payloads.
    - Keep unresolved business policy explicit in API inputs.

Flow:
    HTTP request body
        ->
    Pydantic request schema
        ->
    Catalog controller applies scope and persistence

Used By:
    - core/apis/routes/catalog_routes.py

Returns:
    BaseModel instances - Validated catalog payloads.

Raises:
    pydantic.ValidationError: When payload validation fails.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from core.constants import (
    AllocationStrategy,
    BusinessStatus,
    ProductIdentifierType,
    WarehouseLocationType,
)


class ProductCreateRequest(BaseModel):
    """Request body for seller product creation."""

    seller_id: UUID
    sku: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    unit_of_measure: str = Field(default="EA", min_length=1, max_length=50)
    weight: Decimal | None = Field(default=None, ge=0)
    length: Decimal | None = Field(default=None, ge=0)
    width: Decimal | None = Field(default=None, ge=0)
    height: Decimal | None = Field(default=None, ge=0)
    status: BusinessStatus = BusinessStatus.ACTIVE


class ProductIdentifierCreateRequest(BaseModel):
    """Request body for product identifier creation."""

    product_id: UUID
    identifier_type: ProductIdentifierType
    identifier_value: str = Field(min_length=1, max_length=200)
    is_primary: bool = False


class WarehouseLocationCreateRequest(BaseModel):
    """Request body for warehouse location creation."""

    warehouse_id: UUID
    code: str = Field(min_length=1, max_length=100)
    location_type: WarehouseLocationType
    status: BusinessStatus = BusinessStatus.ACTIVE


class SellerOrderPolicyCreateRequest(BaseModel):
    """Request body for seller order policy creation."""

    seller_id: UUID
    allow_backorder: bool
    allow_partial_fulfillment: bool
    reservation_expiry_minutes: int = Field(ge=5, le=10080)
    allocation_strategy: AllocationStrategy
    cancellation_policy: str | None = Field(default=None, max_length=500)
