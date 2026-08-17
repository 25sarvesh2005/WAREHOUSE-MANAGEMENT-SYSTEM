"""
SQLAlchemy ORM models for customer orders, order lines, and reservations.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Order(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Persisted customer order header."""

    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("seller_id", "seller_order_number", name="uq_seller_order_number"),
        Index("ix_orders_wh_status", "warehouse_id", "status"),
    )

    seller_id: Mapped[UUID] = mapped_column(ForeignKey("sellers.id"), nullable=False, index=True)
    seller_order_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    warehouse_id: Mapped[UUID] = mapped_column(
        ForeignKey("warehouses.id"), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(String(50), nullable=False, default="DIRECT")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="DRAFT", index=True)
    policy_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    customer_name: Mapped[str | None] = mapped_column(String(200))
    shipping_address_line1: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    postal_code: Mapped[str | None] = mapped_column(String(30))

    lines: Mapped[list[OrderLine]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class OrderLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Line item breakdown within an order."""

    __tablename__ = "order_lines"
    __table_args__ = (UniqueConstraint("order_id", "product_id", name="uq_order_line_product"),)

    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    ordered_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    reserved_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    picked_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    shipped_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    backordered_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    cancelled_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )

    order: Mapped[Order] = relationship(back_populates="lines")
    reservations: Mapped[list[InventoryReservation]] = relationship(
        back_populates="order_line",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class InventoryReservation(UUIDPrimaryKeyMixin, Base):
    """Active or historical inventory reservation for an order line."""

    __tablename__ = "inventory_reservations"

    order_line_id: Mapped[UUID] = mapped_column(
        ForeignKey("order_lines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    warehouse_id: Mapped[UUID] = mapped_column(
        ForeignKey("warehouses.id"), nullable=False, index=True
    )
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ACTIVE", index=True)
    reserved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    order_line: Mapped[OrderLine] = relationship(back_populates="reservations")
