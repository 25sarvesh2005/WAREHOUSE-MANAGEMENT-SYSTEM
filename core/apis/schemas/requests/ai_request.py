"""
--------------------------------------------------------------------------------
File        : core/apis/schemas/requests/ai_request.py
Purpose     : Define request schemas for read-only AI operations assistance.

Responsibilities:
    - Validate read-only AI inventory and ledger question payloads.
    - Prevent ambiguous seller and warehouse filter combinations.

Flow:
    HTTP JSON
        ->
    Pydantic request model
        ->
    AIController

Used By:
    - core/apis/routes/ai_routes.py

Returns:
    BaseModel instances - Validated read-only AI request payloads.

Raises:
    pydantic.ValidationError: When request shape validation fails.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class AIInventoryAvailabilityRequest(BaseModel):
    """Request for a scoped read-only available inventory answer."""

    sku: str = Field(..., min_length=1, max_length=100)
    seller_id: UUID | None = None
    seller_code: str | None = Field(default=None, min_length=1, max_length=50)
    warehouse_id: UUID | None = None
    warehouse_code: str | None = Field(default=None, min_length=1, max_length=50)
    prompt: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_filter_pairs(self) -> AIInventoryAvailabilityRequest:
        """
        Reject ambiguous seller and warehouse filter combinations.

        Args:
            None.

        Returns:
            AIInventoryAvailabilityRequest: Validated request instance.

        Raises:
            ValueError: If both ID and code are supplied for the same filter.
        """
        if self.seller_id is not None and self.seller_code is not None:
            raise ValueError("Use seller_id or seller_code, not both.")
        if self.warehouse_id is not None and self.warehouse_code is not None:
            raise ValueError("Use warehouse_id or warehouse_code, not both.")
        return self


class AILedgerExplanationRequest(BaseModel):
    """Request for a scoped read-only ledger explanation answer."""

    sku: str = Field(..., min_length=1, max_length=100)
    seller_id: UUID | None = None
    seller_code: str | None = Field(default=None, min_length=1, max_length=50)
    warehouse_id: UUID | None = None
    warehouse_code: str | None = Field(default=None, min_length=1, max_length=50)
    limit: int = Field(default=10, ge=1, le=50)
    prompt: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_filter_pairs(self) -> AILedgerExplanationRequest:
        """
        Reject ambiguous seller and warehouse filter combinations.

        Args:
            None.

        Returns:
            AILedgerExplanationRequest: Validated request instance.

        Raises:
            ValueError: If both ID and code are supplied for the same filter.
        """
        if self.seller_id is not None and self.seller_code is not None:
            raise ValueError("Use seller_id or seller_code, not both.")
        if self.warehouse_id is not None and self.warehouse_code is not None:
            raise ValueError("Use warehouse_id or warehouse_code, not both.")
        return self


class AIOperationalStatusRequest(BaseModel):
    """Request for a scoped read-only operational status answer."""

    record_id: UUID | None = None
    reference_number: str | None = Field(default=None, min_length=1, max_length=100)
    seller_id: UUID | None = None
    seller_code: str | None = Field(default=None, min_length=1, max_length=50)
    warehouse_id: UUID | None = None
    warehouse_code: str | None = Field(default=None, min_length=1, max_length=50)
    prompt: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_status_lookup(self) -> AIOperationalStatusRequest:
        """
        Require exactly one record lookup key and reject ambiguous filters.

        Args:
            None.

        Returns:
            AIOperationalStatusRequest: Validated request instance.

        Raises:
            ValueError: If lookup keys or filters are ambiguous.
        """
        if (self.record_id is None) == (self.reference_number is None):
            raise ValueError("Use exactly one of record_id or reference_number.")
        if self.seller_id is not None and self.seller_code is not None:
            raise ValueError("Use seller_id or seller_code, not both.")
        if self.warehouse_id is not None and self.warehouse_code is not None:
            raise ValueError("Use warehouse_id or warehouse_code, not both.")
        return self


class AIFeedbackRequest(BaseModel):
    """Request to capture user feedback on an AI interaction."""

    is_helpful: bool
    comment: str | None = Field(default=None, max_length=1000)


class AIExceptionSummaryRequest(BaseModel):
    """Request for a scoped read-only operational exceptions summary."""

    seller_id: UUID | None = None
    seller_code: str | None = Field(default=None, min_length=1, max_length=50)
    warehouse_id: UUID | None = None
    warehouse_code: str | None = Field(default=None, min_length=1, max_length=50)
    prompt: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_filter_pairs(self) -> AIExceptionSummaryRequest:
        """
        Reject ambiguous seller and warehouse filter combinations.

        Args:
            None.

        Returns:
            AIExceptionSummaryRequest: Validated request instance.

        Raises:
            ValueError: If both ID and code are supplied for the same filter.
        """
        if self.seller_id is not None and self.seller_code is not None:
            raise ValueError("Use seller_id or seller_code, not both.")
        if self.warehouse_id is not None and self.warehouse_code is not None:
            raise ValueError("Use warehouse_id or warehouse_code, not both.")
        return self


class AIDraftRecommendationRequest(BaseModel):
    """Request for a human-reviewable draft operational recommendation."""

    recommendation_type: str = Field(..., min_length=1, max_length=100)
    target_record_type: str | None = Field(default=None, max_length=100)
    target_record_id: UUID | None = None
    seller_id: UUID | None = None
    seller_code: str | None = Field(default=None, min_length=1, max_length=50)
    warehouse_id: UUID | None = None
    warehouse_code: str | None = Field(default=None, min_length=1, max_length=50)
    details: dict[str, object] = Field(default_factory=dict)
    prompt: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_filter_pairs(self) -> AIDraftRecommendationRequest:
        """
        Reject ambiguous seller and warehouse filter combinations.

        Args:
            None.

        Returns:
            AIDraftRecommendationRequest: Validated request instance.

        Raises:
            ValueError: If both ID and code are supplied for the same filter.
        """
        if self.seller_id is not None and self.seller_code is not None:
            raise ValueError("Use seller_id or seller_code, not both.")
        if self.warehouse_id is not None and self.warehouse_code is not None:
            raise ValueError("Use warehouse_id or warehouse_code, not both.")
        return self


class AIDraftRejectRequest(BaseModel):
    """Request to reject a draft recommendation."""

    rejection_reason: str | None = Field(default=None, max_length=1000)

