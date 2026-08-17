"""
Database persistence operations for audit trail records.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from common.logger import get_logger
from core.models.audit_model import AuditEvent

logger = get_logger(__name__)


async def create_audit_event(
    session: AsyncSession,
    *,
    actor_user_id: UUID | None,
    action_type: str,
    source_record_type: str,
    source_record_id: UUID | None,
    reason: str | None = None,
    metadata_json: dict[str, object] | None = None,
) -> AuditEvent:
    """
    Create an audit trail record.

    The event is inserted into the caller's transaction so audit evidence commits
    or rolls back atomically with the business change.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        actor_user_id: User ID that performed the action, if known.
        action_type: Domain action category.
        source_record_type: Type of record changed.
        source_record_id: ID of the source record, if available.
        reason: Optional human-supplied reason.
        metadata_json: Safe structured metadata.

    Returns:
        AuditEvent: Persisted audit event model.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the insert fails.
    """
    logger.debug("Creating audit event %s for %s", action_type, source_record_type)
    event = AuditEvent(
        actor_user_id=actor_user_id,
        action_type=action_type,
        source_record_type=source_record_type,
        source_record_id=source_record_id,
        reason=reason,
        metadata_json=metadata_json or {},
    )
    session.add(event)
    await session.flush()
    return event
