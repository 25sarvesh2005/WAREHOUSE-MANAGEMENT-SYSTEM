"""
--------------------------------------------------------------------------------
File        : core/models/catalog_model.py
Purpose     : Define catalog, warehouse location, and seller policy tables.

Responsibilities:
    - Store products and product identifiers by seller.
    - Store warehouse locations and configurable seller order policies.

Flow:
    Admin request
        ->
    Catalog controller validates scope
        ->
    Catalog CRUD persists SQLAlchemy models

Used By:
    - core/cruds/catalog_crud.py

Returns:
    SQLAlchemy model instances - Catalog persistence records.

Raises:
    sqlalchemy.exc.IntegrityError: On uniqueness or foreign-key violations.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.constants import DEFAULT_RESERVATION_EXPIRY_MINUTES
from core.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Product(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Persisted seller product/SKU master-data record."""

    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("seller_id", "sku", name="uq_product_seller_sku"),)

    seller_id: Mapped[UUID] = mapped_column(ForeignKey("sellers.id"), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))
    unit_of_measure: Mapped[str] = mapped_column(String(50), nullable=False, default="EA")
    weight: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    length: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    width: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    height: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    identifiers: Mapped[list[ProductIdentifier]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )


class ProductIdentifier(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Persisted alternate identifier for a product."""

    __tablename__ = "product_identifiers"
    __table_args__ = (
        UniqueConstraint(
            "identifier_type",
            "identifier_value",
            name="uq_product_identifier_type_value",
        ),
    )

    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    identifier_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    identifier_value: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    product: Mapped[Product] = relationship(back_populates="identifiers")


class WarehouseLocation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Persisted addressable or workflow warehouse location."""

    __tablename__ = "warehouse_locations"
    __table_args__ = (UniqueConstraint("warehouse_id", "code", name="uq_location_warehouse_code"),)

    warehouse_id: Mapped[UUID] = mapped_column(
        ForeignKey("warehouses.id"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    location_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)


class SellerOrderPolicy(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Persisted seller order policy version."""

    __tablename__ = "seller_order_policies"

    seller_id: Mapped[UUID] = mapped_column(ForeignKey("sellers.id"), nullable=False, index=True)
    allow_backorder: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_partial_fulfillment: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reservation_expiry_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=DEFAULT_RESERVATION_EXPIRY_MINUTES,
    )
    allocation_strategy: Mapped[str] = mapped_column(String(50), nullable=False)
    cancellation_policy: Mapped[str | None] = mapped_column(String(500))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
