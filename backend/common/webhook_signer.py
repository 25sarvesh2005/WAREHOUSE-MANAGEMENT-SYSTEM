"""
Cryptographic signing and verification utilities for webhook delivery security.
Enforces HMAC-SHA256 signatures and timestamp replay-attack protection.
"""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import hmac
import time


def compute_webhook_signature(payload_bytes: bytes, secret: str) -> str:
    """
    Compute an HMAC-SHA256 hex signature over the raw payload bytes.

    Args:
        payload_bytes: Exact UTF-8 encoded bytes sent in the HTTP request body.
        secret: Pre-shared subscription signing secret.

    Returns:
        Formatted signature string: 'sha256=<hex_digest>'
    """
    mac = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256)
    return f"sha256={mac.hexdigest()}"


def verify_webhook_signature(payload_bytes: bytes, signature_header: str | None, secret: str) -> bool:
    """
    Verify an inbound or outbound HMAC-SHA256 signature using constant-time comparison.

    Args:
        payload_bytes: Raw HTTP request body bytes.
        signature_header: Header value containing 'sha256=<hex_digest>'.
        secret: Pre-shared subscription signing secret.

    Returns:
        True if valid; False otherwise.
    """
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = compute_webhook_signature(payload_bytes, secret)
    return hmac.compare_digest(expected, signature_header)


def verify_webhook_timestamp(timestamp_header: str | None, max_drift_seconds: int = 300) -> bool:
    """
    Verify that the webhook request timestamp is within tolerance to prevent replay attacks.

    Args:
        timestamp_header: ISO-8601 string or Unix timestamp epoch seconds string.
        max_drift_seconds: Maximum allowed clock drift (default 300s / 5 mins).

    Returns:
        True if timestamp is within tolerance; False otherwise.
    """
    if not timestamp_header:
        return False
    try:
        if timestamp_header.isdigit():
            epoch = int(timestamp_header)
        else:
            dt = datetime.fromisoformat(timestamp_header.replace("Z", "+00:00"))
            epoch = int(dt.timestamp())
        now = int(time.time())
        return abs(now - epoch) <= max_drift_seconds
    except Exception:
        return False

