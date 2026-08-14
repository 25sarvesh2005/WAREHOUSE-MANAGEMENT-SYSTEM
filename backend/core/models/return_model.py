"""
Return Models.

Defines customer / seller return header, line, and disposition log models.

Tables:
    - returns: Return header tracking RMA, inbound tracking, warehouse, and status.
    - return_lines: Line item expected/received quantities and inspection notes.
    - return_dispositions: Inspection outcome disposition log moving stock into target buckets.
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.constants import ReturnStatus
from core.database.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from core.models.catalog_model import Product, Seller, Warehouse, WarehouseLocation
    from core.models.order_model import Order


class Return(UUIDPrimaryKeyMixin, Base):
    """Customer / seller inbound return header."""

    __tablename__ = "returns"
    __table_args__ = (
        Index("ix_returns_seller_status", "seller_id", "status"),
        Index("ix_returns_wh_status", "warehouse_id", "status"),
    )

    return_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    seller_id: Mapped[UUID] = mapped_column(ForeignKey("sellers.id"), nullable=False, index=True)
    warehouse_id: Mapped[UUID] = mapped_column(
        ForeignKey("warehouses.id"), nullable=False, index=True
    )
    order_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("orders.id"), nullable=True, index=True
    )
    rma_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    inbound_tracking_number: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default=ReturnStatus.EXPECTED.value, index=True
    )
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    lines: Mapped[list["ReturnLine"]] = relationship(
        back_populates="return_header",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ReturnLine(UUIDPrimaryKeyMixin, Base):
    """Return line item for expected or received products."""

    __tablename__ = "return_lines"

    return_id: Mapped[UUID] = mapped_column(ForeignKey("returns.id"), nullable=False, index=True)
    product_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("products.id"), nullable=True, index=True
    )
    expected_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    received_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    reason_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    inspection_notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    return_header: Mapped["Return"] = relationship(back_populates="lines")
    dispositions: Mapped[list["ReturnDisposition"]] = relationship(
        back_populates="return_line",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ReturnDisposition(UUIDPrimaryKeyMixin, Base):
    """Inspection outcome log itemizing movement to final disposition state."""

    __tablename__ = "return_dispositions"

    return_line_id: Mapped[UUID] = mapped_column(
        ForeignKey("return_lines.id"), nullable=False, index=True
    )
    disposition_state: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    destination_location_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("warehouse_locations.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    return_line: Mapped["ReturnLine"] = relationship(back_populates="dispositions")
