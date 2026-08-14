"""
Unit Tests for Return Workflows.

Validates customer / seller return request schemas, disposition enums, and validation constraints.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from core.apis.schemas.requests.return_request import (
    ReturnCreateRequest,
    ReturnInspectRequest,
    ReturnLineRequest,
)
from core.constants import ReturnDispositionState, ReturnStatus


def test_return_create_request_validation():
    """Verify ReturnCreateRequest parsing."""
    seller_id = uuid4()
    wh_id = uuid4()
    product_id = uuid4()

    req = ReturnCreateRequest(
        seller_id=seller_id,
        warehouse_id=wh_id,
        rma_number="RMA-99482",
        inbound_tracking_number="1Z9999999999",
        is_unidentified=False,
        lines=[
            ReturnLineRequest(
                product_id=product_id,
                expected_quantity=Decimal("5.00"),
                reason_code="DEFECTIVE",
            )
        ],
    )
    assert req.seller_id == seller_id
    assert req.warehouse_id == wh_id
    assert req.rma_number == "RMA-99482"
    assert len(req.lines) == 1


def test_return_create_request_rejects_empty_lines():
    """Verify ReturnCreateRequest rejects requests with zero lines."""
    with pytest.raises(ValidationError):
        ReturnCreateRequest(
            seller_id=uuid4(),
            warehouse_id=uuid4(),
            lines=[],
        )


def test_return_disposition_state_enum():
    """Verify ReturnDispositionState values."""
    assert ReturnDispositionState.AVAILABLE.value == "AVAILABLE"
    assert ReturnDispositionState.DAMAGED.value == "DAMAGED"
    assert ReturnDispositionState.QUARANTINED.value == "QUARANTINED"
    assert ReturnDispositionState.RESTOCKED.value == "RESTOCKED"
    assert ReturnDispositionState.SCRAPPED.value == "SCRAPPED"


def test_return_status_enum():
    """Verify ReturnStatus values."""
    assert ReturnStatus.EXPECTED.value == "EXPECTED"
    assert ReturnStatus.INSPECTION.value == "INSPECTION"
    assert ReturnStatus.COMPLETED.value == "COMPLETED"
    assert ReturnStatus.UNIDENTIFIED.value == "UNIDENTIFIED"
