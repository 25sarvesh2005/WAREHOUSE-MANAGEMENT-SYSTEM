"""
Pytest configuration and session fixtures for the Whitfield Warehouse test suite.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from core.database.database import close_database_connection, connect_to_database, transaction_session
from core.database.seed import initialize_schema_for_development, seed_initial_data


_SCHEMA_INITIALIZED = False


@pytest.fixture(autouse=True)
async def ensure_db():
    """Ensure database connection, schema, and seed exist for test runs."""
    global _SCHEMA_INITIALIZED
    await connect_to_database()
    if not _SCHEMA_INITIALIZED:
        try:
            async with transaction_session() as session:
                await session.execute(
                    text(
                        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                        "WHERE pid <> pg_backend_pid() AND state = 'idle in transaction' "
                        "AND datname = current_database();"
                    )
                )
        except Exception:
            pass
        await initialize_schema_for_development()
        await seed_initial_data()
        _SCHEMA_INITIALIZED = True
    yield
