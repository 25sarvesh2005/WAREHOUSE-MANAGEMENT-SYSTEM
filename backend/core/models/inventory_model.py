"""
--------------------------------------------------------------------------------
File        : core/models/inventory_model.py
Purpose     : Define inventory movement ledger, balance projections, and adjustment models.

Responsibilities:
    - Persist append-only inventory movements (authoritative ledger).
    - Maintain fast operational balance projections by location and state.
    - Track inventory adjustments and reconciliation records.

Flow:
    Receiving / Order / Adjustment action
        ->
    Persist InventoryMovement (append-only)
        ->
    Update InventoryBalance projection (same transaction)

Used By:
    - core/cruds/inventory_crud.py
    - core/controllers/inventory_controller.py

Returns:
    SQLAlchemy model instances - Inventory persistence records.

Raises:
    sqlalchemy.exc.IntegrityError: On constraint or uniqueness violations.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class InventoryMovement(UUIDPrimaryKeyMixin, Base):
    """Append-only inventory movement ledger entry."""

    __tablename__ = "inventory_movements"
    __table_args__ = (
        UniqueConstraint(
            "source_type",
            "source_line_id",
            "movement_type",
            "idempotency_key",
            name="uq_movement_source_retry",
        ),
        Index("ix_movements_seller_product", "seller_id", "product_id"),
        Index("ix_movements_wh_loc", "warehouse_id", "location_id"),
    )

    seller_id: Mapped[UUID] = mapped_column(ForeignKey("sellers.id"), nullable=False, index=True)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    warehouse_id: Mapped[UUID] = mapped_column(
        ForeignKey("warehouses.id"), nullable=False, index=True
    )
    location_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("warehouse_locations.id"),
        nullable=True,
        index=True,
    )
    inventory_state: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    quantity_delta: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    movement_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    source_line_id: Mapped[UUID | None] = mapped_column(nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    reason_code: Mapped[str | None] = mapped_column(String(50))
    reason_text: Mapped[str | None] = mapped_column(String(500))
    actor_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(255))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    reversal_of_movement_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("inventory_movements.id"),
        nullable=True,
    )


class InventoryBalance(UUIDPrimaryKeyMixin, Base):
    """Fast operational balance projection by location and state."""

    __tablename__ = "inventory_balances"
    __table_args__ = (
        UniqueConstraint(
            "seller_id",
            "product_id",
            "warehouse_id",
            "location_id",
            "inventory_state",
            name="uq_balance_composite_scope",
        ),
        CheckConstraint("quantity >= 0", name="ck_balance_non_negative"),
        Index("ix_balances_wh_product", "warehouse_id", "product_id"),
    )

    seller_id: Mapped[UUID] = mapped_column(ForeignKey("sellers.id"), nullable=False, index=True)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    warehouse_id: Mapped[UUID] = mapped_column(
        ForeignKey("warehouses.id"), nullable=False, index=True
    )
    location_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("warehouse_locations.id"),
        nullable=True,
        index=True,
    )
    inventory_state: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class InventoryAdjustment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Approval-driven inventory adjustment record."""

    __tablename__ = "inventory_adjustments"

    seller_id: Mapped[UUID] = mapped_column(ForeignKey("sellers.id"), nullable=False, index=True)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    warehouse_id: Mapped[UUID] = mapped_column(
        ForeignKey("warehouses.id"), nullable=False, index=True
    )
    location_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("warehouse_locations.id"), nullable=True
    )
    inventory_state: Mapped[str] = mapped_column(String(50), nullable=False)
    requested_delta: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(50), nullable=False)
    reason_text: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING_APPROVAL")
    requested_by_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    approved_by_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class InventoryReconciliation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Reconciliation snapshot and variance investigation record."""

    __tablename__ = "inventory_reconciliations"

    warehouse_id: Mapped[UUID] = mapped_column(
        ForeignKey("warehouses.id"), nullable=False, index=True
    )
    seller_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("sellers.id"), nullable=True, index=True
    )
    snapshot_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="COMPLETED")
    total_ledger_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_balance_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    variance_quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    investigated_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(String(1000))
