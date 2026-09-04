"""
Transfer CRUD.

Database queries and transaction-scoped operations for inventory transfers.

Rules:
    - Receive AsyncSession as the first parameter.
    - Never raise HTTPException.
"""

from decimal import Decimal
from typing import Sequence
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from common.logger import get_logger
from core.models.transfer_model import Transfer, TransferLine

logger = get_logger(__name__)


async def create_transfer(
    session: AsyncSession,
    *,
    transfer_number: str,
    seller_id: UUID,
    origin_warehouse_id: UUID,
    destination_warehouse_id: UUID,
    created_by_user_id: UUID,
    status: str,
    notes: str | None = None,
    lines_data: list[dict],
) -> Transfer:
    """
    Create a new transfer header and associated line items.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        transfer_number: Unique transfer reference code.
        seller_id: Seller UUID.
        origin_warehouse_id: Dispatching warehouse UUID.
        destination_warehouse_id: Receiving warehouse UUID.
        created_by_user_id: User UUID creating transfer.
        status: Initial transfer status string.
        notes: Optional transfer notes.
        lines_data: List of line item dicts (product_id, requested_quantity, notes).

    Returns:
        Transfer: Newly created transfer instance with lines populated.
    """
    logger.info(
        "Creating transfer %s from wh %s to wh %s for seller %s",
        transfer_number,
        origin_warehouse_id,
        destination_warehouse_id,
        seller_id,
    )
    transfer = Transfer(
        transfer_number=transfer_number,
        seller_id=seller_id,
        origin_warehouse_id=origin_warehouse_id,
        destination_warehouse_id=destination_warehouse_id,
        created_by_user_id=created_by_user_id,
        status=status,
        notes=notes,
    )
    session.add(transfer)
    await session.flush()

    for item in lines_data:
        line = TransferLine(
            transfer_id=transfer.id,
            product_id=item["product_id"],
            requested_quantity=Decimal(str(item["requested_quantity"])),
            notes=item.get("notes"),
        )
        session.add(line)

    await session.flush()
    await session.refresh(transfer)
    return transfer


async def get_transfer_by_id(session: AsyncSession, transfer_id: UUID) -> Transfer | None:
    """
    Retrieve transfer by primary key with preloaded lines.

    Args:
        session: Active transaction session.
        transfer_id: Transfer UUID.

    Returns:
        Transfer | None: Transfer entity if found, else None.
    """
    stmt = (
        select(Transfer)
        .options(selectinload(Transfer.lines))
        .where(Transfer.id == transfer_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_transfers(
    session: AsyncSession,
    *,
    q: str | None = None,
    seller_id: UUID | None = None,
    seller_ids: Sequence[UUID] | None = None,
    origin_warehouse_id: UUID | None = None,
    destination_warehouse_id: UUID | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[Sequence[Transfer], int]:
    """
    List transfers with text search, filtering, and pagination.

    Applies identical filtering and search predicates to item and count queries.

    Args:
        session: Active session.
        q: Optional text search string matching transfer_number or notes.
        seller_id: Optional seller filter.
        seller_ids: Optional seller scope filter.
        origin_warehouse_id: Optional origin warehouse filter.
        destination_warehouse_id: Optional destination warehouse filter.
        status: Optional status filter.
        limit: Max records.
        offset: Offset records.

    Returns:
        tuple[Sequence[Transfer], int]: (transfers, total_count)
    """
    logger.info("Executing transfer_crud.list_transfers")
    stmt = select(Transfer).options(selectinload(Transfer.lines))
    count_stmt = select(func.count(Transfer.id))

    if q and q.strip():
        trimmed_q = q.strip()
        escaped_q = trimmed_q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        search_pattern = f"%{escaped_q}%"
        search_predicate = or_(
            Transfer.transfer_number.ilike(search_pattern, escape="\\"),
            Transfer.notes.ilike(search_pattern, escape="\\"),
        )
        stmt = stmt.where(search_predicate)
        count_stmt = count_stmt.where(search_predicate)

    if seller_id is not None:
        stmt = stmt.where(Transfer.seller_id == seller_id)
        count_stmt = count_stmt.where(Transfer.seller_id == seller_id)
    elif seller_ids is not None:
        stmt = stmt.where(Transfer.seller_id.in_(seller_ids))
        count_stmt = count_stmt.where(Transfer.seller_id.in_(seller_ids))
    if origin_warehouse_id is not None:
        stmt = stmt.where(Transfer.origin_warehouse_id == origin_warehouse_id)
        count_stmt = count_stmt.where(Transfer.origin_warehouse_id == origin_warehouse_id)
    if destination_warehouse_id is not None:
        stmt = stmt.where(Transfer.destination_warehouse_id == destination_warehouse_id)
        count_stmt = count_stmt.where(
            Transfer.destination_warehouse_id == destination_warehouse_id
        )
    if status is not None:
        stmt = stmt.where(Transfer.status == status)
        count_stmt = count_stmt.where(Transfer.status == status)

    stmt = stmt.order_by(Transfer.created_at.desc()).limit(limit).offset(offset)

    count_res = await session.execute(count_stmt)
    total = count_res.scalar() or 0

    res = await session.execute(stmt)
    transfers = res.scalars().all()

    return transfers, total
