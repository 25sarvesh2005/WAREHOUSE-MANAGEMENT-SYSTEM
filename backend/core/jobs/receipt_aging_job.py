"""
Background job detecting overdue receiving receipts and emitting alerting events.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from common.logger import get_logger
from core.constants import OutboxEventType, ReceiptStatus
from core.cruds import outbox_crud
from core.models.receiving_model import Receipt

logger = get_logger(__name__)


async def check_aging_receipts(
    session: AsyncSession,
    *,
    threshold_hours: int = 48,
) -> dict[str, Any]:
    """
    Scan for receiving receipts in DRAFT/IN_PROGRESS status exceeding age SLA threshold.

    Emits RECEIPT_AGING_ALERT outbox events for operational triage.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        threshold_hours: Inbound processing SLA in hours (default 48).

    Returns:
        dict[str, Any]: Summary containing aging count and emitted alert count.
    """
    now = datetime.now(UTC)
    cutoff = now - timedelta(hours=threshold_hours)
    logger.info("Scanning for aging receipts created before %s (cutoff=%dh)", cutoff.isoformat(), threshold_hours)

    stmt = (
        select(Receipt)
        .where(
            Receipt.status.in_(
                [
                    ReceiptStatus.DRAFT.value,
                    ReceiptStatus.IN_PROGRESS.value,
                    ReceiptStatus.PENDING_REVIEW.value,
                ]
            ),
            Receipt.created_at <= cutoff,
        )
        .order_by(Receipt.created_at.asc())
    )

    result = await session.execute(stmt)
    aging_receipts = list(result.scalars().all())

    alerts_emitted = 0
    for receipt in aging_receipts:
        age_hours = round((now - receipt.created_at).total_seconds() / 3600.0, 1)
        await outbox_crud.create_outbox_event(
            session,
            event_type=OutboxEventType.RECEIPT_AGING_ALERT.value,
            payload={
                "receipt_id": str(receipt.id),
                "receipt_number": receipt.receipt_number,
                "seller_id": str(receipt.seller_id),
                "warehouse_id": str(receipt.warehouse_id),
                "status": receipt.status,
                "created_at": receipt.created_at.isoformat(),
                "age_hours": age_hours,
                "threshold_hours": threshold_hours,
            },
        )
        alerts_emitted += 1

    logger.info(
        "Aging receipts check complete: found %d aging receipts, emitted %d alerts",
        len(aging_receipts),
        alerts_emitted,
    )
    return {
        "aging_receipts_found": len(aging_receipts),
        "alerts_emitted": alerts_emitted,
    }
