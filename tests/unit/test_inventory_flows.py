"""
--------------------------------------------------------------------------------
File        : tests/unit/test_inventory_flows.py
Purpose     : Test inventory schema and request validation.

Responsibilities:
    - Validate inventory request parameters and response schemas.

Flow:
    pytest -> Inventory schemas -> Assertion

Used By:
    - pytest

Returns:
    test_*() -> None - Pytest assertions.

Raises:
    AssertionError: If validation fails.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from core.apis.schemas.requests.inventory_request import ReconciliationRequest
from core.apis.schemas.responses.inventory_response import InventoryBalanceResponse
from core.constants import InventoryMovementType, InventoryState


def test_reconciliation_request_validation() -> None:
    """Verify ReconciliationRequest validation."""
    wh_id = uuid4()
    req = ReconciliationRequest(warehouse_id=wh_id, notes="Monthly audit check")
    assert req.warehouse_id == wh_id
    assert req.notes == "Monthly audit check"


def test_inventory_state_and_type_enums() -> None:
    """Verify InventoryState and InventoryMovementType values."""
    assert InventoryState.AVAILABLE.value == "AVAILABLE"
    assert InventoryState.DAMAGED.value == "DAMAGED"
    assert InventoryState.QUARANTINED.value == "QUARANTINED"
    assert InventoryMovementType.RECEIPT.value == "RECEIPT"
    assert InventoryMovementType.ADJUSTMENT.value == "ADJUSTMENT"
