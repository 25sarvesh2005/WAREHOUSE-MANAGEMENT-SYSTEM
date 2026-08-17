"""
SQLAlchemy ORM models for opening inventory import batches and staged rows.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ImportBatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Header record for an opening inventory migration batch."""

    __tablename__ = "import_batches"

    batch_number: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="STAGED", index=True
    )
    source_notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    approved_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class StagedOpeningInventoryRow(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Staged opening inventory row capturing raw source evidence and validation state."""

    __tablename__ = "staged_opening_inventory_rows"
    __table_args__ = (
        UniqueConstraint(
            "import_batch_id",
            "source_workbook",
            "source_sheet",
            "source_row_number",
            name="uq_staged_row_identity",
        ),
        UniqueConstraint(
            "import_batch_id",
            "source_hash",
            name="uq_staged_row_hash",
        ),
        Index("ix_staged_batch_status", "import_batch_id", "validation_status"),
    )

    import_batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("import_batches.id"), nullable=False, index=True
    )
    source_workbook: Mapped[str] = mapped_column(String(255), nullable=False)
    source_sheet: Mapped[str] = mapped_column(String(255), nullable=False)
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    raw_seller_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_sku: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_upc: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_warehouse_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_location_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_inventory_state: Mapped[str | None] = mapped_column(String(50), nullable=True)
    raw_quantity: Mapped[str | None] = mapped_column(String(100), nullable=True)

    seller_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("sellers.id"), nullable=True, index=True
    )
    product_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("products.id"), nullable=True, index=True
    )
    warehouse_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("warehouses.id"), nullable=True, index=True
    )
    location_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("warehouse_locations.id"), nullable=True, index=True
    )
    inventory_state: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True
    )
    quantity: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    validation_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="PENDING", index=True
    )
    validation_errors: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    applied_movement_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("inventory_movements.id"), nullable=True, index=True
    )
