"""
Pytest configuration and session fixtures for the Whitfield Warehouse test suite.
"""

from __future__ import annotations

import pytest
from core.database.database import close_database_connection, connect_to_database
from core.database.seed import initialize_schema_for_development, seed_initial_data


@pytest.fixture(autouse=True)
async def ensure_db():
    """Ensure database connection and cleanup for test runs."""
    await connect_to_database()
    yield
    await close_database_connection()
