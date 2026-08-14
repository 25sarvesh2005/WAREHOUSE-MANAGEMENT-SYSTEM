"""
--------------------------------------------------------------------------------
File        : core/cruds/reporting_crud.py
Purpose     : Async reporting read-model queries for dashboards and reports.

Responsibilities:
    - Aggregate dashboard quantities and queue counts.
    - Keep SQLAlchemy query construction out of controllers.
    - Return plain Python values for controller response composition.

Flow:
    ReportingController -> reporting_crud -> AsyncSession -> PostgreSQL

Used By:
    - core/controllers/reporting_controller.py

Returns:
    Dictionaries and scalar counts for reporting read models.

Raises:
    Does NOT raise HTTPException. SQLAlchemy exceptions propagate to controllers.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.logger import get_logger
from core.models.fulfillment_model import PickTask
from core.models.inventory_model import InventoryBalance
from core.models.receiving_model import Receipt
from core.models.return_model import Return
from core.models.transfer_model import Transfer

logger = get_logger(__name__)


async def get_balance_totals_by_state(
    session: AsyncSession,
    *,
    warehouse_id: UUID | None = None,
) -> dict[str, float]:
    """
    Aggregate inventory balance quantity by state.

    Args:
        session: Active async database session.
        warehouse_id: Optional warehouse filter.

    Returns:
        dict[str, float]: Total quantity by inventory state.
    """
    statement = select(
        InventoryBalance.inventory_state,
        func.sum(InventoryBalance.quantity).label("total_quantity"),
    ).group_by(InventoryBalance.inventory_state)

    if warehouse_id is not None:
        statement = statement.where(InventoryBalance.warehouse_id == warehouse_id)

    result = await session.execute(statement)
    return {row.inventory_state: float(row.total_quantity) for row in result.all()}


async def count_receipts_by_statuses(
    session: AsyncSession,
    *,
    statuses: Sequence[str],
    warehouse_id: UUID | None = None,
) -> int:
    """
    Count receipts in a status set.

    Args:
        session: Active async database session.
        statuses: Receipt statuses to count.
        warehouse_id: Optional warehouse filter.

    Returns:
        int: Matching receipt count.
    """
    statement = select(func.count(Receipt.id)).where(Receipt.status.in_(statuses))
    if warehouse_id is not None:
        statement = statement.where(Receipt.warehouse_id == warehouse_id)
    return int((await session.execute(statement)).scalar_one_or_none() or 0)


async def count_pick_tasks_by_statuses(
    session: AsyncSession,
    *,
    statuses: Sequence[str],
    warehouse_id: UUID | None = None,
) -> int:
    """
    Count pick tasks in a status set.

    Args:
        session: Active async database session.
        statuses: Pick task statuses to count.
        warehouse_id: Optional warehouse filter.

    Returns:
        int: Matching pick task count.
    """
    statement = select(func.count(PickTask.id)).where(PickTask.status.in_(statuses))
    if warehouse_id is not None:
        statement = statement.where(PickTask.warehouse_id == warehouse_id)
    return int((await session.execute(statement)).scalar_one_or_none() or 0)


async def count_transfers_by_statuses(
    session: AsyncSession,
    *,
    statuses: Sequence[str],
    warehouse_id: UUID | None = None,
) -> int:
    """
    Count transfers in a status set.

    Args:
        session: Active async database session.
        statuses: Transfer statuses to count.
        warehouse_id: Optional origin or destination warehouse filter.

    Returns:
        int: Matching transfer count.
    """
    statement = select(func.count(Transfer.id)).where(Transfer.status.in_(statuses))
    if warehouse_id is not None:
        statement = statement.where(
            (Transfer.origin_warehouse_id == warehouse_id)
            | (Transfer.destination_warehouse_id == warehouse_id)
        )
    return int((await session.execute(statement)).scalar_one_or_none() or 0)


async def count_returns_by_statuses(
    session: AsyncSession,
    *,
    statuses: Sequence[str],
    warehouse_id: UUID | None = None,
) -> int:
    """
    Count returns in a status set.

    Args:
        session: Active async database session.
        statuses: Return statuses to count.
        warehouse_id: Optional warehouse filter.

    Returns:
        int: Matching return count.
    """
    statement = select(func.count(Return.id)).where(Return.status.in_(statuses))
    if warehouse_id is not None:
        statement = statement.where(Return.warehouse_id == warehouse_id)
    return int((await session.execute(statement)).scalar_one_or_none() or 0)
