"""
--------------------------------------------------------------------------------
File        : tests/unit/test_common_helpers.py
Purpose     : Test pure common helper behavior.

Responsibilities:
    - Validate pagination bounds.
    - Validate idempotency-key normalization.

Flow:
    pytest
        ->
    Pure helper function
        ->
    Assertion

Used By:
    - pytest

Returns:
    test_*() -> None - Pytest assertions.

Raises:
    AssertionError: When helper behavior regresses.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import pytest

from common.idempotency import normalize_idempotency_key
from common.pagination import normalize_pagination
from core.config.settings import Settings


def test_normalize_pagination_accepts_valid_bounds() -> None:
    """
    Verify valid pagination values are returned unchanged.

    The helper should preserve caller intent when limit and offset are inside
    the accepted operational range.

    Returns:
        None.

    Raises:
        AssertionError: If pagination values are altered unexpectedly.
    """
    assert normalize_pagination(limit=100, offset=25) == (100, 25)


def test_normalize_pagination_rejects_invalid_limit() -> None:
    """
    Verify invalid page sizes are rejected.

    A too-large limit should fail before a controller can send an unbounded
    query to the database.

    Returns:
        None.

    Raises:
        AssertionError: If invalid pagination is accepted.
    """
    with pytest.raises(ValueError):
        normalize_pagination(limit=201, offset=0)


def test_normalize_idempotency_key_strips_whitespace() -> None:
    """
    Verify idempotency keys are normalized before workflow use.

    Whitespace-only differences should not create distinct retry keys for future
    duplicate-safe workflows.

    Returns:
        None.

    Raises:
        AssertionError: If key normalization regresses.
    """
    assert normalize_idempotency_key("  receipt-123  ") == "receipt-123"


def test_normalize_idempotency_key_rejects_empty_value() -> None:
    """
    Verify empty idempotency keys are rejected.

    Retryable workflows must fail fast when callers omit the key needed for
    duplicate-safe command handling.

    Returns:
        None.

    Raises:
        AssertionError: If empty keys are accepted.
    """
    with pytest.raises(ValueError):
        normalize_idempotency_key("   ")


def test_settings_normalize_database_drivers() -> None:
    """
    Verify runtime and migration URLs use their required drivers.

    A direct Supabase URL without an explicit SQLAlchemy driver should become
    asyncpg for application traffic and psycopg for Alembic.

    Returns:
        None.

    Raises:
        AssertionError: If database URL normalization selects a wrong driver.
    """
    settings = Settings(
        database_url="postgresql://postgres:secret@db.example.supabase.co:5432/postgres",
    )

    assert settings.runtime_database_url.startswith("postgresql+asyncpg://")
    assert settings.alembic_database_url.startswith("postgresql+psycopg://")


def test_settings_prefer_migration_database_url() -> None:
    """
    Verify a dedicated migration connection overrides the runtime URL.

    Persistent application traffic may use Supavisor session mode while Alembic
    retains a direct PostgreSQL connection.

    Returns:
        None.

    Raises:
        AssertionError: If Alembic ignores the dedicated migration URL.
    """
    settings = Settings(
        database_url=(
            "postgresql+asyncpg://postgres.ref:secret@"
            "aws-0-region.pooler.supabase.com:5432/postgres"
        ),
        migration_database_url=(
            "postgresql+psycopg://postgres:secret@db.ref.supabase.co:5432/postgres"
        ),
    )

    assert "aws-0-region.pooler.supabase.com" in settings.runtime_database_url
    assert "db.ref.supabase.co" in settings.alembic_database_url


def test_settings_reject_transaction_pooler_for_persistent_runtime() -> None:
    """
    Verify port 6543 is rejected for this persistent backend runtime.

    Transaction pooling is reserved for a future explicit serverless deployment
    because prepared-statement and session behavior differ from this design.

    Returns:
        None.

    Raises:
        AssertionError: If a transaction-pooler URL is accepted.
    """
    settings = Settings(
        database_url=(
            "postgresql+asyncpg://postgres.ref:secret@"
            "aws-0-region.pooler.supabase.com:6543/postgres"
        ),
    )

    with pytest.raises(ValueError, match="transaction pooling"):
        _ = settings.runtime_database_url


def test_production_config_validation_rejects_weak_secrets() -> None:
    """Verify validate_production_configuration rejects weak secrets in production."""
    from core.config.settings import validate_production_configuration

    prod_settings = Settings(
        app_env="production",
        jwt_secret="short-secret",
        bootstrap_admin_password="change-this-before-use",
        ai_enabled=True,
        ai_provider="google_genai",
        google_genai_api_key="",
    )

    with pytest.raises(ValueError, match="JWT_SECRET"):
        validate_production_configuration(prod_settings)

    dev_settings = Settings(
        app_env="development",
        jwt_secret="short-secret",
        bootstrap_admin_password="change-this-before-use",
        ai_enabled=False,
    )
    warnings = validate_production_configuration(dev_settings)
    assert len(warnings) >= 2


@pytest.mark.asyncio
async def test_rate_limiter_blocks_excessive_requests() -> None:
    """Verify RateLimiter raises 429 when threshold exceeded."""
    from unittest.mock import MagicMock
    from fastapi import HTTPException
    from common.rate_limit import RateLimiter

    limiter = RateLimiter(max_requests=2, window_seconds=60)
    mock_request = MagicMock()
    mock_request.client.host = "192.168.1.100"
    mock_request.headers = {}
    mock_request.url.path = "/test"

    # Request 1 & 2 pass
    await limiter(mock_request)
    await limiter(mock_request)

    # Request 3 fails with 429
    with pytest.raises(HTTPException) as exc_info:
        await limiter(mock_request)
    assert exc_info.value.status_code == 429
    assert "Retry-After" in exc_info.value.headers

