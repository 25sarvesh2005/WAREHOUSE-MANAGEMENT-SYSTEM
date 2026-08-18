"""
Background job detecting uninspected received returns and emitting alert events.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.logger import get_logger
from core.constants import OutboxEventType, ReturnStatus
from core.cruds import outbox_crud
from core.models.return_model import Return

logger = get_logger(__name__)


async def check_aging_returns(
    session: AsyncSession,
    *,
    threshold_hours: int = 24,
) -> dict[str, Any]:
    """
    Scan for returns in RECEIVED or INSPECTION status exceeding inspection SLA threshold.

    Emits RETURN_AGING_ALERT outbox events for warehouse quality manager escalation.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        threshold_hours: Return inspection SLA in hours (default 24).

    Returns:
        dict[str, Any]: Summary containing aging count and emitted alert count.
    """
    now = datetime.now(UTC)
    cutoff = now - timedelta(hours=threshold_hours)
    logger.info(
        "Scanning for uninspected aging returns received before %s (cutoff=%dh)",
        cutoff.isoformat(),
        threshold_hours,
    )

    stmt = (
        select(Return)
        .where(
            Return.status.in_([ReturnStatus.RECEIVED.value, ReturnStatus.INSPECTION.value]),
            Return.received_at.is_not(None),
            Return.received_at <= cutoff,
        )
        .order_by(Return.received_at.asc())
    )

    result = await session.execute(stmt)
    aging_returns = list(result.scalars().all())

    alerts_emitted = 0
    for ret in aging_returns:
        rcv_time = ret.received_at or ret.created_at
        age_hours = round((now - rcv_time).total_seconds() / 3600.0, 1)
        await outbox_crud.create_outbox_event(
            session,
            event_type=OutboxEventType.RETURN_AGING_ALERT.value,
            payload={
                "return_id": str(ret.id),
                "return_number": ret.return_number,
                "seller_id": str(ret.seller_id),
                "warehouse_id": str(ret.warehouse_id),
                "status": ret.status,
                "received_at": rcv_time.isoformat(),
                "age_hours": age_hours,
                "threshold_hours": threshold_hours,
            },
        )
        alerts_emitted += 1

    logger.info(
        "Aging returns check complete: found %d aging returns, emitted %d alerts",
        len(aging_returns),
        alerts_emitted,
    )
    return {
        "aging_returns_found": len(aging_returns),
        "alerts_emitted": alerts_emitted,
    }
