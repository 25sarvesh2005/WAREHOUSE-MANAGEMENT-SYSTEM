"""
Return CRUD.

Database queries and transaction-scoped operations for customer / seller returns.

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
from core.models.return_model import Return, ReturnDisposition, ReturnLine

logger = get_logger(__name__)


async def create_return(
    session: AsyncSession,
    *,
    return_number: str,
    seller_id: UUID,
    warehouse_id: UUID,
    order_id: UUID | None = None,
    rma_number: str | None = None,
    inbound_tracking_number: str | None = None,
    status: str,
    notes: str | None = None,
    lines_data: list[dict],
) -> Return:
    """
    Create a new return header and line item records.

    Args:
        session: Active transaction session.
        return_number: Unique return identifier code.
        seller_id: Seller UUID.
        warehouse_id: Receiving warehouse UUID.
        order_id: Optional reference order UUID.
        rma_number: Optional RMA authorization reference.
        inbound_tracking_number: Inbound parcel tracking code.
        status: Initial return lifecycle status.
        notes: Optional comments.
        lines_data: List of line items (product_id, expected_quantity, reason_code).

    Returns:
        Return: Newly created return record with preloaded lines.
    """
    logger.info(
        "Creating return %s for seller %s at warehouse %s",
        return_number,
        seller_id,
        warehouse_id,
    )
    ret = Return(
        return_number=return_number,
        seller_id=seller_id,
        warehouse_id=warehouse_id,
        order_id=order_id,
        rma_number=rma_number,
        inbound_tracking_number=inbound_tracking_number,
        status=status,
        notes=notes,
    )
    session.add(ret)
    await session.flush()

    for item in lines_data:
        line = ReturnLine(
            return_id=ret.id,
            product_id=item.get("product_id"),
            expected_quantity=Decimal(str(item.get("expected_quantity", "0.00"))),
            received_quantity=Decimal(str(item.get("received_quantity", "0.00"))),
            reason_code=item.get("reason_code"),
            inspection_notes=item.get("inspection_notes"),
        )
        session.add(line)

    await session.flush()
    await session.refresh(ret)
    return ret


async def get_return_by_id(session: AsyncSession, return_id: UUID) -> Return | None:
    """
    Retrieve return by primary key with preloaded lines and dispositions.

    Args:
        session: Active session.
        return_id: Return UUID.

    Returns:
        Return | None: Return entity if found, else None.
    """
    stmt = (
        select(Return)
        .options(
            selectinload(Return.lines).selectinload(ReturnLine.dispositions)
        )
        .where(Return.id == return_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_returns(
    session: AsyncSession,
    *,
    q: str | None = None,
    seller_id: UUID | None = None,
    seller_ids: Sequence[UUID] | None = None,
    warehouse_id: UUID | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[Sequence[Return], int]:
    """
    List returns with text search, filtering, and pagination.

    Applies identical filtering and search predicates to item and count queries.

    Args:
        session: Active transaction session.
        q: Optional text search string matching return_number, rma_number, or inbound_tracking_number.
        seller_id: Optional seller filter.
        seller_ids: Optional seller scope filter.
        warehouse_id: Optional warehouse filter.
        status: Optional status filter.
        limit: Max pagination records.
        offset: Offset pagination records.

    Returns:
        tuple[Sequence[Return], int]: (returns, total_count)
    """
    logger.info("Executing return_crud.list_returns")
    stmt = select(Return).options(
        selectinload(Return.lines).selectinload(ReturnLine.dispositions)
    )
    count_stmt = select(func.count(Return.id))

    if q and q.strip():
        trimmed_q = q.strip()
        escaped_q = trimmed_q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        search_pattern = f"%{escaped_q}%"
        search_predicate = or_(
            Return.return_number.ilike(search_pattern, escape="\\"),
            Return.rma_number.ilike(search_pattern, escape="\\"),
            Return.inbound_tracking_number.ilike(search_pattern, escape="\\"),
        )
        stmt = stmt.where(search_predicate)
        count_stmt = count_stmt.where(search_predicate)

    if seller_id is not None:
        stmt = stmt.where(Return.seller_id == seller_id)
        count_stmt = count_stmt.where(Return.seller_id == seller_id)
    elif seller_ids is not None:
        stmt = stmt.where(Return.seller_id.in_(seller_ids))
        count_stmt = count_stmt.where(Return.seller_id.in_(seller_ids))
    if warehouse_id is not None:
        stmt = stmt.where(Return.warehouse_id == warehouse_id)
        count_stmt = count_stmt.where(Return.warehouse_id == warehouse_id)
    if status is not None:
        stmt = stmt.where(Return.status == status)
        count_stmt = count_stmt.where(Return.status == status)

    stmt = stmt.order_by(Return.created_at.desc()).limit(limit).offset(offset)

    count_res = await session.execute(count_stmt)
    total = count_res.scalar() or 0

    res = await session.execute(stmt)
    returns = res.scalars().all()

    return returns, total


async def create_return_disposition(
    session: AsyncSession,
    *,
    return_line_id: UUID,
    disposition_state: str,
    quantity: Decimal,
    destination_location_id: UUID | None = None,
    notes: str | None = None,
) -> ReturnDisposition:
    """
    Record inspection outcome disposition for a return line.

    Args:
        session: Active session.
        return_line_id: ReturnLine UUID.
        disposition_state: Target inventory bucket state.
        quantity: Quantity disposed.
        destination_location_id: Optional warehouse location UUID.
        notes: Optional inspection notes.

    Returns:
        ReturnDisposition: Created disposition record.
    """
    disp = ReturnDisposition(
        return_line_id=return_line_id,
        disposition_state=disposition_state,
        quantity=quantity,
        destination_location_id=destination_location_id,
        notes=notes,
    )
    session.add(disp)
    await session.flush()
    return disp
