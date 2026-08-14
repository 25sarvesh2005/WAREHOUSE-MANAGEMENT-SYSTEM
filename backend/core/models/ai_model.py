"""
--------------------------------------------------------------------------------
File        : core/models/ai_model.py
Purpose     : Define audited AI interaction persistence models.

Responsibilities:
    - Persist AI interaction summaries without storing unnecessary prompt secrets.
    - Persist permission-aware read-tool call evidence and draft-action records.
    - Keep AI audit storage separate from operational mutation workflows.

Flow:
    AI controller or service boundary
        ->
    ai_crud persistence functions
        ->
    ai_interactions, ai_tool_calls, and ai_draft_actions tables

Used By:
    - core/cruds/ai_crud.py
    - future read-only AI controllers and tools

Returns:
    SQLAlchemy model instances - Audited AI persistence records.

Raises:
    sqlalchemy.exc.IntegrityError: On uniqueness or foreign key violations.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AIInteraction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Audited top-level AI request and response summary."""

    __tablename__ = "ai_interactions"
    __table_args__ = (
        UniqueConstraint("correlation_id", name="uq_ai_interactions_correlation_id"),
        Index("ix_ai_interactions_actor_status", "actor_user_id", "status"),
    )

    actor_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    request_category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_excerpt: Mapped[str | None] = mapped_column(String(500), nullable=True)
    response_excerpt: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    safety_decision: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    refusal_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    seller_scope: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    warehouse_scope: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    retrieved_references: Mapped[list[object]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AIToolCall(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Audited AI application-tool call summary."""

    __tablename__ = "ai_tool_calls"
    __table_args__ = (
        Index("ix_ai_tool_calls_interaction_status", "ai_interaction_id", "status"),
    )

    ai_interaction_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_interactions.id"), nullable=False, index=True
    )
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    permission_scope: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    input_excerpt: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    output_reference_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AIDraftAction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Audited AI-created draft action that cannot execute itself."""

    __tablename__ = "ai_draft_actions"
    __table_args__ = (
        Index("ix_ai_draft_actions_interaction_status", "ai_interaction_id", "status"),
    )

    ai_interaction_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_interactions.id"), nullable=False, index=True
    )
    action_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    target_record_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_record_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), index=True)
    draft_payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    draft_payload_excerpt: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    approved_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict
    )


class AIFeedback(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Audited user feedback for an AI interaction."""

    __tablename__ = "ai_feedbacks"
    __table_args__ = (
        Index("ix_ai_feedbacks_interaction_actor", "ai_interaction_id", "actor_user_id"),
    )

    ai_interaction_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_interactions.id"), nullable=False, index=True
    )
    actor_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    is_helpful: Mapped[bool] = mapped_column(Boolean, nullable=False)
    comment: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    metadata_json: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

