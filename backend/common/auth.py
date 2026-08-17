"""
Authentication and JWT helpers for token creation, password hashing, and user dependencies.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from common.logger import get_logger
from core.config.settings import get_settings

logger = get_logger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def hash_password(plain: str) -> str:
    """
    Hash a plain-text password for storage.

    Passwords are never stored or logged in plain text and are hashed using bcrypt.

    Args:
        plain: Plain-text password provided by the user.

    Returns:
        str: Bcrypt password hash.

    Raises:
        ValueError: If the password is empty.
    """
    if not plain:
        raise ValueError("Password cannot be empty")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plain-text password against a stored hash.

    Args:
        plain: Plain-text password submitted by the user.
        hashed: Stored bcrypt password hash.

    Returns:
        bool: True when the password matches the hash.
    """
    if not plain or not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(data: dict[str, Any]) -> str:
    """
    Create a signed JWT access token.

    The supplied payload is copied before adding an expiry timestamp so callers
    can safely reuse their original dictionary.

    Args:
        data: JWT payload fields such as user_id, email, role, and scopes.

    Returns:
        str: Encoded JWT access token.

    Raises:
        jose.JWTError: If the token cannot be encoded.
    """
    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = dict(data)
    payload["exp"] = expires_at
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a signed JWT access token.

    Invalid or expired tokens are normalized to an HTTP 401 without disclosing
    cryptographic validation details to the caller.

    Args:
        token: Bearer token value without the leading scheme.

    Returns:
        dict[str, Any]: Decoded JWT claims.

    Raises:
        HTTPException: If token validation fails.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError as error:
        logger.warning("Rejected invalid access token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        ) from error


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    """
    FastAPI dependency returning the authenticated JWT payload.

    Route handlers use this dependency for authentication and controllers remain
    responsible for business authorization decisions.

    Args:
        token: OAuth2 bearer token injected by FastAPI.

    Returns:
        dict[str, Any]: Authenticated user claims.

    Raises:
        HTTPException: If the token is invalid or missing required claims.
    """
    payload = decode_access_token(token)
    if not payload.get("user_id") or not payload.get("role"):
        logger.warning("Rejected token with missing required user claims")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    return payload
