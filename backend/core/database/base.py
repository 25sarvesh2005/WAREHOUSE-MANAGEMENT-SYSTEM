"""
--------------------------------------------------------------------------------
File        : core/database/base.py
Purpose     : Define SQLAlchemy declarative base and shared model mixins.

Responsibilities:
    - Provide UUID and timestamp conventions for persisted models.
    - Keep PostgreSQL-friendly mapped type declarations in one place.

Flow:
    Model class definition
        ->
    Inherit Base/TimestampMixin
        ->
    Alembic and SQLAlchemy inspect metadata

Used By:
    - core/models
    - core/database/seed.py

Returns:
    Base.metadata - SQLAlchemy table metadata.

Raises:
    None.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDPrimaryKeyMixin:
    """Mixin that provides a PostgreSQL-generated UUID primary key."""

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )


class TimestampMixin:
    """Mixin that adds UTC creation and update timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
