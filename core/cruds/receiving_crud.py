"""
--------------------------------------------------------------------------------
File        : core/cruds/receiving_crud.py
Purpose     : Perform database operations for receiving receipts, lines, and events.

Responsibilities:
    - Persist receiving receipt drafts, line items, and audit events.
    - Read receipts by ID, client draft ID, or source reference.
    - Check for duplicate completed receipts.
    - Update receipt status and lines upon completion or cancellation.

Flow:
    ReceivingController -> CRUD functions receive AsyncSession -> Execute SQLAlchemy query

Used By:
    - core/controllers/receiving_controller.py

Returns:
    CRUD functions -> Model instances or collections.

Raises:
    sqlalchemy.exc.SQLAlchemyError: On database failures.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from common.logger import get_logger
from core.models.receiving_model import Receipt, ReceiptEvent, ReceiptLine

logger = get_logger(__name__)


def generate_receipt_number() -> str:
    """
    Generate a human-readable receipt number.

    Format: RCV-YYYYMMDD-XXXX where XXXX is a hex token.

    Returns:
        str: Receipt number string.

    Raises:
        None.
    """
    today = datetime.now(UTC).strftime("%Y%m%d")
    suffix = secrets.token_hex(2).upper()
    return f"RCV-{today}-{suffix}"


async def create_receipt(session: AsyncSession, receipt: Receipt) -> Receipt:
    """
    Persist a new receipt record.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        receipt: Unsaved Receipt model.

    Returns:
        Receipt: Persisted receipt model.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If insert fails.
    """
    logger.debug("Creating receipt %s", receipt.receipt_number)
    session.add(receipt)
    await session.flush()
    await session.refresh(receipt)
    return receipt


async def get_receipt_by_id(session: AsyncSession, receipt_id: UUID) -> Receipt | None:
    """
    Fetch a receipt by unique ID with preloaded lines and events.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        receipt_id: Receipt UUID.

    Returns:
        Receipt | None: Matching receipt or None.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If query fails.
    """
    logger.debug("Reading receipt by id %s", receipt_id)
    stmt = (
        select(Receipt)
        .options(selectinload(Receipt.lines), selectinload(Receipt.events))
        .where(Receipt.id == receipt_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_receipt_by_client_draft_id(
    session: AsyncSession,
    client_draft_id: str,
) -> Receipt | None:
    """
    Read a receipt by offline client_draft_id for idempotent draft sync.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        client_draft_id: Unique client draft identifier.

    Returns:
        Receipt | None: Matching receipt or None.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If query fails.
    """
    logger.debug("Reading receipt by client_draft_id %s", client_draft_id)
    stmt = (
        select(Receipt)
        .options(selectinload(Receipt.lines), selectinload(Receipt.events))
        .where(Receipt.client_draft_id == client_draft_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def find_existing_completed_receipt(
    session: AsyncSession,
    *,
    warehouse_id: UUID,
    source_type: str,
    source_reference: str,
) -> Receipt | None:
    """
    Find an existing COMPLETED receipt with matching warehouse and source reference.

    Used by duplicate prevention checks before creating or completing a receipt.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        warehouse_id: Warehouse UUID.
        source_type: Source type (e.g. CARRIER_TRACKING).
        source_reference: Normalized source reference (e.g. tracking number).

    Returns:
        Receipt | None: Matching completed receipt or None.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If query fails.
    """
    stmt = select(Receipt).where(
        Receipt.warehouse_id == warehouse_id,
        Receipt.source_type == source_type,
        Receipt.source_reference == source_reference,
        Receipt.status == "COMPLETED",
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_receipts(
    session: AsyncSession,
    *,
    seller_id: UUID | None = None,
    seller_ids: Sequence[UUID] | None = None,
    warehouse_id: UUID | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[Receipt]:
    """
    Query receipt headers with optional filters.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        seller_id: Optional seller filter.
        seller_ids: Optional seller scope filter.
        warehouse_id: Optional warehouse filter.
        status: Optional receipt status filter.
        limit: Page size.
        offset: Offset.

    Returns:
        Sequence[Receipt]: Matching receipts.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If query fails.
    """
    logger.debug("Listing receipts limit=%s offset=%s", limit, offset)
    stmt = (
        select(Receipt)
        .options(selectinload(Receipt.lines))
        .order_by(Receipt.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if seller_id is not None:
        stmt = stmt.where(Receipt.seller_id == seller_id)
    elif seller_ids is not None:
        stmt = stmt.where(Receipt.seller_id.in_(seller_ids))
    if warehouse_id is not None:
        stmt = stmt.where(Receipt.warehouse_id == warehouse_id)
    if status is not None:
        stmt = stmt.where(Receipt.status == status)

    result = await session.execute(stmt)
    return result.scalars().all()


async def upsert_receipt_line(
    session: AsyncSession,
    line: ReceiptLine,
) -> ReceiptLine:
    """
    Add or update a line item on a receipt.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        line: ReceiptLine model to persist.

    Returns:
        ReceiptLine: Persisted line item.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If persistence fails.
    """
    logger.debug("Upserting line for receipt %s product %s", line.receipt_id, line.product_id)
    session.add(line)
    await session.flush()
    await session.refresh(line)
    return line


async def add_receipt_event(
    session: AsyncSession,
    event: ReceiptEvent,
) -> ReceiptEvent:
    """
    Append an event to a receipt's audit trail.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        event: Unsaved ReceiptEvent model.

    Returns:
        ReceiptEvent: Persisted event record.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If insert fails.
    """
    logger.debug("Adding event %s for receipt %s", event.event_type, event.receipt_id)
    session.add(event)
    await session.flush()
    await session.refresh(event)
    return event
