"""
--------------------------------------------------------------------------------
File        : common/rate_limit.py
Purpose     : In-memory sliding-window rate limiting dependency.

Responsibilities:
    - Track request frequency per client IP or authenticated user key.
    - Reject abusive traffic with HTTP 429 Too Many Requests.
    - Provide preconfigured limits for sensitive endpoints (auth, AI, migrations).

Flow:
    HTTP request -> FastAPI Depends(rate_limiter) -> check window -> proceed or 429

Used By:
    - core/apis/routes/identity_routes.py
    - core/apis/routes/ai_routes.py
    - core/apis/routes/migration_routes.py

Returns:
    None if within limit.

Raises:
    HTTPException: 429 Too Many Requests when rate threshold is exceeded.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock
from typing import Callable

from fastapi import HTTPException, Request, status

from common.logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """Sliding-window in-memory rate limiter for FastAPI routes."""

    def __init__(
        self,
        *,
        max_requests: int,
        window_seconds: int,
        key_func: Callable[[Request], str] | None = None,
        error_message: str = "Rate limit exceeded. Please try again later.",
    ) -> None:
        """
        Initialize rate limiter parameters.

        Args:
            max_requests: Maximum requests allowed within the window.
            window_seconds: Duration of the sliding window in seconds.
            key_func: Optional callable to extract rate limit key from Request.
            error_message: Error detail to return on 429.
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.key_func = key_func or self._default_key_func
        self.error_message = error_message
        self._records: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    @staticmethod
    def _default_key_func(request: Request) -> str:
        """
        Default key extractor using client host and forwarded-for header.

        Args:
            request: FastAPI Request instance.

        Returns:
            str: Identifier key.
        """
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        client = request.client
        return client.host if client else "unknown"

    async def __call__(self, request: Request) -> None:
        """
        FastAPI dependency handler.

        Args:
            request: FastAPI Request instance.

        Raises:
            HTTPException: 429 Too Many Requests if limit exceeded.
        """
        key = self.key_func(request)
        now = time.time()
        cutoff = now - self.window_seconds

        with self._lock:
            queue = self._records[key]
            while queue and queue[0] < cutoff:
                queue.popleft()

            if len(queue) >= self.max_requests:
                oldest = queue[0]
                retry_after = max(1, int(oldest + self.window_seconds - now))
                logger.warning(
                    "Rate limit exceeded for key %s (path: %s). Retry after: %ss",
                    key,
                    request.url.path,
                    retry_after,
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=self.error_message,
                    headers={"Retry-After": str(retry_after)},
                )

            queue.append(now)


_login_rate_limiter = RateLimiter(
    max_requests=10,
    window_seconds=60,
    error_message="Too many login attempts. Please wait before trying again.",
)

_refresh_rate_limiter = RateLimiter(
    max_requests=20,
    window_seconds=60,
    error_message="Too many token refresh requests. Please wait.",
)

_ai_rate_limiter = RateLimiter(
    max_requests=40,
    window_seconds=60,
    error_message="Too many AI requests. Please slow down.",
)

_migration_upload_rate_limiter = RateLimiter(
    max_requests=15,
    window_seconds=60,
    error_message="Too many migration batch submissions. Please wait.",
)

_voice_rate_limiter = RateLimiter(
    max_requests=20,
    window_seconds=60,
    error_message="Too many voice requests. Please wait before speaking again.",
)

_voice_upload_rate_limiter = RateLimiter(
    max_requests=10,
    window_seconds=60,
    error_message="Too many audio uploads. Please wait.",
)


async def login_rate_limiter(request: Request) -> None:
    """
    Apply the configured login rate limit.

    Args:
        request: FastAPI request object.

    Returns:
        None.

    Raises:
        HTTPException: If the requester exceeds the login rate limit.
    """
    await _login_rate_limiter(request)


async def refresh_rate_limiter(request: Request) -> None:
    """
    Apply the configured token-refresh rate limit.

    Args:
        request: FastAPI request object.

    Returns:
        None.

    Raises:
        HTTPException: If the requester exceeds the refresh rate limit.
    """
    await _refresh_rate_limiter(request)


async def ai_rate_limiter(request: Request) -> None:
    """
    Apply the configured AI endpoint rate limit.

    Args:
        request: FastAPI request object.

    Returns:
        None.

    Raises:
        HTTPException: If the requester exceeds the AI rate limit.
    """
    await _ai_rate_limiter(request)


async def migration_upload_rate_limiter(request: Request) -> None:
    """
    Apply the configured migration upload/submission rate limit.

    Args:
        request: FastAPI request object.

    Returns:
        None.

    Raises:
        HTTPException: If the requester exceeds the migration rate limit.
    """
    await _migration_upload_rate_limiter(request)


async def voice_rate_limiter(request: Request) -> None:
    """
    Apply the configured voice request rate limit.

    Args:
        request: FastAPI request object.

    Returns:
        None.

    Raises:
        HTTPException: If the requester exceeds the voice rate limit.
    """
    await _voice_rate_limiter(request)


async def voice_upload_rate_limiter(request: Request) -> None:
    """
    Apply the configured voice audio upload rate limit.

    Args:
        request: FastAPI request object.

    Returns:
        None.

    Raises:
        HTTPException: If the requester exceeds the voice upload rate limit.
    """
    await _voice_upload_rate_limiter(request)
