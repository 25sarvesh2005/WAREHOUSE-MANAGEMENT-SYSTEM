"""
Database persistence operations for transactional outbox records.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import or_, select, update
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
        # Each worker owns the rows it returns until its surrounding
        # transaction commits. Workers can therefore poll concurrently without
        # dispatching the same event at the same time.
        .with_for_update(skip_locked=True)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def claim_pending_events(
    session: AsyncSession,
    *,
    limit: int,
    max_attempts: int,
    lease_duration: timedelta,
) -> tuple[list[OutboxEvent], int]:
    """Claim ready events and dead-letter exhausted events in the current transaction."""
    now = datetime.now(UTC)
    ready = or_(
        OutboxEvent.status == "PENDING",
        (OutboxEvent.status == "FAILED")
        & OutboxEvent.next_attempt_at.is_not(None)
        & (OutboxEvent.next_attempt_at <= now),
        (OutboxEvent.status == "PROCESSING")
        & OutboxEvent.lease_expires_at.is_not(None)
        & (OutboxEvent.lease_expires_at <= now),
    )
    result = await session.execute(
        select(OutboxEvent)
        .where(ready)
        .order_by(OutboxEvent.created_at.asc())
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    candidates = list(result.scalars().all())
    claimed: list[OutboxEvent] = []
    dead_letter_count = 0

    for event in candidates:
        if event.attempts >= max_attempts:
            event.status = "DEAD_LETTER"
            event.last_error = f"Exceeded maximum retry attempts ({max_attempts})"
            event.next_attempt_at = None
            event.claim_token = None
            event.lease_expires_at = None
            dead_letter_count += 1
            continue

        event.status = "PROCESSING"
        event.attempts += 1
        event.claim_token = uuid4()
        event.lease_expires_at = now + lease_duration
        claimed.append(event)

    await session.flush()
    return claimed, dead_letter_count


async def finish_claimed_event(
    session: AsyncSession,
    *,
    event_id: UUID,
    claim_token: UUID,
    status: str,
    error: str | None = None,
    next_attempt_at: datetime | None = None,
) -> bool:
    """Finish an event only if this worker still owns its dispatch lease."""
    result = await session.execute(
        update(OutboxEvent)
        .where(
            OutboxEvent.id == event_id,
            OutboxEvent.status == "PROCESSING",
            OutboxEvent.claim_token == claim_token,
        )
        .values(
            status=status,
            last_error=error[:1000] if error else None,
            next_attempt_at=next_attempt_at,
            claim_token=None,
            lease_expires_at=None,
            updated_at=datetime.now(UTC),
        )
    )
    return (result.rowcount or 0) == 1


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
