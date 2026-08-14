"""
Unit Tests for Transfer Workflows.

Validates multi-warehouse transfer request schemas, validation rules, and state machine enums.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from core.apis.schemas.requests.transfer_request import (
    TransferCreateRequest,
    TransferLineRequest,
    TransferReceiveRequest,
)
from core.constants import TransferStatus


def test_transfer_create_request_validation():
    """Verify valid TransferCreateRequest parsing."""
    seller_id = uuid4()
    origin_wh_id = uuid4()
    dest_wh_id = uuid4()
    product_id = uuid4()

    req = TransferCreateRequest(
        seller_id=seller_id,
        origin_warehouse_id=origin_wh_id,
        destination_warehouse_id=dest_wh_id,
        notes="Reno to Columbus inter-warehouse transfer",
        lines=[
            TransferLineRequest(
                product_id=product_id,
                requested_quantity=Decimal("50.00"),
                notes="Fragile items",
            )
        ],
    )
    assert req.seller_id == seller_id
    assert req.origin_warehouse_id == origin_wh_id
    assert req.destination_warehouse_id == dest_wh_id
    assert len(req.lines) == 1
    assert req.lines[0].requested_quantity == Decimal("50.00")


def test_transfer_create_request_rejects_empty_lines():
    """Verify TransferCreateRequest rejects requests with zero line items."""
    with pytest.raises(ValidationError):
        TransferCreateRequest(
            seller_id=uuid4(),
            origin_warehouse_id=uuid4(),
            destination_warehouse_id=uuid4(),
            lines=[],
        )


def test_transfer_line_rejects_zero_or_negative_quantity():
    """Verify TransferLineRequest rejects non-positive requested quantities."""
    with pytest.raises(ValidationError):
        TransferLineRequest(
            product_id=uuid4(),
            requested_quantity=Decimal("0.00"),
        )

    with pytest.raises(ValidationError):
        TransferLineRequest(
            product_id=uuid4(),
            requested_quantity=Decimal("-10.00"),
        )


def test_transfer_status_enum_values():
    """Verify TransferStatus enum strings."""
    assert TransferStatus.DRAFT.value == "DRAFT"
    assert TransferStatus.APPROVED.value == "APPROVED"
    assert TransferStatus.DISPATCHED.value == "DISPATCHED"
    assert TransferStatus.RECEIVED.value == "RECEIVED"
    assert TransferStatus.DISCREPANCY_REVIEW.value == "DISCREPANCY_REVIEW"
