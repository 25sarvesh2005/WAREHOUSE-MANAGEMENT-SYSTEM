"""
CRUD operations for webhook subscriptions and outbound delivery logs.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.webhook_model import InboundWebhookReceipt, WebhookDelivery, WebhookSubscription


class DuplicateInboundWebhookDelivery(Exception):
    """Raised when an inbound integration reuses an already accepted delivery ID."""


async def create_subscription(
    session: AsyncSession,
    *,
    tenant_id: str = "GLOBAL",
    url: str,
    secret: str,
    event_types: list[str],
    description: str | None = None,
) -> WebhookSubscription:
    """Create a new webhook subscription destination."""
    sub = WebhookSubscription(
        tenant_id=tenant_id,
        url=url,
        secret=secret,
        event_types=event_types,
        description=description,
        status="ACTIVE",
    )
    session.add(sub)
    await session.flush()
    return sub


async def record_inbound_delivery(
    session: AsyncSession,
    *,
    provider: str,
    delivery_id: str,
) -> None:
    """Claim an inbound delivery ID within the caller's transaction."""
    receipt = InboundWebhookReceipt(provider=provider, delivery_id=delivery_id)
    session.add(receipt)
    try:
        await session.flush()
    except Exception as error:
        # Unique constraint conflicts are the expected duplicate path. Raising
        # a domain exception lets the route return 409 after the transaction
        # context rolls back both the receipt and outbox writes.
        from sqlalchemy.exc import IntegrityError

        if isinstance(error, IntegrityError):
            raise DuplicateInboundWebhookDelivery from error
        raise


async def list_subscriptions(
    session: AsyncSession,
    *,
    tenant_id: str | None = None,
) -> list[WebhookSubscription]:
    """List webhook subscriptions filtered by tenant or all if None."""
    query = select(WebhookSubscription).order_by(desc(WebhookSubscription.created_at))
    if tenant_id and tenant_id != "ALL":
        query = query.where(
            (WebhookSubscription.tenant_id == tenant_id)
            | (WebhookSubscription.tenant_id == "GLOBAL")
        )
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_subscription(
    session: AsyncSession,
    subscription_id: UUID,
) -> WebhookSubscription | None:
    """Retrieve subscription by primary key."""
    result = await session.execute(
        select(WebhookSubscription).where(WebhookSubscription.id == subscription_id)
    )
    return result.scalar_one_or_none()


async def delete_subscription(
    session: AsyncSession,
    subscription_id: UUID,
) -> bool:
    """Delete a webhook subscription."""
    result = await session.execute(
        delete(WebhookSubscription).where(WebhookSubscription.id == subscription_id)
    )
    return (result.rowcount or 0) > 0


async def get_active_subscriptions_for_event(
    session: AsyncSession,
    event_type: str,
    *,
    tenant_id: str | None = None,
) -> list[WebhookSubscription]:
    """Retrieve matching global and tenant-specific subscriptions."""
    query = select(WebhookSubscription).where(WebhookSubscription.status == "ACTIVE")
    if tenant_id is not None:
        query = query.where(WebhookSubscription.tenant_id.in_(["GLOBAL", tenant_id]))
    result = await session.execute(query)
    subs = list(result.scalars().all())
    # Match specific event type or wildcard "*"
    return [s for s in subs if "*" in s.event_types or event_type in s.event_types]


async def record_delivery(
    session: AsyncSession,
    *,
    subscription_id: UUID,
    outbox_event_id: UUID | None = None,
    event_type: str,
    payload: dict[str, Any],
    status_code: int | None = None,
    response_body: str | None = None,
    latency_ms: float | None = None,
    attempt_number: int = 1,
    error: str | None = None,
) -> WebhookDelivery:
    """Record an audit trail entry for a dispatched webhook delivery attempt."""
    delivery = WebhookDelivery(
        subscription_id=subscription_id,
        outbox_event_id=outbox_event_id,
        event_type=event_type,
        payload=payload,
        status_code=status_code,
        response_body=response_body[:1000] if response_body else None,
        latency_ms=latency_ms,
        attempt_number=attempt_number,
        error=error[:1000] if error else None,
        delivered_at=datetime.now(UTC),
    )
    session.add(delivery)
    await session.flush()
    return delivery


async def list_deliveries(
    session: AsyncSession,
    *,
    subscription_id: UUID | None = None,
    limit: int = 50,
) -> list[WebhookDelivery]:
    """List recent webhook delivery attempts."""
    query = select(WebhookDelivery).order_by(desc(WebhookDelivery.delivered_at)).limit(limit)
    if subscription_id:
        query = query.where(WebhookDelivery.subscription_id == subscription_id)
    result = await session.execute(query)
    return list(result.scalars().all())

