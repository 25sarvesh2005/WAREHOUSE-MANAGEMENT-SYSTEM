"""
--------------------------------------------------------------------------------
File        : core/apis/schemas/requests/identity_request.py
Purpose     : Define identity and access request schemas.

Responsibilities:
    - Validate login, user creation, seller, warehouse, and assignment payloads.
    - Keep transport shape separate from persistence models.

Flow:
    HTTP request body
        ->
    Pydantic request schema
        ->
    Thin route passes data to controller

Used By:
    - core/apis/routes/identity_routes.py

Returns:
    BaseModel instances - Validated request payloads.

Raises:
    pydantic.ValidationError: When payload validation fails.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from core.constants import BusinessStatus, UserRole, UserStatus


def _validate_permissive_email(v: object) -> str:
    """Accept syntactically valid email addresses including .local TLDs."""
    import email_validator

    s = str(v).strip().lower()
    if not s or "@" not in s:
        raise ValueError("Invalid email format")
    try:
        info = email_validator.validate_email(s, check_deliverability=False)
        return info.normalized
    except email_validator.EmailNotValidError:
        user, domain = s.rsplit("@", 1)
        if user and domain and ("." in domain or domain == "localhost"):
            return s
        raise ValueError("Invalid email address")


class LoginRequest(BaseModel):
    """Request body for user login."""

    email: str = Field(description="User email address.")
    password: str = Field(min_length=8, max_length=128, description="User password.")

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, v: str) -> str:
        return _validate_permissive_email(v)


class RegisterSellerRequest(BaseModel):
    """Request body for public seller registration (pending admin approval)."""

    email: str = Field(description="Seller account email address.")
    name: str = Field(min_length=1, max_length=200, description="Full contact name.")
    password: str = Field(min_length=6, max_length=128, description="Account password.")
    company_name: str = Field(min_length=1, max_length=200, description="Company / Brand name.")
    seller_code: str | None = Field(default=None, max_length=50, description="Optional custom seller code.")

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, v: str) -> str:
        return _validate_permissive_email(v)


class UserCreateRequest(BaseModel):
    """Request body for administrative user creation."""

    email: str = Field(description="User email address.")
    name: str = Field(min_length=1, max_length=200, description="Display name.")
    password: str = Field(min_length=8, max_length=128, description="Initial password.")
    role: UserRole = Field(description="Application role.")
    status: UserStatus = Field(default=UserStatus.ACTIVE, description="Initial account status.")

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, v: str) -> str:
        return _validate_permissive_email(v)


class SellerCreateRequest(BaseModel):
    """Request body for seller tenant creation."""

    code: str = Field(min_length=1, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=200)
    contact_email: str | None = None
    contact_phone: str | None = Field(default=None, max_length=50)
    status: BusinessStatus = BusinessStatus.ACTIVE

    @field_validator("contact_email")
    @classmethod
    def validate_contact_email(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return _validate_permissive_email(v)


class WarehouseCreateRequest(BaseModel):
    """Request body for warehouse creation."""

    code: str = Field(min_length=1, max_length=50, pattern=r"^[A-Za-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=200)
    address_line1: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=30)
    timezone: str = Field(default="America/Los_Angeles", max_length=100)
    status: BusinessStatus = BusinessStatus.ACTIVE


class UserSellerAssignmentRequest(BaseModel):
    """Request body for assigning a user to a seller."""

    user_id: UUID
    seller_id: UUID
    assignment_role: UserRole

    model_config = ConfigDict(use_enum_values=True)


class UserWarehouseAssignmentRequest(BaseModel):
    """Request body for assigning a user to a warehouse."""

    user_id: UUID
    warehouse_id: UUID
    assignment_role: UserRole

    model_config = ConfigDict(use_enum_values=True)


class RefreshRequest(BaseModel):
    """Request body for refresh-token rotation."""

    refresh_token: str = Field(
        min_length=1,
        max_length=512,
        description="Raw refresh token issued at login.",
    )


class UserStatusUpdateRequest(BaseModel):
    """Request body for updating a user's account status."""

    status: UserStatus = Field(description="New account status (ACTIVE, INACTIVE, SUSPENDED, PENDING_APPROVAL).")

    model_config = ConfigDict(use_enum_values=True)


class SellerStatusUpdateRequest(BaseModel):
    """Request body for updating a seller's business status."""

    status: BusinessStatus = Field(description="New seller business status (ACTIVE, INACTIVE, SUSPENDED).")

    model_config = ConfigDict(use_enum_values=True)
