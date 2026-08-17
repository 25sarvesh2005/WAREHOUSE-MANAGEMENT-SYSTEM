"""
SQLAlchemy ORM models for voice interactions and voice receiving drafts.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class VoiceInteraction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Audited voice interaction record capturing STT, TTS, and safety metadata."""

    __tablename__ = "voice_interactions"
    __table_args__ = (
        Index("ix_voice_interactions_actor_created", "actor_user_id", "created_at"),
        Index("ix_voice_interactions_status_created", "status", "created_at"),
    )

    actor_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    warehouse_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("warehouses.id"), nullable=True, index=True
    )
    receipt_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("receipts.id"), nullable=True, index=True
    )
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False)
    stt_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    tts_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    language_code: Mapped[str] = mapped_column(String(20), nullable=False, default="en-IN")
    transcript_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript_confidence: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4), nullable=True
    )
    parsed_payload: Mapped[dict[str, object] | None] = mapped_column(
        JSONB, nullable=True
    )
    safety_flags: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )


class VoiceReceivingDraft(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Voice-generated receiving draft containing proposed lines pending human review."""

    __tablename__ = "voice_receiving_drafts"
    __table_args__ = (
        Index("ix_voice_receiving_drafts_actor_created", "actor_user_id", "created_at"),
        Index("ix_voice_receiving_drafts_status_created", "status", "created_at"),
    )

    voice_interaction_id: Mapped[UUID] = mapped_column(
        ForeignKey("voice_interactions.id"), nullable=False, index=True
    )
    actor_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    warehouse_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("warehouses.id"), nullable=True, index=True
    )
    product_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("products.id"), nullable=True, index=True
    )
    receipt_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("receipts.id"), nullable=True, index=True
    )
    structured_lines: Mapped[list[object]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, default="DRAFTED"
    )
