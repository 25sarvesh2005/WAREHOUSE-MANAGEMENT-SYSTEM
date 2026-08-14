"""
--------------------------------------------------------------------------------
File        : tests/unit/test_ai_release_b_flows.py
Purpose     : Test AI Release B audit, provider health, feedback, exceptions, and drafts.

Responsibilities:
    - Validate Release B request and response schemas.
    - Test provider health check responses.
    - Test feedback capture logic and validation.
    - Test exception summary categorization and fallback generation.
    - Test draft action lifecycle validation (draft creation and rejection).
    - Verify new Release B routes are registered through api_router.

Flow:
    pytest
        ->
    AI Release B schemas, controllers, and helpers
        ->
    Assertion

Used By:
    - pytest

Returns:
    None.

Raises:
    AssertionError: If AI Release B behavior regresses.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from core.apis.api import api_router
from core.apis.schemas.requests.ai_request import (
    AIDraftRecommendationRequest,
    AIDraftRejectRequest,
    AIExceptionSummaryRequest,
    AIFeedbackRequest,
)
from core.apis.schemas.responses.ai_response import (
    AIDraftActionDetailResponse,
    AIDraftActionListResponse,
    AIDraftRecommendationResponse,
    AIExceptionCategorySummary,
    AIExceptionSummaryResponse,
    AIFeedbackResponse,
    AIInteractionDetailResponse,
    AIInteractionListResponse,
    AIProviderHealthResponse,
)
from core.constants import AIDraftActionStatus, UserRole
from core.controllers.ai_controller import AIController
from core.services.ai.read_tools import OperationalExceptionEvidence


def test_feedback_request_validation() -> None:
    """Verify AIFeedbackRequest enforces required fields and limits."""
    req = AIFeedbackRequest(is_helpful=True, comment="Great explanation")
    assert req.is_helpful is True
    assert req.comment == "Great explanation"

    req_unhelpful = AIFeedbackRequest(is_helpful=False)
    assert req_unhelpful.is_helpful is False
    assert req_unhelpful.comment is None


def test_exception_summary_request_validation() -> None:
    """Verify AIExceptionSummaryRequest rejects ambiguous filter pairs."""
    with pytest.raises(ValidationError):
        AIExceptionSummaryRequest(seller_id=uuid4(), seller_code="SELLER-1")

    with pytest.raises(ValidationError):
        AIExceptionSummaryRequest(warehouse_id=uuid4(), warehouse_code="RENO")

    valid_req = AIExceptionSummaryRequest(seller_code="ALPHA", warehouse_code="RENO")
    assert valid_req.seller_code == "ALPHA"
    assert valid_req.warehouse_code == "RENO"


def test_draft_recommendation_request_validation() -> None:
    """Verify AIDraftRecommendationRequest validates recommendation type and filters."""
    with pytest.raises(ValidationError):
        AIDraftRecommendationRequest(
            recommendation_type="STOCK_REBALANCING",
            seller_id=uuid4(),
            seller_code="SELLER-A",
        )

    valid = AIDraftRecommendationRequest(
        recommendation_type="INSPECTION_PRIORITY",
        target_record_type="return",
        target_record_id=uuid4(),
        details={"priority": "URGENT"},
    )
    assert valid.recommendation_type == "INSPECTION_PRIORITY"
    assert valid.target_record_type == "return"


def test_draft_reject_request_validation() -> None:
    """Verify AIDraftRejectRequest accepts optional reason."""
    req = AIDraftRejectRequest(rejection_reason="Not required at this time.")
    assert req.rejection_reason == "Not required at this time."


def test_provider_health_response_schema() -> None:
    """Verify AIProviderHealthResponse serialization."""
    now = datetime.now(UTC)
    resp = AIProviderHealthResponse.model_validate(
        {
            "enabled": True,
            "provider_name": "google_genai",
            "model_name": "gemini-3.1-flash-lite-preview",
            "configured": True,
            "status": "HEALTHY",
            "tested_at": now,
        }
    )
    assert resp.status == "HEALTHY"
    assert resp.configured is True


def test_feedback_response_schema() -> None:
    """Verify AIFeedbackResponse serialization."""
    now = datetime.now(UTC)
    f_id = uuid4()
    i_id = uuid4()
    u_id = uuid4()
    resp = AIFeedbackResponse.model_validate(
        {
            "feedback_id": f_id,
            "interaction_id": i_id,
            "actor_user_id": u_id,
            "is_helpful": True,
            "comment": "Helpful",
            "created_at": now,
        }
    )
    assert resp.feedback_id == f_id
    assert resp.is_helpful is True


def test_exception_summary_response_schema() -> None:
    """Verify AIExceptionSummaryResponse schema mapping."""
    resp = AIExceptionSummaryResponse.model_validate(
        {
            "interaction_id": uuid4(),
            "status": "COMPLETED",
            "safety_decision": "ALLOW_READ_ONLY",
            "provider_name": "disabled",
            "model_name": "gemini-3.1-flash-lite-preview",
            "narrative_summary": "Identified 2 exceptions.",
            "total_exceptions": 2,
            "categories": [
                {
                    "category": "overdue_receipts",
                    "label": "Overdue & Pending Receipts",
                    "count": 2,
                    "severity": "HIGH",
                    "items": [],
                }
            ],
            "references": [],
        }
    )
    assert resp.total_exceptions == 2
    assert len(resp.categories) == 1
    assert resp.categories[0].severity == "HIGH"


def test_controller_requires_admin_or_manager() -> None:
    """Verify controller enforces role restrictions for admin endpoints."""
    controller = AIController()

    with pytest.raises(HTTPException) as exc_info:
        controller._require_admin_or_manager({"role": UserRole.SELLER.value})
    assert exc_info.value.status_code == 403

    with pytest.raises(HTTPException) as exc_info:
        controller._require_admin_or_manager({"role": UserRole.RECEIVER.value})
    assert exc_info.value.status_code == 403

    # Should not raise for Admin or Warehouse Manager
    controller._require_admin_or_manager({"role": UserRole.ADMINISTRATOR.value})
    controller._require_admin_or_manager({"role": UserRole.WAREHOUSE_MANAGER.value})


def test_exception_fallback_narrative_builder() -> None:
    """Verify exception fallback narrative handles empty and populated exceptions."""
    controller = AIController()

    empty_evidence = OperationalExceptionEvidence(
        overdue_receipts=[],
        short_pick_exceptions=[],
        expired_or_expiring_reservations=[],
        transfer_variances=[],
        return_inspection_queues=[],
        migration_validation_failures=[],
        total_exceptions=0,
    )
    empty_cats = controller._build_exception_categories(empty_evidence)
    narrative_empty = controller._build_exception_fallback_narrative(empty_evidence, empty_cats)
    assert "No active operational exceptions found" in narrative_empty

    populated_evidence = OperationalExceptionEvidence(
        overdue_receipts=[{"receipt_id": uuid4(), "receipt_number": "RC-1", "is_overdue": True}],
        short_pick_exceptions=[],
        expired_or_expiring_reservations=[],
        transfer_variances=[],
        return_inspection_queues=[],
        migration_validation_failures=[],
        total_exceptions=1,
    )
    populated_cats = controller._build_exception_categories(populated_evidence)
    narrative_pop = controller._build_exception_fallback_narrative(populated_evidence, populated_cats)
    assert "Identified 1 active operational exception(s)" in narrative_pop
    assert "Overdue & Pending Receipts: 1 item(s)" in narrative_pop


def test_release_b_routes_registered() -> None:
    """Verify all Release B routes are mounted in api_router."""
    routes = {route.path: route.methods for route in api_router.routes}  # type: ignore[attr-defined]

    assert "/api/v1/ai/admin/interactions" in routes
    assert "GET" in routes["/api/v1/ai/admin/interactions"]

    assert "/api/v1/ai/admin/interactions/{interaction_id}" in routes
    assert "GET" in routes["/api/v1/ai/admin/interactions/{interaction_id}"]

    assert "/api/v1/ai/admin/provider-health" in routes
    assert "GET" in routes["/api/v1/ai/admin/provider-health"]

    assert "/api/v1/ai/interactions/{interaction_id}/feedback" in routes
    assert "POST" in routes["/api/v1/ai/interactions/{interaction_id}/feedback"]

    assert "/api/v1/ai/exceptions/summary" in routes
    assert "POST" in routes["/api/v1/ai/exceptions/summary"]

    assert "/api/v1/ai/drafts/recommendation" in routes
    assert "POST" in routes["/api/v1/ai/drafts/recommendation"]

    assert "/api/v1/ai/drafts" in routes
    assert "GET" in routes["/api/v1/ai/drafts"]

    assert "/api/v1/ai/drafts/{draft_id}/reject" in routes
    assert "POST" in routes["/api/v1/ai/drafts/{draft_id}/reject"]
