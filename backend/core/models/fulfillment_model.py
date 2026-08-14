"""
--------------------------------------------------------------------------------
File        : core/models/fulfillment_model.py
Purpose     : Define pick task, package, shipment, and shipment event models.

Responsibilities:
    - Track warehouse pick task generation and execution.
    - Handle short-pick exception reporting.
    - Store package dimensions and manual shipment tracking information.

Flow:
    Reserved Order -> PickTask -> Package -> Shipment -> Post Ledger Movements

Used By:
    - core/cruds/fulfillment_crud.py
    - core/controllers/fulfillment_controller.py

Returns:
    SQLAlchemy model instances - Fulfillment persistence records.

Raises:
    sqlalchemy.exc.IntegrityError: On constraint or foreign key violations.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PickTask(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Warehouse worker pick task header."""

    __tablename__ = "pick_tasks"
    __table_args__ = (Index("ix_pick_tasks_wh_status", "warehouse_id", "status"),)

    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    warehouse_id: Mapped[UUID] = mapped_column(
        ForeignKey("warehouses.id"), nullable=False, index=True
    )
    assigned_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ASSIGNED", index=True)
    priority: Mapped[int] = mapped_column(nullable=False, default=1)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    lines: Mapped[list[PickTaskLine]] = relationship(
        back_populates="pick_task",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class PickTaskLine(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Line item assignment on a pick task."""

    __tablename__ = "pick_task_lines"

    pick_task_id: Mapped[UUID] = mapped_column(
        ForeignKey("pick_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_line_id: Mapped[UUID] = mapped_column(ForeignKey("order_lines.id"), nullable=False)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    location_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("warehouse_locations.id"), nullable=True
    )
    requested_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    picked_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    short_quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )

    pick_task: Mapped[PickTask] = relationship(back_populates="lines")


class Package(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Physical package record for an order shipment."""

    __tablename__ = "packages"

    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    shipment_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("shipments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    box_type: Mapped[str] = mapped_column(String(50), nullable=False, default="CUSTOM")
    weight_lbs: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    length_in: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    width_in: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    height_in: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))


class Shipment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Outbound shipment record with manual tracking dispatch."""

    __tablename__ = "shipments"
    __table_args__ = (UniqueConstraint("tracking_number", name="uq_shipment_tracking"),)

    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    warehouse_id: Mapped[UUID] = mapped_column(
        ForeignKey("warehouses.id"), nullable=False, index=True
    )
    carrier: Mapped[str] = mapped_column(String(50), nullable=False, default="MANUAL_CARRIER")
    service_level: Mapped[str] = mapped_column(String(50), nullable=False, default="GROUND")
    tracking_number: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="SHIPPED", index=True)
    shipped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    packages: Mapped[list[Package]] = relationship(lazy="selectin")
    events: Mapped[list[ShipmentEvent]] = relationship(
        back_populates="shipment",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ShipmentEvent(UUIDPrimaryKeyMixin, Base):
    """Audit event for shipment lifecycle activity."""

    __tablename__ = "shipment_events"

    shipment_id: Mapped[UUID] = mapped_column(
        ForeignKey("shipments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    details: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    shipment: Mapped[Shipment] = relationship(back_populates="events")
