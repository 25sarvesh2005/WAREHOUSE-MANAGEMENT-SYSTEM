"""
--------------------------------------------------------------------------------
File        : core/models/identity_model.py
Purpose     : Define identity, tenant, and warehouse access tables.

Responsibilities:
    - Store users, sellers, warehouses, and assignment records.
    - Preserve role and active-scope relationships for authorization.

Flow:
    Controller request
        ->
    CRUD persists identity model
        ->
    JWT and scope helpers derive allowed access

Used By:
    - core/cruds/identity_crud.py
    - core/database/seed.py

Returns:
    SQLAlchemy model instances - Identity persistence records.

Raises:
    sqlalchemy.exc.IntegrityError: On uniqueness or foreign-key violations.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Persisted application user account."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, index=True
    )

    seller_assignments: Mapped[list[UserSellerAssignment]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    warehouse_assignments: Mapped[list[UserWarehouseAssignment]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Seller(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Persisted seller tenant record."""

    __tablename__ = "sellers"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(320))
    contact_phone: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    user_assignments: Mapped[list[UserSellerAssignment]] = relationship(back_populates="seller")


class Warehouse(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Persisted shared warehouse facility record."""

    __tablename__ = "warehouses"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address_line1: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    postal_code: Mapped[str | None] = mapped_column(String(30))
    timezone: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    user_assignments: Mapped[list[UserWarehouseAssignment]] = relationship(
        back_populates="warehouse"
    )


class UserSellerAssignment(UUIDPrimaryKeyMixin, Base):
    """Active or historical seller assignment for a user."""

    __tablename__ = "user_seller_assignments"
    __table_args__ = (
        UniqueConstraint("user_id", "seller_id", "assignment_role", name="uq_user_seller_role"),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    seller_id: Mapped[UUID] = mapped_column(ForeignKey("sellers.id"), nullable=False, index=True)
    assignment_role: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="seller_assignments")
    seller: Mapped[Seller] = relationship(back_populates="user_assignments")


class UserWarehouseAssignment(UUIDPrimaryKeyMixin, Base):
    """Active or historical warehouse assignment for a user."""

    __tablename__ = "user_warehouse_assignments"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "warehouse_id",
            "assignment_role",
            name="uq_user_warehouse_role",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    warehouse_id: Mapped[UUID] = mapped_column(
        ForeignKey("warehouses.id"),
        nullable=False,
        index=True,
    )
    assignment_role: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="warehouse_assignments")
    warehouse: Mapped[Warehouse] = relationship(back_populates="user_assignments")


class RefreshToken(UUIDPrimaryKeyMixin, Base):
    """Persisted hashed refresh token for session renewal."""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped[User] = relationship()
