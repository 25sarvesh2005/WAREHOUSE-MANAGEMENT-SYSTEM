"""
--------------------------------------------------------------------------------
File        : core/models/outbox_model.py
Purpose     : Define transactional outbox storage for future background jobs.

Responsibilities:
    - Persist deferred events within business transactions.
    - Track dispatch attempts and failure details without provider coupling.

Flow:
    Controller transaction
        ->
    OutboxEvent persisted
        ->
    Worker dispatches after commit

Used By:
    - core/jobs/outbox_dispatch_job.py

Returns:
    OutboxEvent - Persisted outbox row.

Raises:
    sqlalchemy.exc.SQLAlchemyError: On persistence failures.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class OutboxEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Persisted outbox event awaiting background dispatch."""

    __tablename__ = "outbox_events"

    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING", index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_error: Mapped[str | None] = mapped_column(String(1000))
