"""
--------------------------------------------------------------------------------
File        : core/apis/schemas/responses/identity_response.py
Purpose     : Define identity and access response schemas.

Responsibilities:
    - Hide sensitive account fields such as password hashes.
    - Serialize UUIDs, timestamps, roles, and active scopes for API clients.

Flow:
    Controller response data
        ->
    Pydantic response schema
        ->
    FastAPI serialized JSON

Used By:
    - core/apis/routes/identity_routes.py

Returns:
    BaseModel instances - Serialized response payloads.

Raises:
    pydantic.ValidationError: When controller payloads do not match contracts.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TokenResponse(BaseModel):
    """Response body for successful authentication or token refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Public user account response."""

    id: UUID
    email: str
    name: str
    role: str
    status: str
    token_version: int
    seller_ids: list[UUID] = []
    warehouse_ids: list[UUID] = []
    created_by_user_id: UUID | None = None
    created_by_name: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SellerResponse(BaseModel):
    """Public seller tenant response."""

    id: UUID
    code: str
    name: str
    contact_email: str | None
    contact_phone: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WarehouseResponse(BaseModel):
    """Public warehouse response."""

    id: UUID
    code: str
    name: str
    address_line1: str | None
    city: str | None
    state: str | None
    postal_code: str | None
    timezone: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssignmentResponse(BaseModel):
    """Public assignment creation response."""

    id: UUID
    user_id: UUID
    assignment_role: str
    seller_id: UUID | None = None
    warehouse_id: UUID | None = None

    model_config = ConfigDict(from_attributes=True)
