"""
--------------------------------------------------------------------------------
File        : core/database/database.py
Purpose     : Manage async PostgreSQL engine and session lifecycle.

Responsibilities:
    - Create and dispose the SQLAlchemy async engine.
    - Expose transaction helpers for controller-owned units of work.

Flow:
    FastAPI lifespan startup
        ->
    connect_to_database()
        ->
    Controllers call transaction_session()
        ->
    FastAPI lifespan shutdown closes engine

Used By:
    - main.py
    - core/controllers
    - scripts and CLI commands

Returns:
    transaction_session() -> AsyncIterator[AsyncSession] - Transactional session.

Raises:
    RuntimeError: When session access occurs before database connection.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from common.logger import get_logger
from core.config.settings import get_settings

logger = get_logger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


async def connect_to_database() -> None:
    """
    Create the async SQLAlchemy engine and session factory.

    The connection pool is configured from environment settings and is reused
    until application shutdown.

    Returns:
        None.

    Raises:
        Exception: If the database engine cannot be created.
    """
    global _engine, _session_factory
    if _engine is not None and _session_factory is not None:
        return

    settings = get_settings()
    logger.info("Connecting to PostgreSQL database")
    if settings.app_env in ("test", "testing") or "pytest" in sys.modules:
        _engine = create_async_engine(
            settings.runtime_database_url,
            poolclass=NullPool,
            connect_args={"prepared_statement_cache_size": 0},
        )
    else:
        _engine = create_async_engine(
            settings.runtime_database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,
            connect_args={"prepared_statement_cache_size": 0},
        )
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def close_database_connection() -> None:
    """
    Dispose the async SQLAlchemy engine.

    Shutdown resets module-level state so tests and CLI runs can reconnect
    cleanly in the same Python process.

    Returns:
        None.

    Raises:
        Exception: If engine disposal fails.
    """
    global _engine, _session_factory
    if _engine is not None:
        logger.info("Closing PostgreSQL database connection")
        await _engine.dispose()
    _engine = None
    _session_factory = None


def get_engine() -> AsyncEngine:
    """
    Return the initialized async SQLAlchemy engine.

    Controllers, migrations, and diagnostics can use this accessor after
    application startup has connected to the database.

    Returns:
        AsyncEngine: Active SQLAlchemy async engine.

    Raises:
        RuntimeError: If called before connect_to_database().
    """
    if _engine is None:
        raise RuntimeError("Database engine is not initialized")
    return _engine


@asynccontextmanager
async def transaction_session() -> AsyncIterator[AsyncSession]:
    """
    Yield an AsyncSession wrapped in a transaction.

    The session commits on successful exit and rolls back automatically when
    an exception escapes the controller workflow.

    Yields:
        AsyncSession: Transaction-scoped database session.

    Raises:
        RuntimeError: If the session factory is not initialized.
        Exception: Re-raises database or workflow failures after rollback.
    """
    if _session_factory is None:
        raise RuntimeError("Database session factory is not initialized")

    async with _session_factory() as session:
        async with session.begin():
            yield session


async def check_database_ready() -> bool:
    """
    Verify that PostgreSQL can execute a trivial query.

    This function is used by readiness checks and avoids exposing connection
    details in HTTP responses or logs.

    Returns:
        bool: True when the database responds successfully.

    Raises:
        Exception: If the readiness query fails.
    """
    async with transaction_session() as session:
        await session.execute(text("SELECT 1"))
    return True
