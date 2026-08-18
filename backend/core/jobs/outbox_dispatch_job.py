"""
Background job dispatching pending transactional outbox events to downstream consumers.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Callable, Coroutine
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from common.logger import get_logger
from core.cruds import outbox_crud
from core.models.outbox_model import OutboxEvent

logger = get_logger(__name__)

# Type definition for event handler callbacks
EventHandler = Callable[[OutboxEvent], Coroutine[Any, Any, None]]
_EVENT_HANDLERS: dict[str, list[EventHandler]] = {}


def register_outbox_handler(event_type: str, handler: EventHandler) -> None:
    """Register a downstream handler callback for a specific outbox event type."""
    if event_type not in _EVENT_HANDLERS:
        _EVENT_HANDLERS[event_type] = []
    _EVENT_HANDLERS[event_type].append(handler)


async def dispatch_pending_outbox_events(
    session: AsyncSession,
    *,
    batch_size: int = 50,
    max_attempts: int = 5,
) -> dict[str, Any]:
    """
    Poll and dispatch pending or retry-ready outbox events.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        batch_size: Maximum events to process in one batch.
        max_attempts: Maximum attempts before marking as DEAD_LETTER.

    Returns:
        dict[str, Any]: Summary containing processed, dispatched, and failed counts.
    """
    now = datetime.now(UTC)
    events = await outbox_crud.fetch_pending_events(session, limit=batch_size)
    if not events:
        return {"processed": 0, "dispatched": 0, "failed": 0, "dead_letter": 0}

    logger.info("Found %d pending outbox events for dispatch", len(events))
    dispatched_count = 0
    failed_count = 0
    dead_letter_count = 0

    for event in events:
        # Check max attempts
        if event.attempts >= max_attempts:
            logger.warning(
                "Outbox event %s exceeded max attempts (%d); marking DEAD_LETTER",
                event.id,
                max_attempts,
            )
            event.status = "DEAD_LETTER"
            event.last_error = f"Exceeded maximum retry attempts ({max_attempts})"
            await session.flush()
            dead_letter_count += 1
            continue

        try:
            # Execute registered handlers if any exist
            handlers = _EVENT_HANDLERS.get(event.event_type, [])
            for handler in handlers:
                await handler(event)

            # Mark as dispatched
            await outbox_crud.mark_event_dispatched(session, event.id)
            dispatched_count += 1
            logger.debug("Successfully dispatched outbox event %s (%s)", event.id, event.event_type)

        except Exception as exc:
            failed_count += 1
            # Exponential backoff: min(3600, (2 ** attempts) * 10)
            backoff_seconds = min(3600, (2 ** (event.attempts + 1)) * 10)
            next_retry = now + timedelta(seconds=backoff_seconds)
            logger.error(
                "Failed to dispatch outbox event %s (%s): %s (retry in %ds)",
                event.id,
                event.event_type,
                exc,
                backoff_seconds,
                exc_info=True,
            )
            await outbox_crud.mark_event_failed(
                session,
                event.id,
                error=str(exc),
                next_attempt_at=next_retry,
            )

    return {
        "processed": len(events),
        "dispatched": dispatched_count,
        "failed": failed_count,
        "dead_letter": dead_letter_count,
    }
