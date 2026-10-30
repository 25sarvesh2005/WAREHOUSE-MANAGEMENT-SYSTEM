"""Retention cleanup for accepted inbound webhook delivery IDs."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.webhook_model import InboundWebhookReceipt


async def prune_inbound_webhook_receipts(
    session: AsyncSession,
    *,
    retention_days: int = 7,
) -> int:
    """Delete delivery IDs older than the replay protection retention window."""
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    result = await session.execute(
        delete(InboundWebhookReceipt).where(InboundWebhookReceipt.received_at < cutoff)
    )
    return result.rowcount or 0
