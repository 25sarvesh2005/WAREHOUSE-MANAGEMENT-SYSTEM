"""
--------------------------------------------------------------------------------
File        : tests/unit/test_fulfillment_flows.py
Purpose     : Unit tests for Phase 3 Fulfillment request schemas.

Responsibilities:
    - Test PickTaskCreateRequest, PickTaskCompleteRequest, and ShipmentCreateRequest payloads.

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

from core.apis.schemas.requests.fulfillment_request import (
    PickTaskCompleteRequest,
    PickTaskCreateRequest,
    ShipmentCreateRequest,
)


def test_pick_task_create_request_validation() -> None:
    """Verify PickTaskCreateRequest accepts valid parameters."""
    order_id = uuid4()
    req = PickTaskCreateRequest.model_validate({"order_id": str(order_id), "priority": 3})
    assert req.order_id == order_id
    assert req.priority == 3


def test_pick_task_complete_request_validation() -> None:
    """Verify PickTaskCompleteRequest validates line results."""
    line_id = uuid4()
    payload = {
        "lines": [
            {
                "pick_task_line_id": str(line_id),
                "picked_quantity": "10.00",
                "short_quantity": "2.00",
            }
        ]
    }
    req = PickTaskCompleteRequest.model_validate(payload)
    assert len(req.lines) == 1
    assert req.lines[0].picked_quantity == Decimal("10.00")
    assert req.lines[0].short_quantity == Decimal("2.00")


def test_shipment_create_request_validation() -> None:
    """Verify ShipmentCreateRequest validates manual shipment dispatch payload."""
    payload = {
        "order_id": str(uuid4()),
        "warehouse_id": str(uuid4()),
        "carrier": "UPS",
        "service_level": "NEXT_DAY_AIR",
        "tracking_number": "1Z9999999999999999",
        "packages": [
            {
                "box_type": "MEDIUM_BOX",
                "weight_lbs": "4.50",
            }
        ],
    }
    req = ShipmentCreateRequest.model_validate(payload)
    assert req.carrier == "UPS"
    assert req.tracking_number == "1Z9999999999999999"
    assert len(req.packages) == 1
    assert req.packages[0].weight_lbs == Decimal("4.50")
