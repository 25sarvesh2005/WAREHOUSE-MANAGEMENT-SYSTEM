"""
Outbound HTTP webhook dispatch service with HMAC signing and delivery auditing.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from common.logger import get_logger
from common.pinned_webhook_transport import PinnedWebhookTransport
from common.webhook_signer import compute_webhook_signature
from common.webhook_url import ensure_public_https_url
from core.cruds import webhook_crud
from core.models.outbox_model import OutboxEvent
from core.models.webhook_model import WebhookSubscription

logger = get_logger(__name__)


@dataclass(frozen=True)
class WebhookDeliveryAttempt:
    subscription_id: UUID
    status_code: int | None
    response_body: str | None
    latency_ms: float
    error: str | None


@dataclass(frozen=True)
class WebhookDispatchResult:
    attempts: list[WebhookDeliveryAttempt]
    success_count: int
    failure_count: int


async def get_matching_webhook_subscriptions(
    event: OutboxEvent,
    session: AsyncSession,
) -> list[WebhookSubscription]:
    tenant_id = (
        event.payload.get("seller_tenant_id")
        or event.payload.get("seller_id")
        or event.payload.get("tenant_id")
    )
    return await webhook_crud.get_active_subscriptions_for_event(
        session,
        event.event_type,
        # Events without a seller are global-only; they must not fan out to
        # every seller-specific subscription.
        tenant_id=str(tenant_id) if tenant_id is not None else "GLOBAL",
    )


async def send_webhook_event(
    event: OutboxEvent,
    subscriptions: list[WebhookSubscription],
) -> WebhookDispatchResult:
    """Send an event to its subscriptions without holding a database session."""
    if not subscriptions:
        return WebhookDispatchResult([], success_count=0, failure_count=0)

    envelope = {
        "event_id": str(event.id),
        "event_type": event.event_type,
        "timestamp": datetime.now(UTC).isoformat(),
        "payload": event.payload,
    }
    raw_body = json.dumps(envelope, default=str).encode("utf-8")
    now_ts = str(int(time.time()))
    attempts: list[WebhookDeliveryAttempt] = []
    success_count = 0
    failure_count = 0

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
            destination = await ensure_public_https_url(sub.url)
            transport = PinnedWebhookTransport(destination)
            async with httpx.AsyncClient(
                transport=transport,
                timeout=5.0,
                follow_redirects=False,
                trust_env=False,
            ) as client:
                response = await client.post(sub.url, content=raw_body, headers=headers)
            status_code = response.status_code
            response_text = response.text[:500]
            if 200 <= status_code < 300:
                success_count += 1
            else:
                failure_count += 1
                error_message = f"Remote returned HTTP {status_code}"
        except Exception as exc:
            failure_count += 1
            error_message = f"Delivery failed: {exc}"

        attempts.append(
            WebhookDeliveryAttempt(
                subscription_id=sub.id,
                status_code=status_code,
                response_body=response_text,
                latency_ms=(time.perf_counter() - start_time) * 1000.0,
                error=error_message,
            )
        )

    return WebhookDispatchResult(attempts, success_count, failure_count)


async def record_webhook_attempts(
    event: OutboxEvent,
    attempts: list[WebhookDeliveryAttempt],
    session: AsyncSession,
    *,
    attempt_number: int | None = None,
) -> None:
    for attempt in attempts:
        await webhook_crud.record_delivery(
            session,
            subscription_id=attempt.subscription_id,
            outbox_event_id=event.id,
            event_type=event.event_type,
            payload=event.payload,
            status_code=attempt.status_code,
            response_body=attempt.response_body,
            latency_ms=attempt.latency_ms,
            attempt_number=attempt_number or event.attempts + 1,
            error=attempt.error,
        )


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
    subscriptions = await get_matching_webhook_subscriptions(event, session)
    if not subscriptions:
        logger.debug("No active webhook subscriptions match event '%s'", event.event_type)
        return 0
    dispatch_result = await send_webhook_event(event, subscriptions)
    await record_webhook_attempts(event, dispatch_result.attempts, session)

    logger.info(
        "Dispatched event %s (%s) to %d webhook(s): %d ok, %d failed",
        event.id,
        event.event_type,
        len(subscriptions),
        dispatch_result.success_count,
        dispatch_result.failure_count,
    )

    if dispatch_result.failure_count > 0 and dispatch_result.success_count == 0:
        raise RuntimeError(
            f"All {dispatch_result.failure_count} webhook deliveries failed for event {event.id}"
        )

    return dispatch_result.success_count

