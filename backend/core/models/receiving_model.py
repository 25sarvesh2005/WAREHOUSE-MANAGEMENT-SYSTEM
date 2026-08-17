"""
SQLAlchemy ORM models for receiving receipts, lines, and receipt events.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Receipt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Receiving receipt header."""

    __tablename__ = "receipts"
    __table_args__ = (
        UniqueConstraint("receipt_number", name="uq_receipt_number"),
        Index("ix_receipts_seller_wh", "seller_id", "warehouse_id"),
        Index("ix_receipts_source", "warehouse_id", "source_type", "source_reference"),
    )

    receipt_number: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    seller_id: Mapped[UUID] = mapped_column(ForeignKey("sellers.id"), nullable=False, index=True)
    warehouse_id: Mapped[UUID] = mapped_column(
        ForeignKey("warehouses.id"), nullable=False, index=True
    )
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(255), nullable=False)
    client_draft_id: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="DRAFT", index=True)
    expected_arrival_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_arrival_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    completed_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    is_duplicate_override: Mapped[bool] = mapped_column(nullable=False, default=False)
    original_receipt_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("receipts.id"), nullable=True
    )
    overridden_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    override_reason: Mapped[str | None] = mapped_column(String(500))

    lines: Mapped[list[ReceiptLine]] = relationship(
        back_populates="receipt",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    events: Mapped[list[ReceiptEvent]] = relationship(
        back_populates="receipt",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ReceiptLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Line item breakdown within a receiving receipt."""

    __tablename__ = "receipt_lines"
    __table_args__ = (
        UniqueConstraint("receipt_id", "product_id", name="uq_receipt_line_product"),
    )

    receipt_id: Mapped[UUID] = mapped_column(
        ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    expected_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    sellable_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    damaged_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    quarantined_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    shortage_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    overage_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    notes: Mapped[str | None] = mapped_column(String(500))

    receipt: Mapped[Receipt] = relationship(back_populates="lines")


class ReceiptEvent(UUIDPrimaryKeyMixin, Base):
    """Workflow event audit record for receiving activity."""

    __tablename__ = "receipt_events"

    receipt_id: Mapped[UUID] = mapped_column(
        ForeignKey("receipts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    details: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    receipt: Mapped[Receipt] = relationship(back_populates="events")
