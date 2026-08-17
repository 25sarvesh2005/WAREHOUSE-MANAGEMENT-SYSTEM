"""
Starlette middleware that attaches a correlation request ID to every HTTP request.

The ID is read from the incoming ``X-Request-ID`` header when supplied by a
load balancer or API gateway. A new UUID4 is generated when the header is
absent so every request is always traceable end-to-end.

The resolved ID is:
  - Stored on ``request.state.request_id`` for use by route handlers.
  - Echoed back to the caller in the ``X-Request-ID`` response header.
  - Available to downstream logging via ``contextvars`` so log lines can be
    tagged without passing the ID through every function signature.

Flow:
    Incoming HTTP request
        ->
    RequestIDMiddleware reads / generates ID
        ->
    Stores ID in request.state and context var
        ->
    Route handler executes
        ->
    Response carries X-Request-ID header out

Used By:
    - main.py (registered as ASGI middleware)
    - common/logger.py (can read REQUEST_ID_CTX_VAR for structured logging)
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from common.logger import get_logger

logger = get_logger(__name__)

# Context variable that holds the request ID for the duration of a single
# async task / request.  Other modules may import and read this var.
REQUEST_ID_CTX_VAR: ContextVar[str] = ContextVar("request_id", default="-")

_HEADER_NAME = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that injects a per-request correlation ID.

    Reads the caller-supplied ``X-Request-ID`` header or generates a new UUID4.
    The resolved ID is available via ``request.state.request_id`` inside route
    handlers and via ``REQUEST_ID_CTX_VAR`` in any async context during the
    request lifecycle.
    """

    async def dispatch(self, request: Request, call_next: object) -> Response:
        """Inject a correlation request ID and propagate it to the response.

        Args:
            request: Incoming Starlette request.
            call_next: ASGI call-next middleware callable.

        Returns:
            Response: Original response with ``X-Request-ID`` header appended.

        Raises:
            None: All exceptions are allowed to propagate to the next handler.
        """
        raw_id = request.headers.get(_HEADER_NAME, "").strip()
        request_id = raw_id if raw_id else str(uuid.uuid4())

        # Store on request state for route handlers
        request.state.request_id = request_id

        # Store in context var for logger access without passing through params
        token = REQUEST_ID_CTX_VAR.set(request_id)

        try:
            response: Response = await call_next(request)
        finally:
            REQUEST_ID_CTX_VAR.reset(token)

        response.headers[_HEADER_NAME] = request_id
        return response
