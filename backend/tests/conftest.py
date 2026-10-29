"""
Pytest configuration and session fixtures for the Whitfield Warehouse test suite.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from core.database.database import connect_to_database, transaction_session
from core.database.seed import initialize_schema_for_development, seed_initial_data


_SCHEMA_INITIALIZED = False
_DB_AVAILABLE = False


@pytest.fixture(autouse=True)
async def ensure_db(request: pytest.FixtureRequest):
    """Ensure database connection, schema, and seed exist when DB is available."""
    global _SCHEMA_INITIALIZED, _DB_AVAILABLE
    
    # If the test is purely a non-db unit test, don't fail fixture if DB is down
    try:
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
        _DB_AVAILABLE = True
    except Exception as err:
        _DB_AVAILABLE = False
        db_required_modules = {
            "test_background_jobs",
            "test_mcp_tools",
            "test_outbox_flows",
            "test_system_flaw_fixes",
            "test_voice_receiving_flows",
        }
        mod_name = request.module.__name__.split(".")[-1] if request.module else ""
        if request.node.get_closest_marker("db") is not None or mod_name in db_required_modules:
            pytest.skip(f"Live database connection unavailable: {err}")
    yield

