"""
--------------------------------------------------------------------------------
File        : common/idempotency.py
Purpose     : Provide reusable idempotency-key validation helpers.

Responsibilities:
    - Normalize caller-provided idempotency keys.
    - Reject empty keys before they reach transactional workflows.

Flow:
    Route or controller input
        ->
    normalize_idempotency_key()
        ->
    Workflow-specific duplicate-safe operation

Used By:
    - future receiving, order, transfer, and return controllers

Returns:
    normalize_idempotency_key() -> str - Normalized key.

Raises:
    ValueError: When a required idempotency key is missing.
--------------------------------------------------------------------------------
"""

from __future__ import annotations


def normalize_idempotency_key(value: str | None) -> str:
    """
    Normalize an externally retryable command idempotency key.

    The key is stripped of surrounding whitespace and must remain non-empty so
    future workflows can safely enforce duplicate protection.

    Args:
        value: Caller-provided idempotency key.

    Returns:
        str: Normalized idempotency key.

    Raises:
        ValueError: If the key is missing or empty.
    """
    normalized = (value or "").strip()
    if not normalized:
        raise ValueError("Idempotency key is required")
    return normalized
