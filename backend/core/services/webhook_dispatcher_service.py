"""
Outbound HTTP webhook dispatch service with HMAC signing and delivery auditing.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
import time
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from common.logger import get_logger
from common.webhook_signer import compute_webhook_signature
from core.cruds import webhook_crud
from core.models.outbox_model import OutboxEvent

logger = get_logger(__name__)


async def dispatch_outbox_event_to_webhooks(
    event: OutboxEvent,
    session: AsyncSession,
) -> int:
    """
    Dispatch a transactional outbox event to all active matching webhook subscriptions.

    Args:
        event: Persisted OutboxEvent instance.
        session: Active database session.

    Returns:
        int: Number of successful deliveries.
    """
    subscriptions = await webhook_crud.get_active_subscriptions_for_event(
        session, event.event_type
    )
    if not subscriptions:
        logger.debug("No active webhook subscriptions match event '%s'", event.event_type)
        return 0

    envelope = {
        "event_id": str(event.id),
        "event_type": event.event_type,
        "timestamp": datetime.now(UTC).isoformat(),
        "payload": event.payload,
    }
    raw_body = json.dumps(envelope, default=str).encode("utf-8")
    now_ts = str(int(time.time()))

    success_count = 0
    failure_count = 0

    async with httpx.AsyncClient(timeout=5.0) as client:
        for sub in subscriptions:
            signature = compute_webhook_signature(raw_body, sub.secret)
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Whitfield-WMS-Webhook/1.0",
                "X-Whitfield-Event": event.event_type,
                "X-Whitfield-Signature": signature,
                "X-Whitfield-Timestamp": now_ts,
                "X-Whitfield-Delivery": str(event.id),
            }

            start_time = time.perf_counter()
            status_code: int | None = None
            response_text: str | None = None
            error_message: str | None = None

            try:
                response = await client.post(sub.url, content=raw_body, headers=headers)
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                status_code = response.status_code
                response_text = response.text[:500]

                if 200 <= response.status_code < 300:
                    success_count += 1
                else:
                    failure_count += 1
                    error_message = f"Remote returned HTTP {response.status_code}"
            except Exception as exc:
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                failure_count += 1
                error_message = f"Delivery failed: {exc}"

            await webhook_crud.record_delivery(
                session,
                subscription_id=sub.id,
                outbox_event_id=event.id,
                event_type=event.event_type,
                payload=event.payload,
                status_code=status_code,
                response_body=response_text,
                latency_ms=latency_ms,
                attempt_number=event.attempts + 1,
                error=error_message,
            )

    logger.info(
        "Dispatched event %s (%s) to %d webhook(s): %d ok, %d failed",
        event.id,
        event.event_type,
        len(subscriptions),
        success_count,
        failure_count,
    )

    if failure_count > 0 and success_count == 0:
        raise RuntimeError(f"All {failure_count} webhook deliveries failed for event {event.id}")

    return success_count

