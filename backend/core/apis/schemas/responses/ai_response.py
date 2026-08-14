"""
--------------------------------------------------------------------------------
File        : core/apis/schemas/responses/ai_response.py
Purpose     : Define response schemas for read-only AI operations assistance.

Responsibilities:
    - Serialize AI answers with audited interaction IDs and evidence references.
    - Return structured inventory and ledger data beside generated or fallback text.

Flow:
    AIController result dictionary
        ->
    Pydantic response schema
        ->
    FastAPI JSON

Used By:
    - core/apis/routes/ai_routes.py

Returns:
    BaseModel instances - Serialized read-only AI responses.

Raises:
    pydantic.ValidationError: When response schema mapping fails.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AIReferenceResponse(BaseModel):
    """Application record reference used by an AI answer."""

    record_type: str
    record_id: UUID | None
    label: str
    metadata: dict[str, object] = Field(default_factory=dict)


class AIAvailabilityRowResponse(BaseModel):
    """Available inventory evidence row returned by the read-only AI tool."""

    seller_id: UUID
    seller_code: str
    product_id: UUID
    sku: str
    product_name: str
    warehouse_id: UUID
    warehouse_code: str
    available_quantity: Decimal


class AILedgerMovementRowResponse(BaseModel):
    """Movement ledger evidence row returned by the read-only AI tool."""

    movement_id: UUID
    seller_id: UUID
    seller_code: str
    product_id: UUID
    sku: str
    product_name: str
    warehouse_id: UUID
    warehouse_code: str
    inventory_state: str
    quantity_delta: Decimal
    movement_type: str
    source_type: str
    source_id: UUID
    reason_code: str | None
    reason_text: str | None
    recorded_at: datetime


class AIInventoryAvailabilityResponse(BaseModel):
    """Read-only AI response for available inventory questions."""

    interaction_id: UUID
    status: str
    safety_decision: str
    provider_name: str
    model_name: str
    answer: str
    references: list[AIReferenceResponse]
    rows: list[AIAvailabilityRowResponse]

    model_config = ConfigDict(from_attributes=True)


class AILedgerExplanationResponse(BaseModel):
    """Read-only AI response for inventory ledger explanation questions."""

    interaction_id: UUID
    status: str
    safety_decision: str
    provider_name: str
    model_name: str
    answer: str
    references: list[AIReferenceResponse]
    movements: list[AILedgerMovementRowResponse]

    model_config = ConfigDict(from_attributes=True)


class AIOperationalStatusResponse(BaseModel):
    """Read-only AI response for operational record status questions."""

    interaction_id: UUID
    status: str
    safety_decision: str
    provider_name: str
    model_name: str
    answer: str
    references: list[AIReferenceResponse]
    record: dict[str, object] | None

    model_config = ConfigDict(from_attributes=True)


class AIFeedbackResponse(BaseModel):
    """Audited user feedback response."""

    feedback_id: UUID
    interaction_id: UUID
    actor_user_id: UUID
    is_helpful: bool
    comment: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AIProviderHealthResponse(BaseModel):
    """AI provider runtime status and health summary."""

    enabled: bool
    provider_name: str
    model_name: str
    configured: bool
    status: str
    tested_at: datetime


class AIToolCallDetailResponse(BaseModel):
    """Audited tool call detail record."""

    id: UUID
    tool_name: str
    status: str
    permission_scope: dict[str, object]
    input_excerpt: str | None = None
    output_reference_count: int
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AIDraftActionDetailResponse(BaseModel):
    """Audited draft recommendation detail record."""

    id: UUID
    action_type: str
    status: str
    target_record_type: str | None = None
    target_record_id: UUID | None = None
    draft_payload_excerpt: str | None = None
    requires_approval: bool
    approved_by_user_id: UUID | None = None
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
    rejection_reason: str | None = None
    metadata_json: dict[str, object] = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AIInteractionSummaryItem(BaseModel):
    """Audited AI interaction summary item for admin listing."""

    id: UUID
    actor_user_id: UUID
    correlation_id: str
    request_category: str
    status: str
    provider_name: str
    model_name: str
    prompt_excerpt: str | None = None
    response_excerpt: str | None = None
    safety_decision: str
    refusal_reason: str | None = None
    tool_call_count: int = 0
    draft_action_count: int = 0
    feedback_count: int = 0
    helpful_count: int = 0
    unhelpful_count: int = 0
    created_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AIInteractionListResponse(BaseModel):
    """Paginated list of audited AI interactions."""

    items: list[AIInteractionSummaryItem]
    total_count: int
    limit: int
    offset: int


class AIInteractionDetailResponse(BaseModel):
    """Full detail view of an AI interaction with tool calls, drafts, and feedbacks."""

    id: UUID
    actor_user_id: UUID
    correlation_id: str
    request_category: str
    status: str
    provider_name: str
    model_name: str
    prompt_hash: str
    prompt_excerpt: str | None = None
    response_excerpt: str | None = None
    safety_decision: str
    refusal_reason: str | None = None
    seller_scope: list[object] = Field(default_factory=list)
    warehouse_scope: list[object] = Field(default_factory=list)
    retrieved_references: list[object] = Field(default_factory=list)
    metadata_json: dict[str, object] = Field(default_factory=dict)
    tool_calls: list[AIToolCallDetailResponse] = Field(default_factory=list)
    draft_actions: list[AIDraftActionDetailResponse] = Field(default_factory=list)
    feedbacks: list[AIFeedbackResponse] = Field(default_factory=list)
    created_at: datetime
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AIExceptionCategorySummary(BaseModel):
    """Exception category count, severity, and preview items."""

    category: str
    label: str
    count: int
    severity: str
    items: list[dict[str, object]] = Field(default_factory=list)


class AIExceptionSummaryResponse(BaseModel):
    """Read-only operational exception summary."""

    interaction_id: UUID
    status: str
    safety_decision: str
    provider_name: str
    model_name: str
    narrative_summary: str
    total_exceptions: int
    categories: list[AIExceptionCategorySummary]
    references: list[AIReferenceResponse]

    model_config = ConfigDict(from_attributes=True)


class AIDraftActionListResponse(BaseModel):
    """Paginated list of draft recommendation actions."""

    items: list[AIDraftActionDetailResponse]
    total_count: int
    limit: int
    offset: int


class AIDraftRecommendationResponse(BaseModel):
    """Response returned when a new draft recommendation is generated."""

    interaction_id: UUID
    draft_id: UUID
    action_type: str
    status: str
    recommendation_summary: str
    draft_payload: dict[str, object]
    references: list[AIReferenceResponse]

    model_config = ConfigDict(from_attributes=True)

