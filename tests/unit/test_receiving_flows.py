"""
--------------------------------------------------------------------------------
File        : tests/unit/test_receiving_flows.py
Purpose     : Test receiving schemas and request validation.

Responsibilities:
    - Validate receipt create, line item, and override request schemas.

Flow:
    pytest -> Receiving schemas -> Assertion

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

import pytest
from pydantic import ValidationError

from core.apis.schemas.requests.receiving_request import (
    DuplicateOverrideRequest,
    ReceiptCreateRequest,
    ReceiptLineSaveRequest,
)
from core.constants import ReceiptSourceType, ReceiptStatus


def test_receipt_create_request_validation() -> None:
    """Verify ReceiptCreateRequest validates source types and references."""
    seller_id = uuid4()
    wh_id = uuid4()
    req = ReceiptCreateRequest(
        seller_id=seller_id,
        warehouse_id=wh_id,
        source_type=ReceiptSourceType.CARRIER_TRACKING,
        source_reference="1Z9999999999999999",
    )
    assert req.seller_id == seller_id
    assert req.source_type == ReceiptSourceType.CARRIER_TRACKING
    assert req.source_reference == "1Z9999999999999999"


def test_receipt_line_save_request_validation() -> None:
    """Verify ReceiptLineSaveRequest non-negative quantities."""
    product_id = uuid4()
    req = ReceiptLineSaveRequest(
        product_id=product_id,
        expected_quantity=Decimal("100.00"),
        sellable_quantity=Decimal("95.00"),
        damaged_quantity=Decimal("5.00"),
    )
    assert req.product_id == product_id
    assert req.sellable_quantity == Decimal("95.00")
    assert req.damaged_quantity == Decimal("5.00")


def test_receipt_line_save_request_rejects_negative_quantity() -> None:
    """Verify ReceiptLineSaveRequest rejects negative quantities."""
    with pytest.raises(ValidationError):
        ReceiptLineSaveRequest(
            product_id=uuid4(),
            sellable_quantity=Decimal("-1.00"),
        )


def test_duplicate_override_request_validation() -> None:
    """Verify DuplicateOverrideRequest min length constraint on reason."""
    orig_id = uuid4()
    req = DuplicateOverrideRequest(
        original_receipt_id=orig_id,
        override_reason="Split shipment received on second carrier truck",
    )
    assert req.original_receipt_id == orig_id
    assert "Split shipment" in req.override_reason
