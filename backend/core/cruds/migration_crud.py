"""
Database CRUD operations for import batches and staged opening inventory.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.logger import get_logger
from core.constants import (
    InventoryMovementType,
    MigrationBatchStatus,
    StagedRowValidationStatus,
)
from core.cruds import inventory_crud
from core.models.inventory_model import InventoryMovement
from core.models.migration_model import ImportBatch, StagedOpeningInventoryRow

logger = get_logger(__name__)


async def create_import_batch(
    session: AsyncSession,
    *,
    created_by_user_id: UUID,
    batch_number: str,
    source_notes: str | None = None,
) -> ImportBatch:
    """
    Create a new opening inventory import batch header.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        created_by_user_id: User UUID creating the batch.
        batch_number: Unique batch identifier string.
        source_notes: Optional notes or description.

    Returns:
        ImportBatch: Created import batch header.
    """
    logger.debug("Creating import batch number=%s user=%s", batch_number, created_by_user_id)
    batch = ImportBatch(
        batch_number=batch_number,
        status=MigrationBatchStatus.STAGED.value,
        source_notes=source_notes,
        created_by_user_id=created_by_user_id,
        total_rows=0,
        valid_rows=0,
        invalid_rows=0,
    )
    session.add(batch)
    await session.flush()
    await session.refresh(batch)
    return batch


async def get_import_batch_by_id(
    session: AsyncSession,
    batch_id: UUID,
    for_update: bool = False,
) -> ImportBatch | None:
    """
    Retrieve an import batch header by UUID.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        batch_id: Target batch UUID.
        for_update: If True, acquire row lock with SELECT FOR UPDATE.

    Returns:
        ImportBatch | None: Found import batch or None.
    """
    stmt = select(ImportBatch).where(ImportBatch.id == batch_id)
    if for_update:
        stmt = stmt.with_for_update()
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_import_batch_by_number(
    session: AsyncSession,
    batch_number: str,
) -> ImportBatch | None:
    """
    Retrieve an import batch header by batch number string.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        batch_number: Unique batch number.

    Returns:
        ImportBatch | None: Found import batch or None.
    """
    stmt = select(ImportBatch).where(ImportBatch.batch_number == batch_number)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_import_batches(
    session: AsyncSession,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[ImportBatch]:
    """
    List import batch headers ordered by creation time descending.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        limit: Page size.
        offset: Offset.

    Returns:
        Sequence[ImportBatch]: List of matching import batches.
    """
    stmt = (
        select(ImportBatch)
        .order_by(ImportBatch.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_staged_row_by_identity(
    session: AsyncSession,
    batch_id: UUID,
    workbook: str,
    sheet: str,
    row_number: int,
) -> StagedOpeningInventoryRow | None:
    """
    Find a staged row by its source identity key.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        batch_id: Import batch UUID.
        workbook: Source workbook name.
        sheet: Source sheet name.
        row_number: Source row number.

    Returns:
        StagedOpeningInventoryRow | None: Found row model or None.
    """
    stmt = select(StagedOpeningInventoryRow).where(
        StagedOpeningInventoryRow.import_batch_id == batch_id,
        StagedOpeningInventoryRow.source_workbook == workbook,
        StagedOpeningInventoryRow.source_sheet == sheet,
        StagedOpeningInventoryRow.source_row_number == row_number,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_staged_row_by_hash(
    session: AsyncSession,
    batch_id: UUID,
    source_hash: str,
) -> StagedOpeningInventoryRow | None:
    """
    Find a staged row by its source content hash.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        batch_id: Import batch UUID.
        source_hash: SHA-256 content hash.

    Returns:
        StagedOpeningInventoryRow | None: Found row model or None.
    """
    stmt = select(StagedOpeningInventoryRow).where(
        StagedOpeningInventoryRow.import_batch_id == batch_id,
        StagedOpeningInventoryRow.source_hash == source_hash,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def submit_staged_rows_bulk(
    session: AsyncSession,
    batch_id: UUID,
    rows_data: list[dict],
) -> list[StagedOpeningInventoryRow]:
    """
    Process and insert staged opening inventory rows with strict idempotency rules.

    Rules:
    - Same (batch_id, workbook, sheet, row_number) + same hash -> idempotent no-op.
    - Same source identity + different hash raises a conflict ValueError.
    - Same hash + different source identity raises a conflict ValueError.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        batch_id: Parent batch UUID.
        rows_data: List of raw row dicts.

    Returns:
        list[StagedOpeningInventoryRow]: All staged rows after submission.

    Raises:
        ValueError: When identity or content hash conflict is detected.
    """
    logger.debug("Submitting %s staged rows for batch=%s", len(rows_data), batch_id)

    processed_rows: list[StagedOpeningInventoryRow] = []

    for item in rows_data:
        workbook = item["source_workbook"]
        sheet = item["source_sheet"]
        row_number = item["source_row_number"]
        source_hash = item["source_hash"]

        existing_by_identity = await get_staged_row_by_identity(
            session, batch_id, workbook, sheet, row_number
        )
        existing_by_hash = await get_staged_row_by_hash(session, batch_id, source_hash)

        if existing_by_identity is not None:
            if existing_by_identity.source_hash == source_hash:
                # Idempotent re-submission of exact same row content
                processed_rows.append(existing_by_identity)
                continue
            else:
                # Same source row identity but different content -> 409 Conflict
                raise ValueError(
                    f"Conflict: Source row {workbook}/{sheet} line {row_number} "
                    "already staged with different content hash."
                )

        if existing_by_hash is not None:
            # Same content hash already exists for a different row identity -> 409 Conflict
            raise ValueError(
                f"Conflict: Content hash '{source_hash}' already staged under row "
                f"{existing_by_hash.source_workbook}/{existing_by_hash.source_sheet} "
                f"line {existing_by_hash.source_row_number}."
            )

        new_row = StagedOpeningInventoryRow(
            import_batch_id=batch_id,
            source_workbook=workbook,
            source_sheet=sheet,
            source_row_number=row_number,
            source_hash=source_hash,
            raw_seller_code=item.get("raw_seller_code"),
            raw_sku=item.get("raw_sku"),
            raw_upc=item.get("raw_upc"),
            raw_warehouse_code=item.get("raw_warehouse_code"),
            raw_location_code=item.get("raw_location_code"),
            raw_inventory_state=item.get("raw_inventory_state"),
            raw_quantity=item.get("raw_quantity"),
            validation_status=StagedRowValidationStatus.PENDING.value,
            validation_errors=[],
        )
        session.add(new_row)
        processed_rows.append(new_row)

    await session.flush()
    return processed_rows


async def get_staged_rows_by_batch(
    session: AsyncSession,
    batch_id: UUID,
    limit: int = 200,
    offset: int = 0,
) -> Sequence[StagedOpeningInventoryRow]:
    """
    Query staged opening inventory rows for a batch with pagination.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        batch_id: Parent batch UUID.
        limit: Page size.
        offset: Offset.

    Returns:
        Sequence[StagedOpeningInventoryRow]: Page of staged rows.
    """
    stmt = (
        select(StagedOpeningInventoryRow)
        .where(StagedOpeningInventoryRow.import_batch_id == batch_id)
        .order_by(StagedOpeningInventoryRow.source_row_number.asc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_all_staged_rows_by_batch(
    session: AsyncSession,
    batch_id: UUID,
) -> Sequence[StagedOpeningInventoryRow]:
    """
    Fetch all staged opening inventory rows for a batch.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        batch_id: Parent batch UUID.

    Returns:
        Sequence[StagedOpeningInventoryRow]: All staged rows in batch.
    """
    stmt = (
        select(StagedOpeningInventoryRow)
        .where(StagedOpeningInventoryRow.import_batch_id == batch_id)
        .order_by(StagedOpeningInventoryRow.source_row_number.asc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def update_staged_row_validation(
    session: AsyncSession,
    row: StagedOpeningInventoryRow,
    *,
    validation_status: str,
    validation_errors: list[dict],
    seller_id: UUID | None = None,
    product_id: UUID | None = None,
    warehouse_id: UUID | None = None,
    location_id: UUID | None = None,
    inventory_state: str | None = None,
    quantity: Decimal | None = None,
) -> StagedOpeningInventoryRow:
    """
    Update validation status, error list, and resolved FK fields on a staged row.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        row: StagedOpeningInventoryRow model to update.
        validation_status: Target validation status (VALID or INVALID).
        validation_errors: List of error details.
        seller_id: Resolved seller UUID or None.
        product_id: Resolved product UUID or None.
        warehouse_id: Resolved warehouse UUID or None.
        location_id: Resolved location UUID or None.
        inventory_state: Resolved inventory state or None.
        quantity: Resolved quantity or None.

    Returns:
        StagedOpeningInventoryRow: Updated row model.
    """
    row.validation_status = validation_status
    row.validation_errors = validation_errors
    row.seller_id = seller_id
    row.product_id = product_id
    row.warehouse_id = warehouse_id
    row.location_id = location_id
    row.inventory_state = inventory_state
    row.quantity = quantity

    await session.flush()
    return row


async def update_import_batch_counts(
    session: AsyncSession,
    batch: ImportBatch,
    *,
    status: str,
    total_rows: int,
    valid_rows: int,
    invalid_rows: int,
) -> ImportBatch:
    """
    Update validation status and counts on an import batch header.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        batch: ImportBatch header to update.
        status: Updated status string.
        total_rows: Total staged rows count.
        valid_rows: Valid rows count.
        invalid_rows: Invalid rows count.

    Returns:
        ImportBatch: Updated header model.
    """
    batch.status = status
    batch.total_rows = total_rows
    batch.valid_rows = valid_rows
    batch.invalid_rows = invalid_rows
    await session.flush()
    await session.refresh(batch)
    return batch


async def mark_batch_approved(
    session: AsyncSession,
    batch: ImportBatch,
    *,
    approved_by_user_id: UUID,
    approved_at: datetime,
) -> ImportBatch:
    """
    Mark an import batch as APPROVED with approver metadata.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        batch: Locked ImportBatch header.
        approved_by_user_id: User UUID approving the batch.
        approved_at: UTC timestamp of approval.

    Returns:
        ImportBatch: Updated batch model.
    """
    batch.status = MigrationBatchStatus.APPROVED.value
    batch.approved_by_user_id = approved_by_user_id
    batch.approved_at = approved_at
    await session.flush()
    await session.refresh(batch)
    return batch


async def apply_staged_rows_to_ledger(
    session: AsyncSession,
    batch: ImportBatch,
    staged_rows: Sequence[StagedOpeningInventoryRow],
    *,
    applied_by_user_id: UUID,
    applied_at: datetime,
) -> ImportBatch:
    """
    Apply valid staged rows to the movement ledger and balance projections.

    Each row creates an append-only InventoryMovement with type MIGRATION_OPENING_BALANCE.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        batch: Locked ImportBatch header model.
        staged_rows: List of valid staged rows for the batch.
        applied_by_user_id: User UUID applying the batch.
        applied_at: UTC application timestamp.

    Returns:
        ImportBatch: Updated batch model marked APPLIED.
    """
    logger.info("Applying import batch %s (%s valid rows)", batch.id, len(staged_rows))

    for row in staged_rows:
        if row.applied_movement_id is not None:
            # Skip rows already applied (idempotency check)
            continue
        if (
            row.seller_id is None
            or row.product_id is None
            or row.warehouse_id is None
            or row.inventory_state is None
            or row.quantity is None
        ):
            raise ValueError(f"Cannot apply un-resolved staged row id={row.id}")

        idempotency_key = f"migration_{batch.id}_{row.id}"

        movement = InventoryMovement(
            seller_id=row.seller_id,
            product_id=row.product_id,
            warehouse_id=row.warehouse_id,
            location_id=row.location_id,
            inventory_state=row.inventory_state,
            quantity_delta=row.quantity,
            movement_type=InventoryMovementType.MIGRATION_OPENING_BALANCE.value,
            source_type="MIGRATION_OPENING_INVENTORY",
            source_id=batch.id,
            source_line_id=row.id,
            idempotency_key=idempotency_key,
            reason_code="OPENING_BALANCE_MIGRATION",
            reason_text=(
                f"Opening balance import batch {batch.batch_number} row "
                f"{row.source_workbook}/{row.source_sheet}:{row.source_row_number}"
            ),
            actor_user_id=applied_by_user_id,
            occurred_at=applied_at,
            recorded_at=applied_at,
        )

        persisted_movement, _ = await inventory_crud.apply_movement(session, movement)
        row.applied_movement_id = persisted_movement.id

    batch.status = MigrationBatchStatus.APPLIED.value
    batch.applied_at = applied_at
    await session.flush()
    await session.refresh(batch)
    return batch


async def get_migration_movements_by_batch(
    session: AsyncSession,
    batch_id: UUID,
) -> Sequence[InventoryMovement]:
    """
    Retrieve all inventory movements produced by a migration batch.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        batch_id: Import batch UUID.

    Returns:
        Sequence[InventoryMovement]: Created movement rows.
    """
    stmt = select(InventoryMovement).where(
        InventoryMovement.source_type == "MIGRATION_OPENING_INVENTORY",
        InventoryMovement.source_id == batch_id,
    )
    result = await session.execute(stmt)
    return result.scalars().all()
