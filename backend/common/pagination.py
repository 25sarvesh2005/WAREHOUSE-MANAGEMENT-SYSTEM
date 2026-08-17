"""
Pagination helpers for standard query parameter normalization.
"""

from __future__ import annotations


def normalize_pagination(limit: int = 50, offset: int = 0) -> tuple[int, int]:
    """
    Normalize pagination parameters.

    Limits are bounded to protect operational endpoints from accidental large
    table scans during the initial implementation.

    Args:
        limit: Requested page size.
        offset: Requested row offset.

    Returns:
        tuple[int, int]: Normalized limit and offset.

    Raises:
        ValueError: If limit or offset is invalid.
    """
    if limit < 1 or limit > 200:
        raise ValueError("Limit must be between 1 and 200")
    if offset < 0:
        raise ValueError("Offset cannot be negative")
    return limit, offset
