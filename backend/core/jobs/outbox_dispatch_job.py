"""
Background job dispatching pending transactional outbox events to downstream consumers.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from datetime import UTC, datetime, timedelta
from typing import Any

from common.logger import get_logger
from core.constants import OutboxEventStatus
from core.cruds import outbox_crud
from core.database.database import transaction_session
from core.models.outbox_model import OutboxEvent
from core.services.webhook_dispatcher_service import (
    WebhookDispatchResult,
    get_matching_webhook_subscriptions,
    record_webhook_attempts,
    send_webhook_event,
)

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
    *,
    batch_size: int = 50,
    max_attempts: int = 5,
) -> dict[str, Any]:
    """
    Poll and dispatch pending or retry-ready outbox events.

    Args:
        batch_size: Maximum events to process in one batch.
        max_attempts: Maximum attempts before marking as DEAD_LETTER.

    Returns:
        dict[str, Any]: Summary containing processed, dispatched, and failed counts.
    """
    processed_count = 0
    dispatched_count = 0
    failed_count = 0
    dead_letter_count = 0

    for _ in range(batch_size):
        async with transaction_session() as session:
            events, newly_dead_lettered = await outbox_crud.claim_pending_events(
                session,
                limit=1,
                max_attempts=max_attempts,
                lease_duration=timedelta(minutes=10),
            )

        dead_letter_count += newly_dead_lettered
        processed_count += newly_dead_lettered
        if not events:
            if newly_dead_lettered:
                continue
            break

        event = events[0]
        claim_token = event.claim_token
        if claim_token is None:
            logger.error("Claimed outbox event %s has no claim token", event.id)
            continue

        dispatch_result: WebhookDispatchResult | None = None
        failure: Exception | None = None
        try:
            async with transaction_session() as session:
                subscriptions = await get_matching_webhook_subscriptions(event, session)

            dispatch_result = await send_webhook_event(event, subscriptions)
            if (
                dispatch_result.failure_count > 0
                and dispatch_result.success_count == 0
            ):
                raise RuntimeError(
                    "All webhook deliveries failed for event "
                    f"{event.id} ({dispatch_result.failure_count} destination(s))"
                )

            # Execute registered in-memory handlers if any exist
            handlers = _EVENT_HANDLERS.get(event.event_type, [])
            for handler in handlers:
                await handler(event)
        except Exception as exc:
            failure = exc
            backoff_seconds = min(3600, (2**event.attempts) * 10)
            logger.error(
                "Failed to dispatch outbox event %s (%s): %s (retry in %ds)",
                event.id,
                event.event_type,
                exc,
                backoff_seconds,
                exc_info=True,
            )
            next_retry = datetime.now(UTC) + timedelta(seconds=backoff_seconds)

        async with transaction_session() as session:
            if dispatch_result is not None:
                await record_webhook_attempts(
                    event,
                    dispatch_result.attempts,
                    session,
                    attempt_number=event.attempts,
                )
            updated = await outbox_crud.finish_claimed_event(
                session,
                event_id=event.id,
                claim_token=claim_token,
                status=(
                    OutboxEventStatus.FAILED.value
                    if failure is not None
                    else OutboxEventStatus.DISPATCHED.value
                ),
                error=str(failure) if failure is not None else None,
                next_attempt_at=next_retry if failure is not None else None,
            )
            if not updated:
                logger.warning(
                    "Outbox lease expired before event %s could be finalized",
                    event.id,
                )
                continue

        processed_count += 1
        if failure is None:
            dispatched_count += 1
            logger.debug("Successfully dispatched outbox event %s (%s)", event.id, event.event_type)
        else:
            failed_count += 1

    return {
        "processed": processed_count,
        "dispatched": dispatched_count,
        "failed": failed_count,
        "dead_letter": dead_letter_count,
    }
