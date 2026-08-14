"""
--------------------------------------------------------------------------------
File        : tests/unit/test_auth_flows.py
Purpose     : Test authentication token helper behavior and schema contracts.

Responsibilities:
    - Validate JWT creation and decoding round-trips.
    - Validate password hash and verify behavior.
    - Validate TokenResponse schema includes both token fields.
    - Validate RefreshRequest schema enforces minimum length.

Flow:
    pytest
        ->
    Pure helper / schema functions
        ->
    Assertion

Used By:
    - pytest

Returns:
    test_*() -> None - Pytest assertions.

Raises:
    AssertionError: When helper or schema behavior regresses.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import pytest

from common.auth import create_access_token, decode_access_token, hash_password, verify_password
from core.apis.schemas.requests.identity_request import RefreshRequest
from core.apis.schemas.responses.identity_response import TokenResponse
from core.config.settings import Settings


def test_hash_and_verify_password_round_trip() -> None:
    """
    Verify that hash_password produces a hash that verify_password accepts.

    Password storage must never expose the plain-text value, so the hash and
    verify cycle is the only path that should confirm correctness.

    Returns:
        None.

    Raises:
        AssertionError: If the hash/verify round-trip fails.
    """
    plain = "S3cur3P@ssw0rd!"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed) is True


def test_verify_password_rejects_wrong_value() -> None:
    """
    Verify that an incorrect password fails verification.

    Security depends on verify_password returning False for any input that does
    not match the stored hash.

    Returns:
        None.

    Raises:
        AssertionError: If an incorrect password is accepted.
    """
    hashed = hash_password("correct_password_123")
    assert verify_password("wrong_password_456", hashed) is False


def test_hash_password_rejects_empty_string() -> None:
    """
    Verify that hash_password raises ValueError for empty input.

    Storing empty-password hashes would allow bypass attacks if the empty string
    ever matched a stored hash.

    Returns:
        None.

    Raises:
        AssertionError: If an empty password is accepted.
    """
    with pytest.raises(ValueError):
        hash_password("")


def test_access_token_round_trip() -> None:
    """
    Verify that create_access_token produces a token decode_access_token accepts.

    The JWT contract requires user_id and role to be present in the decoded
    payload for the get_current_user dependency to accept the token.

    Returns:
        None.

    Raises:
        AssertionError: If the JWT encode/decode round-trip fails.
    """
    settings = Settings(
        jwt_secret="test-secret-that-is-long-enough-to-use-in-unit-tests",
        database_url=(
            "postgresql+asyncpg://postgres.ref:secret@"
            "aws-0-region.pooler.supabase.com:5432/postgres"
        ),
    )
    # Override the settings used by create_access_token for this test
    from core.config import settings as settings_module

    settings_module.get_settings.cache_clear()
    import os

    original = os.environ.get("JWT_SECRET")
    os.environ["JWT_SECRET"] = settings.jwt_secret

    try:
        payload = {
            "user_id": "00000000-0000-0000-0000-000000000001",
            "email": "test@example.com",
            "role": "ADMINISTRATOR",
            "seller_ids": [],
            "warehouse_ids": [],
            "token_version": 0,
        }
        token = create_access_token(payload)
        assert isinstance(token, str)
        assert len(token) > 50

        decoded = decode_access_token(token)
        assert decoded["user_id"] == payload["user_id"]
        assert decoded["role"] == payload["role"]
        assert "exp" in decoded
    finally:
        if original is None:
            os.environ.pop("JWT_SECRET", None)
        else:
            os.environ["JWT_SECRET"] = original
        settings_module.get_settings.cache_clear()


def test_token_response_schema_includes_refresh_token() -> None:
    """
    Verify that TokenResponse requires and serializes the refresh_token field.

    The frontend depends on receiving both tokens in a single login response to
    set up automatic access-token renewal.

    Returns:
        None.

    Raises:
        AssertionError: If the schema does not include the refresh_token field.
    """
    response = TokenResponse(
        access_token="access.token.here",
        refresh_token="raw-refresh-token-here",
    )
    assert response.access_token == "access.token.here"
    assert response.refresh_token == "raw-refresh-token-here"
    assert response.token_type == "bearer"

    data = response.model_dump()
    assert "access_token" in data
    assert "refresh_token" in data
    assert "token_type" in data


def test_token_response_schema_requires_refresh_token() -> None:
    """
    Verify that TokenResponse raises a validation error when refresh_token is missing.

    Omitting the refresh_token field from a token response would break the
    frontend's session-renewal flow silently.

    Returns:
        None.

    Raises:
        AssertionError: If a TokenResponse without refresh_token is accepted.
    """
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        TokenResponse(access_token="access.token.here")  # type: ignore[call-arg]


def test_refresh_request_schema_rejects_empty_token() -> None:
    """
    Verify that RefreshRequest rejects empty or whitespace-only token values.

    An empty refresh_token field should never reach the controller because the
    schema layer is the first line of defense against malformed requests.

    Returns:
        None.

    Raises:
        AssertionError: If an empty token is accepted.
    """
    import pydantic

    with pytest.raises(pydantic.ValidationError):
        RefreshRequest(refresh_token="")


def test_refresh_request_schema_accepts_valid_token() -> None:
    """
    Verify that RefreshRequest accepts a well-formed token string.

    The refresh endpoint must not reject legitimate token values that fall
    within the declared length constraints.

    Returns:
        None.

    Raises:
        AssertionError: If a valid token is rejected.
    """
    token = "a" * 86  # typical urlsafe_b64 token from secrets.token_urlsafe(64)
    request = RefreshRequest(refresh_token=token)
    assert request.refresh_token == token
