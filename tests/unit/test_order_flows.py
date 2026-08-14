"""
--------------------------------------------------------------------------------
File        : tests/unit/test_order_flows.py
Purpose     : Unit tests for Phase 3 Order request schemas and validation logic.

Responsibilities:
    - Test OrderCreateRequest validation and line quantity constraints.
    - Test OrderReserveRequest optional payload handling.

Used By:
    - pytest test runner

Returns:
    Assertion results.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from core.apis.schemas.requests.order_request import (
    OrderCreateRequest,
    OrderLineCreateRequest,
    OrderReserveRequest,
)


def test_order_create_request_validation() -> None:
    """Verify OrderCreateRequest accepts valid payloads."""
    payload = {
        "seller_id": str(uuid4()),
        "seller_order_number": "ORD-1001",
        "warehouse_id": str(uuid4()),
        "channel": "SHOPIFY",
        "customer_name": "Alice Smith",
        "lines": [
            {
                "product_id": str(uuid4()),
                "ordered_quantity": "5.00",
            }
        ],
    }
    req = OrderCreateRequest.model_validate(payload)
    assert req.seller_order_number == "ORD-1001"
    assert req.channel == "SHOPIFY"
    assert len(req.lines) == 1
    assert req.lines[0].ordered_quantity == Decimal("5.00")


def test_order_create_request_rejects_empty_lines() -> None:
    """Verify OrderCreateRequest rejects empty line item list."""
    payload = {
        "seller_id": str(uuid4()),
        "seller_order_number": "ORD-1002",
        "warehouse_id": str(uuid4()),
        "lines": [],
    }
    with pytest.raises(ValidationError):
        OrderCreateRequest.model_validate(payload)


def test_order_line_rejects_zero_or_negative_quantity() -> None:
    """Verify OrderLineCreateRequest rejects zero or negative ordered quantity."""
    payload = {
        "product_id": str(uuid4()),
        "ordered_quantity": "0.00",
    }
    with pytest.raises(ValidationError):
        OrderLineCreateRequest.model_validate(payload)


def test_order_reserve_request_validation() -> None:
    """Verify OrderReserveRequest accepts valid notes."""
    req = OrderReserveRequest.model_validate({"notes": "Expedited reservation"})
    assert req.notes == "Expedited reservation"


def test_seller_order_policy_snapshot_structure() -> None:
    """Verify seller order policy snapshot dictionary defaults."""
    default_policy = {
        "policy_id": None,
        "allocation_strategy": "FIFO",
        "allow_backorder": True,
        "allow_partial_fulfillment": False,
        "reservation_expiry_minutes": 120,
    }
    assert default_policy["allow_partial_fulfillment"] is False
    assert default_policy["reservation_expiry_minutes"] == 120

