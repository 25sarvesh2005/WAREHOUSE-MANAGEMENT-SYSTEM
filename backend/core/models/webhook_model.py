"""
SQLAlchemy ORM models for webhook subscriptions and outbound delivery auditing.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class WebhookSubscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Registered webhook destination for tenant or global operational events."""

    __tablename__ = "webhook_subscriptions"

    tenant_id: Mapped[str] = mapped_column(String(50), nullable=False, default="GLOBAL", index=True)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    secret: Mapped[str] = mapped_column(String(255), nullable=False)
    event_types: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ACTIVE", index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    deliveries: Mapped[list[WebhookDelivery]] = relationship(
        "WebhookDelivery",
        back_populates="subscription",
        cascade="all, delete-orphan",
    )


class WebhookDelivery(UUIDPrimaryKeyMixin, Base):
    """Audit record for an outbound HTTP delivery attempt."""

    __tablename__ = "webhook_deliveries"

    subscription_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("webhook_subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    outbox_event_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("outbox_events.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    delivered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    subscription: Mapped[WebhookSubscription] = relationship("WebhookSubscription", back_populates="deliveries")

