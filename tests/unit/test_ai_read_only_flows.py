"""
--------------------------------------------------------------------------------
File        : tests/unit/test_ai_read_only_flows.py
Purpose     : Test AI Release A Slice 2 read-only request and response behavior.

Responsibilities:
    - Validate AI request schema filters.
    - Verify deterministic fallback answer helpers remain read-only.
    - Confirm AI routes are registered through the API router.

Flow:
    pytest
        ->
    AI schemas and controller helper methods
        ->
    Assertion

Used By:
    - pytest

Returns:
    None.

Raises:
    AssertionError: If read-only AI behavior regresses.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError
from fastapi import HTTPException

from core.apis.api import api_router
from core.apis.schemas.requests.ai_request import (
    AIInventoryAvailabilityRequest,
    AILedgerExplanationRequest,
    AIOperationalStatusRequest,
)
from core.apis.schemas.responses.ai_response import (
    AIInventoryAvailabilityResponse,
    AILedgerExplanationResponse,
    AIOperationalStatusResponse,
)
from core.constants import UserRole
from core.controllers.ai_controller import AIController
from core.services.ai.read_tools import (
    AvailableInventoryEvidence,
    LedgerMovementEvidence,
    OperationalStatusEvidence,
)


def test_ai_availability_request_rejects_ambiguous_seller_filter() -> None:
    """Verify availability requests cannot mix seller ID and seller code."""
    with pytest.raises(ValidationError):
        AIInventoryAvailabilityRequest(
            sku="SKU-1",
            seller_id=uuid4(),
            seller_code="SELLER-1",
        )


def test_ai_ledger_request_rejects_ambiguous_warehouse_filter() -> None:
    """Verify ledger requests cannot mix warehouse ID and warehouse code."""
    with pytest.raises(ValidationError):
        AILedgerExplanationRequest(
            sku="SKU-1",
            warehouse_id=uuid4(),
            warehouse_code="RENO",
        )


def test_ai_status_request_requires_one_lookup_key() -> None:
    """Verify status requests require exactly one record lookup key."""
    with pytest.raises(ValidationError):
        AIOperationalStatusRequest()

    with pytest.raises(ValidationError):
        AIOperationalStatusRequest(record_id=uuid4(), reference_number="ORD-1")

    request = AIOperationalStatusRequest(reference_number="ORD-1")
    assert request.reference_number == "ORD-1"


def test_ai_availability_response_accepts_string_references() -> None:
    """Verify response models parse audit-safe string UUID references."""
    product_id = uuid4()
    response = AIInventoryAvailabilityResponse.model_validate(
        {
            "interaction_id": uuid4(),
            "status": "COMPLETED",
            "safety_decision": "ALLOW_READ_ONLY",
            "provider_name": "disabled",
            "model_name": "gemini-2.5-flash",
            "answer": "SKU-1 has 3.00 units at warehouse RENO.",
            "references": [
                {
                    "record_type": "products",
                    "record_id": str(product_id),
                    "label": "Product SKU-1",
                    "metadata": {},
                }
            ],
            "rows": [
                {
                    "seller_id": uuid4(),
                    "seller_code": "SELLER-1",
                    "product_id": product_id,
                    "sku": "SKU-1",
                    "product_name": "Test product",
                    "warehouse_id": uuid4(),
                    "warehouse_code": "RENO",
                    "available_quantity": "3.00",
                }
            ],
        }
    )

    assert response.references[0].record_id == product_id
    assert response.rows[0].available_quantity == Decimal("3.00")


def test_ai_ledger_response_accepts_movement_rows() -> None:
    """Verify ledger response serializes movement evidence rows."""
    movement_id = uuid4()
    response = AILedgerExplanationResponse.model_validate(
        {
            "interaction_id": uuid4(),
            "status": "COMPLETED",
            "safety_decision": "ALLOW_READ_ONLY",
            "provider_name": "disabled",
            "model_name": "gemini-2.5-flash",
            "answer": "Found 1 recent ledger movement.",
            "references": [
                {
                    "record_type": "inventory_movements",
                    "record_id": str(movement_id),
                    "label": "RECEIPT 5.00 AVAILABLE",
                    "metadata": {},
                }
            ],
            "movements": [
                {
                    "movement_id": movement_id,
                    "seller_id": uuid4(),
                    "seller_code": "SELLER-1",
                    "product_id": uuid4(),
                    "sku": "SKU-1",
                    "product_name": "Test product",
                    "warehouse_id": uuid4(),
                    "warehouse_code": "RENO",
                    "inventory_state": "AVAILABLE",
                    "quantity_delta": "5.00",
                    "movement_type": "RECEIPT",
                    "source_type": "RECEIPT",
                    "source_id": uuid4(),
                    "reason_code": None,
                    "reason_text": None,
                    "recorded_at": datetime.now(UTC),
                }
            ],
        }
    )

    assert response.references[0].record_id == movement_id
    assert response.movements[0].quantity_delta == Decimal("5.00")


def test_ai_status_response_accepts_record_payload() -> None:
    """Verify status responses serialize record evidence dictionaries."""
    order_id = uuid4()
    response = AIOperationalStatusResponse.model_validate(
        {
            "interaction_id": uuid4(),
            "status": "COMPLETED",
            "safety_decision": "ALLOW_READ_ONLY",
            "provider_name": "disabled",
            "model_name": "gemini-2.5-flash",
            "answer": "Order ORD-1 is RESERVED.",
            "references": [
                {
                    "record_type": "orders",
                    "record_id": str(order_id),
                    "label": "Order ORD-1",
                    "metadata": {"status": "RESERVED"},
                }
            ],
            "record": {
                "record_type": "order",
                "record_id": str(order_id),
                "reference_number": "ORD-1",
                "status": "RESERVED",
                "seller_id": str(uuid4()),
                "seller_code": "SELLER-1",
                "warehouse_ids": [str(uuid4())],
                "warehouse_codes": ["RENO"],
                "summary": {},
                "details": [],
            },
        }
    )

    assert response.references[0].record_id == order_id
    assert response.record is not None
    assert response.record["status"] == "RESERVED"


def test_ai_controller_builds_deterministic_availability_answer() -> None:
    """Verify deterministic availability answer uses application evidence only."""
    controller = AIController()
    row = AvailableInventoryEvidence(
        seller_id=uuid4(),
        seller_code="SELLER-1",
        product_id=uuid4(),
        sku="SKU-1",
        product_name="Test product",
        warehouse_id=uuid4(),
        warehouse_code="RENO",
        available_quantity=Decimal("4.00"),
    )

    answer = controller._availability_fallback_answer("SKU-1", [row])

    assert "SKU-1 has 4.00 units" in answer
    assert "RENO" in answer


def test_ai_controller_builds_deterministic_ledger_answer() -> None:
    """Verify deterministic ledger answer summarizes returned movement evidence."""
    controller = AIController()
    movement = LedgerMovementEvidence(
        movement_id=uuid4(),
        seller_id=uuid4(),
        seller_code="SELLER-1",
        product_id=uuid4(),
        sku="SKU-1",
        product_name="Test product",
        warehouse_id=uuid4(),
        warehouse_code="RENO",
        inventory_state="AVAILABLE",
        quantity_delta=Decimal("5.00"),
        movement_type="RECEIPT",
        source_type="RECEIPT",
        source_id=uuid4(),
        reason_code=None,
        reason_text=None,
        recorded_at=datetime.now(UTC),
    )

    answer = controller._ledger_fallback_answer("SKU-1", [movement])

    assert "Found 1 recent ledger movement" in answer
    assert "net delta across returned rows is 5.00" in answer


def test_ai_controller_builds_deterministic_status_answer() -> None:
    """Verify deterministic status answer summarizes application record evidence."""
    controller = AIController()
    evidence = _status_evidence(
        seller_id=uuid4(),
        warehouse_id=uuid4(),
        warehouse_code="RENO",
    )

    answer = controller._status_fallback_answer(evidence)

    assert "Order ORD-1 is RESERVED" in answer
    assert "seller SELLER-1" in answer
    assert "RENO" in answer


def test_ai_status_scope_allows_matching_warehouse_role() -> None:
    """Verify warehouse-scoped roles can see records for assigned warehouses."""
    controller = AIController()
    warehouse_id = uuid4()
    evidence = _status_evidence(
        seller_id=uuid4(),
        warehouse_id=warehouse_id,
        warehouse_code="RENO",
    )
    scope = {
        "role": UserRole.WAREHOUSE_MANAGER.value,
        "seller_ids": [],
        "warehouse_ids": [str(warehouse_id)],
    }

    controller._assert_status_evidence_access(scope, evidence)


def test_ai_status_scope_denies_cross_tenant_seller() -> None:
    """Verify seller-scoped users cannot see another seller's status record."""
    controller = AIController()
    seller_id = uuid4()
    evidence = _status_evidence(
        seller_id=seller_id,
        warehouse_id=uuid4(),
        warehouse_code="RENO",
    )
    scope = {
        "role": UserRole.SELLER.value,
        "seller_ids": [str(uuid4())],
        "warehouse_ids": [],
    }

    with pytest.raises(HTTPException):
        controller._assert_status_evidence_access(scope, evidence)


def test_ai_routes_are_registered() -> None:
    """Verify read-only AI routes are included in the aggregate API router."""
    route_paths = {route.path for route in api_router.routes}

    assert "/api/v1/ai/inventory/availability" in route_paths
    assert "/api/v1/ai/inventory/ledger-explanation" in route_paths
    assert "/api/v1/ai/status/order" in route_paths
    assert "/api/v1/ai/status/receipt" in route_paths
    assert "/api/v1/ai/status/transfer" in route_paths
    assert "/api/v1/ai/status/shipment" in route_paths
    assert "/api/v1/ai/status/return" in route_paths


def _status_evidence(
    *,
    seller_id: object,
    warehouse_id: object,
    warehouse_code: str,
) -> OperationalStatusEvidence:
    """Build operational status evidence for controller unit tests."""
    return OperationalStatusEvidence(
        record_type="order",
        record_id=uuid4(),
        reference_number="ORD-1",
        status="RESERVED",
        seller_id=seller_id,
        seller_code="SELLER-1",
        warehouse_ids=[warehouse_id],
        warehouse_codes=[warehouse_code],
        summary={},
        details=[],
    )
