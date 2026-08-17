"""
SQLAlchemy ORM models for append-only audit trail event storage.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AuditEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Persisted audit trail record."""

    __tablename__ = "audit_events"

    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), index=True)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_record_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_record_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), index=True)
    reason: Mapped[str | None] = mapped_column(String(1000))
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
