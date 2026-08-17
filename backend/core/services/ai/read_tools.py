"""
--------------------------------------------------------------------------------
File        : core/services/ai/read_tools.py
Purpose     : Provide permission-scoped read-only AI application tools.

Responsibilities:
    - Query approved application records for AI Release A answers.
    - Keep AI reads scoped by seller and warehouse filters supplied by controllers.
    - Return structured evidence without exposing direct database access to AI.

Flow:
    AIController
        ->
    read-only tool function with AsyncSession
        ->
    SQLAlchemy selects against application models
        ->
    dataclass evidence returned to controller

Used By:
    - core/controllers/ai_controller.py

Returns:
    Dataclass evidence records for availability and ledger explanation.

Raises:
    sqlalchemy.exc.SQLAlchemyError: On database failures.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from common.logger import get_logger
from core.constants import (
    InventoryState,
    MigrationBatchStatus,
    PickTaskStatus,
    ReceiptStatus,
    ReservationStatus,
    ReturnStatus,
    TransferStatus,
)
from core.models.catalog_model import Product
from core.models.fulfillment_model import PickTask, Shipment
from core.models.identity_model import Seller, Warehouse
from core.models.inventory_model import InventoryBalance, InventoryMovement
from core.models.migration_model import ImportBatch
from core.models.order_model import InventoryReservation, Order, OrderLine
from core.models.receiving_model import Receipt
from core.models.return_model import Return
from core.models.transfer_model import Transfer

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class AvailableInventoryEvidence:
    """Aggregated available inventory evidence for one seller/product/warehouse."""

    seller_id: UUID
    seller_code: str
    product_id: UUID
    sku: str
    product_name: str
    warehouse_id: UUID
    warehouse_code: str
    available_quantity: Decimal


@dataclass(frozen=True, slots=True)
class LedgerMovementEvidence:
    """Append-only movement ledger evidence for AI explanation."""

    movement_id: UUID
    seller_id: UUID
    seller_code: str
    product_id: UUID
    sku: str
    product_name: str
    warehouse_id: UUID
    warehouse_code: str
    inventory_state: str
    quantity_delta: Decimal
    movement_type: str
    source_type: str
    source_id: UUID
    reason_code: str | None
    reason_text: str | None
    recorded_at: datetime


@dataclass(frozen=True, slots=True)
class OperationalStatusEvidence:
    """Read-only operational record status evidence for AI answers."""

    record_type: str
    record_id: UUID
    reference_number: str
    status: str
    seller_id: UUID
    seller_code: str
    warehouse_ids: list[UUID]
    warehouse_codes: list[str]
    summary: dict[str, object]
    details: list[dict[str, object]]


@dataclass(frozen=True, slots=True)
class OperationalExceptionEvidence:
    """Read-only operational exceptions aggregated across warehouse subsystems."""

    overdue_receipts: list[dict[str, object]]
    short_pick_exceptions: list[dict[str, object]]
    expired_or_expiring_reservations: list[dict[str, object]]
    transfer_variances: list[dict[str, object]]
    return_inspection_queues: list[dict[str, object]]
    migration_validation_failures: list[dict[str, object]]
    total_exceptions: int


async def lookup_available_inventory(
    session: AsyncSession,
    *,
    sku: str,
    seller_id: UUID | None,
    seller_ids: Sequence[UUID] | None,
    warehouse_id: UUID | None,
    warehouse_ids: Sequence[UUID] | None,
) -> list[AvailableInventoryEvidence]:
    """
    Aggregate available inventory for a SKU or natural language query by warehouse.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        sku: Product SKU, product name, or freeform inventory question.
        seller_id: Optional exact seller filter.
        seller_ids: Optional permitted seller scope filter.
        warehouse_id: Optional exact warehouse filter.
        warehouse_ids: Optional permitted warehouse scope filter.

    Returns:
        list[AvailableInventoryEvidence]: Matching available quantity rows.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the query fails.
    """
    logger.debug("AI read tool lookup_available_inventory query=%s", sku)
    clean_query = sku.strip()

    # Check for exact SKU match
    exact_prod = await session.scalar(
        select(Product.id).where(func.upper(Product.sku) == clean_query.upper()).limit(1)
    )

    quantity_sum = func.coalesce(func.sum(InventoryBalance.quantity), Decimal("0.00"))
    stmt = (
        select(
            Product.seller_id,
            Seller.code,
            Product.id,
            Product.sku,
            Product.name,
            InventoryBalance.warehouse_id,
            Warehouse.code,
            quantity_sum,
        )
        .select_from(InventoryBalance)
        .join(Product, InventoryBalance.product_id == Product.id)
        .join(Seller, InventoryBalance.seller_id == Seller.id)
        .join(Warehouse, InventoryBalance.warehouse_id == Warehouse.id)
        .where(
            InventoryBalance.inventory_state == InventoryState.AVAILABLE.value,
        )
    )

    if exact_prod:
        stmt = stmt.where(func.upper(Product.sku) == clean_query.upper())
    else:
        # Check if query contains specific product keywords (e.g. "headphones", "hoodie", "ANC100")
        stop_words = {
            "product", "products", "with", "quantity", "quantities", "stock", "stocks",
            "level", "levels", "have", "show", "list", "what", "which", "where",
            "across", "total", "from", "in", "the", "and", "for", "item", "items"
        }
        tokens = [t for t in clean_query.split() if len(t) > 2 and t.lower() not in stop_words]
        is_general_query = any(
            phrase in clean_query.lower()
            for phrase in ["0 quantity", "zero", "low stock", "all products", "all items", "no stock", "out of stock"]
        )

        if tokens and not is_general_query:
            from sqlalchemy import or_
            token_filters = []
            for t in tokens:
                token_filters.append(Product.sku.ilike(f"%{t}%"))
                token_filters.append(Product.name.ilike(f"%{t}%"))
            stmt = stmt.where(or_(*token_filters))

    stmt = (
        stmt.group_by(
            Product.seller_id,
            Seller.code,
            Product.id,
            Product.sku,
            Product.name,
            InventoryBalance.warehouse_id,
            Warehouse.code,
        )
        .order_by(Seller.code, Product.sku, Warehouse.code)
    )

    if seller_id is not None:
        stmt = stmt.where(InventoryBalance.seller_id == seller_id)
    elif seller_ids:
        stmt = stmt.where(InventoryBalance.seller_id.in_(seller_ids))
    if warehouse_id is not None:
        stmt = stmt.where(InventoryBalance.warehouse_id == warehouse_id)
    elif warehouse_ids:
        stmt = stmt.where(InventoryBalance.warehouse_id.in_(warehouse_ids))

    result = await session.execute(stmt)
    return [
        AvailableInventoryEvidence(
            seller_id=row[0],
            seller_code=str(row[1]),
            product_id=row[2],
            sku=str(row[3]),
            product_name=str(row[4]),
            warehouse_id=row[5],
            warehouse_code=str(row[6]),
            available_quantity=Decimal(str(row[7])),
        )
        for row in result.all()
    ]


async def lookup_recent_ledger_movements(
    session: AsyncSession,
    *,
    sku: str,
    seller_id: UUID | None,
    seller_ids: Sequence[UUID] | None,
    warehouse_id: UUID | None,
    warehouse_ids: Sequence[UUID] | None,
    limit: int,
) -> list[LedgerMovementEvidence]:
    """
    Return recent movement ledger records for a SKU.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        sku: Product SKU to inspect.
        seller_id: Optional exact seller filter.
        seller_ids: Optional permitted seller scope filter.
        warehouse_id: Optional exact warehouse filter.
        warehouse_ids: Optional permitted warehouse scope filter.
        limit: Maximum movement rows to return.

    Returns:
        list[LedgerMovementEvidence]: Recent movement ledger evidence.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the query fails.
    """
    logger.debug("AI read tool lookup_recent_ledger_movements sku=%s limit=%s", sku, limit)
    stmt = (
        select(
            InventoryMovement.id,
            InventoryMovement.seller_id,
            Seller.code,
            InventoryMovement.product_id,
            Product.sku,
            Product.name,
            InventoryMovement.warehouse_id,
            Warehouse.code,
            InventoryMovement.inventory_state,
            InventoryMovement.quantity_delta,
            InventoryMovement.movement_type,
            InventoryMovement.source_type,
            InventoryMovement.source_id,
            InventoryMovement.reason_code,
            InventoryMovement.reason_text,
            InventoryMovement.recorded_at,
        )
        .select_from(InventoryMovement)
        .join(Product, InventoryMovement.product_id == Product.id)
        .join(Seller, InventoryMovement.seller_id == Seller.id)
        .join(Warehouse, InventoryMovement.warehouse_id == Warehouse.id)
        .where(Product.sku == sku)
        .order_by(InventoryMovement.recorded_at.desc(), InventoryMovement.id.desc())
        .limit(limit)
    )
    if seller_id is not None:
        stmt = stmt.where(InventoryMovement.seller_id == seller_id)
    elif seller_ids:
        stmt = stmt.where(InventoryMovement.seller_id.in_(seller_ids))
    if warehouse_id is not None:
        stmt = stmt.where(InventoryMovement.warehouse_id == warehouse_id)
    elif warehouse_ids:
        stmt = stmt.where(InventoryMovement.warehouse_id.in_(warehouse_ids))

    result = await session.execute(stmt)
    return [
        LedgerMovementEvidence(
            movement_id=row[0],
            seller_id=row[1],
            seller_code=str(row[2]),
            product_id=row[3],
            sku=str(row[4]),
            product_name=str(row[5]),
            warehouse_id=row[6],
            warehouse_code=str(row[7]),
            inventory_state=str(row[8]),
            quantity_delta=Decimal(str(row[9])),
            movement_type=str(row[10]),
            source_type=str(row[11]),
            source_id=row[12],
            reason_code=str(row[13]) if row[13] is not None else None,
            reason_text=str(row[14]) if row[14] is not None else None,
            recorded_at=row[15],
        )
        for row in result.all()
    ]


async def lookup_order_status(
    session: AsyncSession,
    *,
    record_id: UUID | None,
    reference_number: str | None,
    seller_id: UUID | None,
    warehouse_id: UUID | None,
) -> OperationalStatusEvidence | None:
    """
    Read one order status record by ID or seller order number.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        record_id: Optional order UUID.
        reference_number: Optional seller order number.
        seller_id: Optional exact seller filter.
        warehouse_id: Optional exact warehouse filter.

    Returns:
        OperationalStatusEvidence | None: Matching order evidence or None.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the query fails.
    """
    stmt = (
        select(Order, Seller.code, Warehouse.code)
        .join(Seller, Order.seller_id == Seller.id)
        .join(Warehouse, Order.warehouse_id == Warehouse.id)
        .options(selectinload(Order.lines))
    )
    if record_id is not None:
        stmt = stmt.where(Order.id == record_id)
    if reference_number is not None:
        stmt = stmt.where(Order.seller_order_number == reference_number)
    if seller_id is not None:
        stmt = stmt.where(Order.seller_id == seller_id)
    if warehouse_id is not None:
        stmt = stmt.where(Order.warehouse_id == warehouse_id)

    result = await session.execute(stmt)
    row = result.first()
    if row is None:
        return None
    order, seller_code, warehouse_code = row
    return OperationalStatusEvidence(
        record_type="order",
        record_id=order.id,
        reference_number=order.seller_order_number,
        status=order.status,
        seller_id=order.seller_id,
        seller_code=str(seller_code),
        warehouse_ids=[order.warehouse_id],
        warehouse_codes=[str(warehouse_code)],
        summary={
            "channel": order.channel,
            "customer_name": order.customer_name,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
        },
        details=[
            {
                "line_id": line.id,
                "product_id": line.product_id,
                "ordered_quantity": line.ordered_quantity,
                "reserved_quantity": line.reserved_quantity,
                "picked_quantity": line.picked_quantity,
                "shipped_quantity": line.shipped_quantity,
                "backordered_quantity": line.backordered_quantity,
                "cancelled_quantity": line.cancelled_quantity,
            }
            for line in order.lines
        ],
    )


async def lookup_receipt_status(
    session: AsyncSession,
    *,
    record_id: UUID | None,
    reference_number: str | None,
    seller_id: UUID | None,
    warehouse_id: UUID | None,
) -> OperationalStatusEvidence | None:
    """
    Read one receipt status record by ID or receipt number.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        record_id: Optional receipt UUID.
        reference_number: Optional receipt number.
        seller_id: Optional exact seller filter.
        warehouse_id: Optional exact warehouse filter.

    Returns:
        OperationalStatusEvidence | None: Matching receipt evidence or None.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the query fails.
    """
    stmt = (
        select(Receipt, Seller.code, Warehouse.code)
        .join(Seller, Receipt.seller_id == Seller.id)
        .join(Warehouse, Receipt.warehouse_id == Warehouse.id)
        .options(selectinload(Receipt.lines), selectinload(Receipt.events))
    )
    if record_id is not None:
        stmt = stmt.where(Receipt.id == record_id)
    if reference_number is not None:
        stmt = stmt.where(Receipt.receipt_number == reference_number)
    if seller_id is not None:
        stmt = stmt.where(Receipt.seller_id == seller_id)
    if warehouse_id is not None:
        stmt = stmt.where(Receipt.warehouse_id == warehouse_id)

    result = await session.execute(stmt)
    row = result.first()
    if row is None:
        return None
    receipt, seller_code, warehouse_code = row
    return OperationalStatusEvidence(
        record_type="receipt",
        record_id=receipt.id,
        reference_number=receipt.receipt_number,
        status=receipt.status,
        seller_id=receipt.seller_id,
        seller_code=str(seller_code),
        warehouse_ids=[receipt.warehouse_id],
        warehouse_codes=[str(warehouse_code)],
        summary={
            "source_type": receipt.source_type,
            "source_reference": receipt.source_reference,
            "expected_arrival_at": receipt.expected_arrival_at,
            "actual_arrival_at": receipt.actual_arrival_at,
            "completed_at": receipt.completed_at,
        },
        details=[
            {
                "line_id": line.id,
                "product_id": line.product_id,
                "expected_quantity": line.expected_quantity,
                "sellable_quantity": line.sellable_quantity,
                "damaged_quantity": line.damaged_quantity,
                "quarantined_quantity": line.quarantined_quantity,
                "shortage_quantity": line.shortage_quantity,
                "overage_quantity": line.overage_quantity,
            }
            for line in receipt.lines
        ],
    )


async def lookup_transfer_status(
    session: AsyncSession,
    *,
    record_id: UUID | None,
    reference_number: str | None,
    seller_id: UUID | None,
    warehouse_id: UUID | None,
) -> OperationalStatusEvidence | None:
    """
    Read one transfer status record by ID or transfer number.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        record_id: Optional transfer UUID.
        reference_number: Optional transfer number.
        seller_id: Optional exact seller filter.
        warehouse_id: Optional origin/destination warehouse filter.

    Returns:
        OperationalStatusEvidence | None: Matching transfer evidence or None.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the query fails.
    """
    origin = aliased(Warehouse)
    destination = aliased(Warehouse)
    stmt = (
        select(Transfer, Seller.code, origin.code, destination.code)
        .join(Seller, Transfer.seller_id == Seller.id)
        .join(origin, Transfer.origin_warehouse_id == origin.id)
        .join(destination, Transfer.destination_warehouse_id == destination.id)
        .options(selectinload(Transfer.lines))
    )
    if record_id is not None:
        stmt = stmt.where(Transfer.id == record_id)
    if reference_number is not None:
        stmt = stmt.where(Transfer.transfer_number == reference_number)
    if seller_id is not None:
        stmt = stmt.where(Transfer.seller_id == seller_id)
    if warehouse_id is not None:
        stmt = stmt.where(
            (Transfer.origin_warehouse_id == warehouse_id)
            | (Transfer.destination_warehouse_id == warehouse_id)
        )

    result = await session.execute(stmt)
    row = result.first()
    if row is None:
        return None
    transfer, seller_code, origin_code, destination_code = row
    return OperationalStatusEvidence(
        record_type="transfer",
        record_id=transfer.id,
        reference_number=transfer.transfer_number,
        status=transfer.status,
        seller_id=transfer.seller_id,
        seller_code=str(seller_code),
        warehouse_ids=[transfer.origin_warehouse_id, transfer.destination_warehouse_id],
        warehouse_codes=[str(origin_code), str(destination_code)],
        summary={
            "origin_warehouse_id": transfer.origin_warehouse_id,
            "destination_warehouse_id": transfer.destination_warehouse_id,
            "dispatched_at": transfer.dispatched_at,
            "received_at": transfer.received_at,
            "notes": transfer.notes,
        },
        details=[
            {
                "line_id": line.id,
                "product_id": line.product_id,
                "requested_quantity": line.requested_quantity,
                "approved_quantity": line.approved_quantity,
                "dispatched_quantity": line.dispatched_quantity,
                "received_good_quantity": line.received_good_quantity,
                "received_damaged_quantity": line.received_damaged_quantity,
                "missing_quantity": line.missing_quantity,
                "overage_quantity": line.overage_quantity,
            }
            for line in transfer.lines
        ],
    )


async def lookup_shipment_status(
    session: AsyncSession,
    *,
    record_id: UUID | None,
    reference_number: str | None,
    seller_id: UUID | None,
    warehouse_id: UUID | None,
) -> OperationalStatusEvidence | None:
    """
    Read one shipment status record by ID or tracking number.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        record_id: Optional shipment UUID.
        reference_number: Optional tracking number.
        seller_id: Optional exact seller filter through order ownership.
        warehouse_id: Optional exact warehouse filter.

    Returns:
        OperationalStatusEvidence | None: Matching shipment evidence or None.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the query fails.
    """
    stmt = (
        select(Shipment, Order, Seller.code, Warehouse.code)
        .join(Order, Shipment.order_id == Order.id)
        .join(Seller, Order.seller_id == Seller.id)
        .join(Warehouse, Shipment.warehouse_id == Warehouse.id)
        .options(selectinload(Shipment.packages), selectinload(Shipment.events))
    )
    if record_id is not None:
        stmt = stmt.where(Shipment.id == record_id)
    if reference_number is not None:
        stmt = stmt.where(Shipment.tracking_number == reference_number)
    if seller_id is not None:
        stmt = stmt.where(Order.seller_id == seller_id)
    if warehouse_id is not None:
        stmt = stmt.where(Shipment.warehouse_id == warehouse_id)

    result = await session.execute(stmt)
    row = result.first()
    if row is None:
        return None
    shipment, order, seller_code, warehouse_code = row
    details = [
        {
            "package_id": package.id,
            "box_type": package.box_type,
            "weight_lbs": package.weight_lbs,
            "length_in": package.length_in,
            "width_in": package.width_in,
            "height_in": package.height_in,
        }
        for package in shipment.packages
    ]
    details.extend(
        {
            "event_id": event.id,
            "event_type": event.event_type,
            "details": event.details,
            "created_at": event.created_at,
        }
        for event in shipment.events
    )
    return OperationalStatusEvidence(
        record_type="shipment",
        record_id=shipment.id,
        reference_number=shipment.tracking_number,
        status=shipment.status,
        seller_id=order.seller_id,
        seller_code=str(seller_code),
        warehouse_ids=[shipment.warehouse_id],
        warehouse_codes=[str(warehouse_code)],
        summary={
            "order_id": shipment.order_id,
            "seller_order_number": order.seller_order_number,
            "carrier": shipment.carrier,
            "service_level": shipment.service_level,
            "shipped_at": shipment.shipped_at,
        },
        details=details,
    )


async def lookup_return_status(
    session: AsyncSession,
    *,
    record_id: UUID | None,
    reference_number: str | None,
    seller_id: UUID | None,
    warehouse_id: UUID | None,
) -> OperationalStatusEvidence | None:
    """
    Read one return status record by ID or return number.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        record_id: Optional return UUID.
        reference_number: Optional return number.
        seller_id: Optional exact seller filter.
        warehouse_id: Optional exact warehouse filter.

    Returns:
        OperationalStatusEvidence | None: Matching return evidence or None.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the query fails.
    """
    stmt = (
        select(Return, Seller.code, Warehouse.code)
        .join(Seller, Return.seller_id == Seller.id)
        .join(Warehouse, Return.warehouse_id == Warehouse.id)
        .options(selectinload(Return.lines))
    )
    if record_id is not None:
        stmt = stmt.where(Return.id == record_id)
    if reference_number is not None:
        stmt = stmt.where(Return.return_number == reference_number)
    if seller_id is not None:
        stmt = stmt.where(Return.seller_id == seller_id)
    if warehouse_id is not None:
        stmt = stmt.where(Return.warehouse_id == warehouse_id)

    result = await session.execute(stmt)
    row = result.first()
    if row is None:
        return None
    return_header, seller_code, warehouse_code = row
    return OperationalStatusEvidence(
        record_type="return",
        record_id=return_header.id,
        reference_number=return_header.return_number,
        status=return_header.status,
        seller_id=return_header.seller_id,
        seller_code=str(seller_code),
        warehouse_ids=[return_header.warehouse_id],
        warehouse_codes=[str(warehouse_code)],
        summary={
            "order_id": return_header.order_id,
            "rma_number": return_header.rma_number,
            "inbound_tracking_number": return_header.inbound_tracking_number,
            "received_at": return_header.received_at,
            "completed_at": return_header.completed_at,
            "notes": return_header.notes,
        },
        details=[
            {
                "line_id": line.id,
                "product_id": line.product_id,
                "expected_quantity": line.expected_quantity,
                "received_quantity": line.received_quantity,
                "reason_code": line.reason_code,
                "inspection_notes": line.inspection_notes,
            }
            for line in return_header.lines
        ],
    )


async def lookup_operational_exceptions(
    session: AsyncSession,
    *,
    seller_id: UUID | None = None,
    seller_ids: Sequence[UUID] | None = None,
    warehouse_id: UUID | None = None,
    warehouse_ids: Sequence[UUID] | None = None,
    include_migration_failures: bool = True,
) -> OperationalExceptionEvidence:
    """
    Query operational exception records across warehouse subsystems.

    Collects pending/overdue receipts, short-pick tasks, expired/expiring
    reservations, transfer discrepancies, return inspection queues, and
    staged migration validation failures.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        seller_id: Optional specific seller UUID filter.
        seller_ids: Optional allowed seller UUIDs for role scoping.
        warehouse_id: Optional specific warehouse UUID filter.
        warehouse_ids: Optional allowed warehouse UUIDs for role scoping.
        include_migration_failures: Whether to include staged migration validation failures.

    Returns:
        OperationalExceptionEvidence: Structured exceptions across categories.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: On database query failures.
    """
    logger.debug("Aggregating operational exceptions across subsystems")

    # 1. Pending & Overdue Receipts
    receipt_stmt = (
        select(Receipt, Seller.code, Warehouse.code)
        .join(Seller, Receipt.seller_id == Seller.id)
        .join(Warehouse, Receipt.warehouse_id == Warehouse.id)
        .where(
            Receipt.status.in_(
                [
                    ReceiptStatus.DRAFT.value,
                    ReceiptStatus.IN_PROGRESS.value,
                    ReceiptStatus.PENDING_REVIEW.value,
                ]
            )
        )
        .order_by(Receipt.created_at.asc())
        .limit(25)
    )
    if seller_id is not None:
        receipt_stmt = receipt_stmt.where(Receipt.seller_id == seller_id)
    elif seller_ids is not None:
        receipt_stmt = receipt_stmt.where(Receipt.seller_id.in_(seller_ids))
    if warehouse_id is not None:
        receipt_stmt = receipt_stmt.where(Receipt.warehouse_id == warehouse_id)
    elif warehouse_ids is not None:
        receipt_stmt = receipt_stmt.where(Receipt.warehouse_id.in_(warehouse_ids))

    receipt_rows = (await session.execute(receipt_stmt)).all()
    overdue_receipts: list[dict[str, object]] = []
    now = datetime.now(UTC)
    for rc, s_code, w_code in receipt_rows:
        is_overdue = (now - rc.created_at).total_seconds() > 86400 * 2  # older than 48h
        overdue_receipts.append(
            {
                "receipt_id": rc.id,
                "receipt_number": rc.receipt_number,
                "status": rc.status,
                "seller_id": rc.seller_id,
                "seller_code": str(s_code),
                "warehouse_id": rc.warehouse_id,
                "warehouse_code": str(w_code),
                "source_type": rc.source_type,
                "source_reference": rc.source_reference,
                "is_overdue": is_overdue,
                "age_hours": round((now - rc.created_at).total_seconds() / 3600, 1),
                "created_at": rc.created_at.isoformat(),
            }
        )

    # 2. Short-Pick Exceptions
    pick_stmt = (
        select(PickTask, Warehouse.code)
        .join(Warehouse, PickTask.warehouse_id == Warehouse.id)
        .where(PickTask.status == PickTaskStatus.SHORT_PICK_EXCEPTION.value)
        .order_by(PickTask.created_at.desc())
        .limit(25)
    )
    if warehouse_id is not None:
        pick_stmt = pick_stmt.where(PickTask.warehouse_id == warehouse_id)
    elif warehouse_ids is not None:
        pick_stmt = pick_stmt.where(PickTask.warehouse_id.in_(warehouse_ids))

    pick_rows = (await session.execute(pick_stmt)).all()
    short_picks: list[dict[str, object]] = [
        {
            "pick_task_id": pt.id,
            "pick_task_reference": str(pt.id),
            "order_id": pt.order_id,
            "warehouse_id": pt.warehouse_id,
            "warehouse_code": str(w_code),
            "status": pt.status,
            "exception_reason": getattr(pt, "exception_reason", None) or "Short pick detected",
            "created_at": pt.created_at.isoformat(),
        }
        for pt, w_code in pick_rows
    ]

    # 3. Expired or Expiring Reservations (within 1 hour or already expired)
    expiry_horizon = now + timedelta(hours=1)
    res_stmt = (
        select(InventoryReservation, Order.seller_id, Seller.code, Warehouse.code)
        .join(OrderLine, InventoryReservation.order_line_id == OrderLine.id)
        .join(Order, OrderLine.order_id == Order.id)
        .join(Seller, Order.seller_id == Seller.id)
        .join(Warehouse, InventoryReservation.warehouse_id == Warehouse.id)
        .where(
            InventoryReservation.status == ReservationStatus.ACTIVE.value,
            InventoryReservation.expires_at <= expiry_horizon,
        )
        .order_by(InventoryReservation.expires_at.asc())
        .limit(25)
    )
    if seller_id is not None:
        res_stmt = res_stmt.where(Order.seller_id == seller_id)
    elif seller_ids is not None:
        res_stmt = res_stmt.where(Order.seller_id.in_(seller_ids))
    if warehouse_id is not None:
        res_stmt = res_stmt.where(InventoryReservation.warehouse_id == warehouse_id)
    elif warehouse_ids is not None:
        res_stmt = res_stmt.where(InventoryReservation.warehouse_id.in_(warehouse_ids))

    res_rows = (await session.execute(res_stmt)).all()
    reservations: list[dict[str, object]] = [
        {
            "reservation_id": r.id,
            "order_line_id": r.order_line_id,
            "seller_id": s_id,
            "seller_code": str(s_code),
            "warehouse_id": r.warehouse_id,
            "warehouse_code": str(w_code),
            "product_id": r.product_id,
            "quantity": float(r.quantity),
            "expires_at": r.expires_at.isoformat() if r.expires_at else None,
            "is_expired": bool(r.expires_at and r.expires_at <= now),
        }
        for r, s_id, s_code, w_code in res_rows
    ]

    # 4. Transfer Discrepancies
    src_warehouse = aliased(Warehouse)
    dst_warehouse = aliased(Warehouse)
    transfer_stmt = (
        select(Transfer, src_warehouse.code, dst_warehouse.code)
        .join(src_warehouse, Transfer.origin_warehouse_id == src_warehouse.id)
        .join(dst_warehouse, Transfer.destination_warehouse_id == dst_warehouse.id)
        .where(Transfer.status == TransferStatus.DISCREPANCY_REVIEW.value)
        .order_by(Transfer.created_at.desc())
        .limit(25)
    )
    if warehouse_id is not None:
        transfer_stmt = transfer_stmt.where(
            (Transfer.origin_warehouse_id == warehouse_id)
            | (Transfer.destination_warehouse_id == warehouse_id)
        )
    elif warehouse_ids is not None:
        transfer_stmt = transfer_stmt.where(
            Transfer.origin_warehouse_id.in_(warehouse_ids)
            | Transfer.destination_warehouse_id.in_(warehouse_ids)
        )

    transfer_rows = (await session.execute(transfer_stmt)).all()
    transfers: list[dict[str, object]] = [
        {
            "transfer_id": t.id,
            "transfer_number": t.transfer_number,
            "status": t.status,
            "origin_warehouse_id": t.origin_warehouse_id,
            "origin_warehouse_code": str(src_code),
            "destination_warehouse_id": t.destination_warehouse_id,
            "destination_warehouse_code": str(dst_code),
            "discrepancy_notes": getattr(t, "discrepancy_notes", None) or t.notes,
            "created_at": t.created_at.isoformat(),
        }
        for t, src_code, dst_code in transfer_rows
    ]

    # 5. Return Inspection Queues
    return_stmt = (
        select(Return, Seller.code, Warehouse.code)
        .join(Seller, Return.seller_id == Seller.id)
        .join(Warehouse, Return.warehouse_id == Warehouse.id)
        .where(
            Return.status.in_(
                [
                    ReturnStatus.RECEIVED.value,
                    ReturnStatus.INSPECTION.value,
                    ReturnStatus.UNIDENTIFIED.value,
                ]
            )
        )
        .order_by(Return.created_at.asc())
        .limit(25)
    )
    if seller_id is not None:
        return_stmt = return_stmt.where(Return.seller_id == seller_id)
    elif seller_ids is not None:
        return_stmt = return_stmt.where(Return.seller_id.in_(seller_ids))
    if warehouse_id is not None:
        return_stmt = return_stmt.where(Return.warehouse_id == warehouse_id)
    elif warehouse_ids is not None:
        return_stmt = return_stmt.where(Return.warehouse_id.in_(warehouse_ids))

    return_rows = (await session.execute(return_stmt)).all()
    returns: list[dict[str, object]] = [
        {
            "return_id": ret.id,
            "return_number": ret.return_number,
            "status": ret.status,
            "seller_id": ret.seller_id,
            "seller_code": str(s_code),
            "warehouse_id": ret.warehouse_id,
            "warehouse_code": str(w_code),
            "rma_number": ret.rma_number,
            "inbound_tracking_number": ret.inbound_tracking_number,
            "created_at": ret.created_at.isoformat(),
        }
        for ret, s_code, w_code in return_rows
    ]

    # 6. Migration Validation Failures
    migration_failures: list[dict[str, object]] = []
    if include_migration_failures:
        mig_stmt = (
            select(ImportBatch)
            .where(ImportBatch.status == MigrationBatchStatus.VALIDATION_FAILED.value)
            .order_by(ImportBatch.created_at.desc())
            .limit(10)
        )
        mig_rows = (await session.execute(mig_stmt)).scalars().all()
        migration_failures = [
            {
                "batch_id": mb.id,
                "batch_number": mb.batch_number,
                "status": mb.status,
                "source_notes": mb.source_notes,
                "invalid_rows_count": mb.invalid_rows,
                "created_at": mb.created_at.isoformat(),
            }
            for mb in mig_rows
        ]

    total_count = (
        len(overdue_receipts)
        + len(short_picks)
        + len(reservations)
        + len(transfers)
        + len(returns)
        + len(migration_failures)
    )

    return OperationalExceptionEvidence(
        overdue_receipts=overdue_receipts,
        short_pick_exceptions=short_picks,
        expired_or_expiring_reservations=reservations,
        transfer_variances=transfers,
        return_inspection_queues=returns,
        migration_validation_failures=migration_failures,
        total_exceptions=total_count,
    )
