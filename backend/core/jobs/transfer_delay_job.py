"""
Background job detecting delayed in-transit inventory transfers and emitting alert events.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.logger import get_logger
from core.constants import OutboxEventType, TransferStatus
from core.cruds import outbox_crud
from core.models.transfer_model import Transfer

logger = get_logger(__name__)


async def check_delayed_transfers(
    session: AsyncSession,
    *,
    max_transit_days: int = 7,
) -> dict[str, Any]:
    """
    Scan for transfers in DISPATCHED status exceeding expected transit time SLA.

    Emits TRANSFER_DELAY_ALERT outbox events for warehouse ops escalation.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        max_transit_days: Maximum expected transit duration in days (default 7).

    Returns:
        dict[str, Any]: Summary containing delayed count and emitted alert count.
    """
    now = datetime.now(UTC)
    cutoff = now - timedelta(days=max_transit_days)
    logger.info(
        "Scanning for delayed transfers dispatched before %s (cutoff=%dd)",
        cutoff.isoformat(),
        max_transit_days,
    )

    stmt = (
        select(Transfer)
        .where(
            Transfer.status == TransferStatus.DISPATCHED.value,
            Transfer.dispatched_at.is_not(None),
            Transfer.dispatched_at <= cutoff,
        )
        .order_by(Transfer.dispatched_at.asc())
    )

    result = await session.execute(stmt)
    delayed_transfers = list(result.scalars().all())

    alerts_emitted = 0
    for transfer in delayed_transfers:
        dispatched_time = transfer.dispatched_at or transfer.created_at
        transit_days = round((now - dispatched_time).total_seconds() / 86400.0, 1)
        await outbox_crud.create_outbox_event(
            session,
            event_type=OutboxEventType.TRANSFER_DELAY_ALERT.value,
            payload={
                "transfer_id": str(transfer.id),
                "transfer_number": transfer.transfer_number,
                "seller_id": str(transfer.seller_id),
                "origin_warehouse_id": str(transfer.origin_warehouse_id),
                "destination_warehouse_id": str(transfer.destination_warehouse_id),
                "dispatched_at": dispatched_time.isoformat(),
                "transit_days": transit_days,
                "max_transit_days": max_transit_days,
            },
        )
        alerts_emitted += 1

    logger.info(
        "Delayed transfers check complete: found %d delayed transfers, emitted %d alerts",
        len(delayed_transfers),
        alerts_emitted,
    )
    return {
        "delayed_transfers_found": len(delayed_transfers),
        "alerts_emitted": alerts_emitted,
    }
