"""
Transfer Models.

Defines multi-warehouse inventory transfer header and line models.

Tables:
    - transfers: Transfer header tracking origin/destination facilities and lifecycle states.
    - transfer_lines: Per-SKU transfer line items tracking requested, dispatched, and received quantities.
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.constants import TransferStatus
from core.database.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from core.models.catalog_model import Product, Seller, Warehouse
    from core.models.identity_model import User


class Transfer(UUIDPrimaryKeyMixin, Base):
    """Multi-warehouse inventory transfer header."""

    __tablename__ = "transfers"
    __table_args__ = (
        CheckConstraint(
            "origin_warehouse_id != destination_warehouse_id",
            name="ck_transfer_origin_diff_dest",
        ),
        Index("ix_transfers_seller_status", "seller_id", "status"),
        Index("ix_transfers_origin_dest", "origin_warehouse_id", "destination_warehouse_id"),
    )

    transfer_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    seller_id: Mapped[UUID] = mapped_column(ForeignKey("sellers.id"), nullable=False, index=True)
    origin_warehouse_id: Mapped[UUID] = mapped_column(
        ForeignKey("warehouses.id"), nullable=False, index=True
    )
    destination_warehouse_id: Mapped[UUID] = mapped_column(
        ForeignKey("warehouses.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=TransferStatus.DRAFT.value, index=True
    )
    created_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    approved_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    lines: Mapped[list["TransferLine"]] = relationship(
        back_populates="transfer",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class TransferLine(UUIDPrimaryKeyMixin, Base):
    """Line item itemization for inventory transfer."""

    __tablename__ = "transfer_lines"

    transfer_id: Mapped[UUID] = mapped_column(ForeignKey("transfers.id"), nullable=False, index=True)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    requested_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    approved_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    dispatched_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    received_good_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    received_damaged_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    missing_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    overage_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    transfer: Mapped["Transfer"] = relationship(back_populates="lines")
