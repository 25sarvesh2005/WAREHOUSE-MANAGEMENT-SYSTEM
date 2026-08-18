"""
Database persistence operations for transactional outbox records.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.logger import get_logger
from core.models.outbox_model import OutboxEvent

logger = get_logger(__name__)


async def create_outbox_event(
    session: AsyncSession,
    *,
    event_type: str,
    payload: dict[str, object],
    status: str = "PENDING",
) -> OutboxEvent:
    """
    Create a transactional outbox record.

    The event is inserted into the caller's transaction so outbox events commit
    or roll back atomically with the business changes.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        event_type: Domain event classification string or OutboxEventType value.
        payload: JSON-serializable event payload dictionary.
        status: Initial status (default "PENDING").

    Returns:
        OutboxEvent: Persisted outbox event model.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the insert fails.
    """
    logger.debug("Creating outbox event %s", event_type)
    event = OutboxEvent(
        event_type=event_type,
        payload=payload,
        status=status,
        attempts=0,
        next_attempt_at=None,
        last_error=None,
    )
    session.add(event)
    await session.flush()
    return event


async def fetch_pending_events(
    session: AsyncSession,
    limit: int = 50,
) -> list[OutboxEvent]:
    """
    Fetch pending or retry-ready outbox events for background dispatch.

    Selects events in PENDING status or FAILED status where next_attempt_at is due.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        limit: Maximum number of events to fetch.

    Returns:
        list[OutboxEvent]: Ordered list of events ready for dispatch.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the query fails.
    """
    now = datetime.now(UTC)
    stmt = (
        select(OutboxEvent)
        .where(
            or_(
                OutboxEvent.status == "PENDING",
                (OutboxEvent.status == "FAILED")
                & (OutboxEvent.next_attempt_at.is_not(None))
                & (OutboxEvent.next_attempt_at <= now),
            )
        )
        .order_by(OutboxEvent.created_at.asc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def mark_event_dispatched(
    session: AsyncSession,
    event_id: UUID,
) -> None:
    """
    Mark an outbox event as successfully dispatched.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        event_id: Target outbox event UUID.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the update fails.
    """
    event = await session.get(OutboxEvent, event_id)
    if event is not None:
        event.status = "DISPATCHED"
        event.attempts += 1
        event.last_error = None
        event.next_attempt_at = None
        await session.flush()


async def mark_event_failed(
    session: AsyncSession,
    event_id: UUID,
    error: str,
    next_attempt_at: datetime | None,
) -> None:
    """
    Mark an outbox event as failed with error details and scheduled retry time.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        event_id: Target outbox event UUID.
        error: Truncated error message or stack summary.
        next_attempt_at: When the event can next be attempted.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the update fails.
    """
    event = await session.get(OutboxEvent, event_id)
    if event is not None:
        event.status = "FAILED"
        event.attempts += 1
        event.last_error = error[:1000] if error else None
        event.next_attempt_at = next_attempt_at
        await session.flush()
