"""
--------------------------------------------------------------------------------
File        : core/apis/routes/ai_routes.py
Purpose     : Expose read-only AI operations assistance endpoints.

Responsibilities:
    - Validate AI request payloads and authenticate requester scope.
    - Delegate read-only AI workflows to AIController.
    - Keep routes free of direct database queries and business policy.

Flow:
    HTTP request
        ->
    Route dependency validation
        ->
    AIController
        ->
    Response schema

Used By:
    - core/apis/api.py

Returns:
    APIRouter - Registered read-only AI API routes.

Raises:
    HTTPException: For route-level and controller errors.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from common.logger import get_logger
from common.rate_limit import ai_rate_limiter
from common.warehouse_scope import get_warehouse_scope
from core.apis.schemas.requests.ai_request import (
    AIDraftRecommendationRequest,
    AIDraftRejectRequest,
    AIExceptionSummaryRequest,
    AIFeedbackRequest,
    AIInventoryAvailabilityRequest,
    AILedgerExplanationRequest,
    AIOperationalStatusRequest,
)
from core.apis.schemas.responses.ai_response import (
    AIDraftActionDetailResponse,
    AIDraftActionListResponse,
    AIDraftRecommendationResponse,
    AIExceptionSummaryResponse,
    AIFeedbackResponse,
    AIInteractionDetailResponse,
    AIInteractionListResponse,
    AIInventoryAvailabilityResponse,
    AILedgerExplanationResponse,
    AIOperationalStatusResponse,
    AIProviderHealthResponse,
)
from core.controllers.ai_controller import ai_controller

logger = get_logger(__name__)
router = APIRouter(
    prefix="/v1/ai",
    tags=["AI"],
    dependencies=[Depends(ai_rate_limiter)],
)


@router.post(
    "/inventory/availability",
    response_model=AIInventoryAvailabilityResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask read-only AI for available inventory",
)
async def answer_available_inventory(
    request: AIInventoryAvailabilityRequest,
    scope: dict = Depends(get_warehouse_scope),
) -> AIInventoryAvailabilityResponse:
    """
    Answer available inventory questions through a scoped read-only AI tool.

    Args:
        request: Available inventory AI request.
        scope: Authenticated warehouse scope dependency.

    Returns:
        AIInventoryAvailabilityResponse: Answer, evidence, references, and audit ID.

    Raises:
        HTTPException: For access denial or safe server errors.
    """
    try:
        logger.info("Calling POST /v1/ai/inventory/availability endpoint")
        response = await ai_controller.answer_available_inventory(scope, request)
        return AIInventoryAvailabilityResponse.model_validate(response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error(
            "Error in POST /v1/ai/inventory/availability endpoint: %s",
            error,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.post(
    "/inventory/ledger-explanation",
    response_model=AILedgerExplanationResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask read-only AI to explain inventory ledger changes",
)
async def explain_ledger_changes(
    request: AILedgerExplanationRequest,
    scope: dict = Depends(get_warehouse_scope),
) -> AILedgerExplanationResponse:
    """
    Explain inventory ledger changes through a scoped read-only AI tool.

    Args:
        request: Ledger explanation AI request.
        scope: Authenticated warehouse scope dependency.

    Returns:
        AILedgerExplanationResponse: Explanation, movements, references, and audit ID.

    Raises:
        HTTPException: For access denial or safe server errors.
    """
    try:
        logger.info("Calling POST /v1/ai/inventory/ledger-explanation endpoint")
        response = await ai_controller.explain_ledger_changes(scope, request)
        return AILedgerExplanationResponse.model_validate(response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error(
            "Error in POST /v1/ai/inventory/ledger-explanation endpoint: %s",
            error,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.post(
    "/status/order",
    response_model=AIOperationalStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask read-only AI for order status",
)
async def answer_order_status(
    request: AIOperationalStatusRequest,
    scope: dict = Depends(get_warehouse_scope),
) -> AIOperationalStatusResponse:
    """
    Answer an order status question through a scoped read-only AI tool.

    Args:
        request: Operational status request.
        scope: Authenticated warehouse scope dependency.

    Returns:
        AIOperationalStatusResponse: Answer, evidence, references, and audit ID.

    Raises:
        HTTPException: For access denial, not-found, or safe server errors.
    """
    return await _answer_operational_status("order", request, scope)


@router.post(
    "/status/receipt",
    response_model=AIOperationalStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask read-only AI for receipt status",
)
async def answer_receipt_status(
    request: AIOperationalStatusRequest,
    scope: dict = Depends(get_warehouse_scope),
) -> AIOperationalStatusResponse:
    """
    Answer a receipt status question through a scoped read-only AI tool.

    Args:
        request: Operational status request.
        scope: Authenticated warehouse scope dependency.

    Returns:
        AIOperationalStatusResponse: Answer, evidence, references, and audit ID.

    Raises:
        HTTPException: For access denial, not-found, or safe server errors.
    """
    return await _answer_operational_status("receipt", request, scope)


@router.post(
    "/status/transfer",
    response_model=AIOperationalStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask read-only AI for transfer status",
)
async def answer_transfer_status(
    request: AIOperationalStatusRequest,
    scope: dict = Depends(get_warehouse_scope),
) -> AIOperationalStatusResponse:
    """
    Answer a transfer status question through a scoped read-only AI tool.

    Args:
        request: Operational status request.
        scope: Authenticated warehouse scope dependency.

    Returns:
        AIOperationalStatusResponse: Answer, evidence, references, and audit ID.

    Raises:
        HTTPException: For access denial, not-found, or safe server errors.
    """
    return await _answer_operational_status("transfer", request, scope)


@router.post(
    "/status/shipment",
    response_model=AIOperationalStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask read-only AI for shipment status",
)
async def answer_shipment_status(
    request: AIOperationalStatusRequest,
    scope: dict = Depends(get_warehouse_scope),
) -> AIOperationalStatusResponse:
    """
    Answer a shipment status question through a scoped read-only AI tool.

    Args:
        request: Operational status request.
        scope: Authenticated warehouse scope dependency.

    Returns:
        AIOperationalStatusResponse: Answer, evidence, references, and audit ID.

    Raises:
        HTTPException: For access denial, not-found, or safe server errors.
    """
    return await _answer_operational_status("shipment", request, scope)


@router.post(
    "/status/return",
    response_model=AIOperationalStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask read-only AI for return status",
)
async def answer_return_status(
    request: AIOperationalStatusRequest,
    scope: dict = Depends(get_warehouse_scope),
) -> AIOperationalStatusResponse:
    """
    Answer a return status question through a scoped read-only AI tool.

    Args:
        request: Operational status request.
        scope: Authenticated warehouse scope dependency.

    Returns:
        AIOperationalStatusResponse: Answer, evidence, references, and audit ID.

    Raises:
        HTTPException: For access denial, not-found, or safe server errors.
    """
    return await _answer_operational_status("return", request, scope)


async def _answer_operational_status(
    record_type: str,
    request: AIOperationalStatusRequest,
    scope: dict,
) -> AIOperationalStatusResponse:
    """
    Delegate a status route to the AI controller with safe error normalization.

    Args:
        record_type: Operational record type handled by the route.
        request: Operational status request.
        scope: Authenticated warehouse scope dependency.

    Returns:
        AIOperationalStatusResponse: Answer, evidence, references, and audit ID.

    Raises:
        HTTPException: For controller-raised or safe server errors.
    """
    try:
        logger.info("Calling POST /v1/ai/status/%s endpoint", record_type)
        response = await ai_controller.answer_operational_status(
            scope,
            request,
            record_type=record_type,
        )
        return AIOperationalStatusResponse.model_validate(response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error(
            "Error in POST /v1/ai/status/%s endpoint: %s",
            record_type,
            error,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.get(
    "/admin/interactions",
    response_model=AIInteractionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List audited AI interactions for administrators and managers",
)
async def list_ai_interactions(
    status_filter: str | None = Query(default=None, alias="status"),
    provider_name: str | None = Query(default=None),
    request_category: str | None = Query(default=None),
    actor_user_id: UUID | None = Query(default=None),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    scope: dict = Depends(get_warehouse_scope),
) -> AIInteractionListResponse:
    """
    List audited AI interactions with filtering and pagination.

    Args:
        status_filter: Optional status filter (e.g., COMPLETED, REFUSED, FAILED).
        provider_name: Optional provider name filter.
        request_category: Optional request category filter.
        actor_user_id: Optional user filter.
        start_date: Optional inclusive start date.
        end_date: Optional inclusive end date.
        limit: Number of items per page.
        offset: Number of items to skip.
        scope: Authenticated requester scope.

    Returns:
        AIInteractionListResponse: Paginated interaction list and count.

    Raises:
        HTTPException: For permission or safe server errors.
    """
    try:
        logger.info("Calling GET /v1/ai/admin/interactions endpoint")
        response = await ai_controller.list_interactions(
            scope,
            status=status_filter,
            provider_name=provider_name,
            request_category=request_category,
            actor_user_id=actor_user_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )
        return AIInteractionListResponse.model_validate(response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in GET /v1/ai/admin/interactions: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.get(
    "/admin/interactions/{interaction_id}",
    response_model=AIInteractionDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get audited AI interaction details",
)
async def get_ai_interaction_detail(
    interaction_id: UUID,
    scope: dict = Depends(get_warehouse_scope),
) -> AIInteractionDetailResponse:
    """
    Fetch comprehensive audit detail for an interaction.

    Args:
        interaction_id: AI interaction UUID.
        scope: Authenticated requester scope.

    Returns:
        AIInteractionDetailResponse: Interaction details with tool calls and feedback.

    Raises:
        HTTPException: For not-found, permission, or server errors.
    """
    try:
        logger.info("Calling GET /v1/ai/admin/interactions/%s endpoint", interaction_id)
        response = await ai_controller.get_interaction_detail(scope, interaction_id)
        return AIInteractionDetailResponse.model_validate(response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error(
            "Error in GET /v1/ai/admin/interactions/%s: %s",
            interaction_id,
            error,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.get(
    "/admin/provider-health",
    response_model=AIProviderHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Get AI provider health and configuration status",
)
async def get_ai_provider_health(
    scope: dict = Depends(get_warehouse_scope),
) -> AIProviderHealthResponse:
    """
    Check AI provider runtime readiness and configuration status.

    Args:
        scope: Authenticated requester scope.

    Returns:
        AIProviderHealthResponse: Provider health summary.

    Raises:
        HTTPException: For permission or safe server errors.
    """
    try:
        logger.info("Calling GET /v1/ai/admin/provider-health endpoint")
        response = await ai_controller.get_provider_health(scope)
        return AIProviderHealthResponse.model_validate(response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error(
            "Error in GET /v1/ai/admin/provider-health: %s", error, exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.post(
    "/interactions/{interaction_id}/feedback",
    response_model=AIFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit helpful/unhelpful feedback on an AI interaction",
)
async def submit_ai_feedback(
    interaction_id: UUID,
    request: AIFeedbackRequest,
    scope: dict = Depends(get_warehouse_scope),
) -> AIFeedbackResponse:
    """
    Capture user feedback on an AI response.

    Args:
        interaction_id: AI interaction UUID receiving feedback.
        request: Validated feedback payload.
        scope: Authenticated requester scope.

    Returns:
        AIFeedbackResponse: Created feedback record.

    Raises:
        HTTPException: For not-found or server errors.
    """
    try:
        logger.info(
            "Calling POST /v1/ai/interactions/%s/feedback endpoint", interaction_id
        )
        response = await ai_controller.submit_feedback(scope, interaction_id, request)
        return AIFeedbackResponse.model_validate(response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error(
            "Error in POST /v1/ai/interactions/%s/feedback: %s",
            interaction_id,
            error,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.post(
    "/exceptions/summary",
    response_model=AIExceptionSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask read-only AI for operational exceptions summary",
)
async def summarize_operational_exceptions(
    request: AIExceptionSummaryRequest,
    scope: dict = Depends(get_warehouse_scope),
) -> AIExceptionSummaryResponse:
    """
    Aggregate operational exceptions across warehouse subsystems into a structured summary.

    Args:
        request: Validated exception summary request.
        scope: Authenticated requester scope.

    Returns:
        AIExceptionSummaryResponse: Categorized exceptions and narrative summary.

    Raises:
        HTTPException: For permission, validation, or server errors.
    """
    try:
        logger.info("Calling POST /v1/ai/exceptions/summary endpoint")
        response = await ai_controller.summarize_exceptions(scope, request)
        return AIExceptionSummaryResponse.model_validate(response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error(
            "Error in POST /v1/ai/exceptions/summary: %s", error, exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.post(
    "/drafts/recommendation",
    response_model=AIDraftRecommendationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a human-reviewable draft operational recommendation",
)
async def create_draft_recommendation(
    request: AIDraftRecommendationRequest,
    scope: dict = Depends(get_warehouse_scope),
) -> AIDraftRecommendationResponse:
    """
    Create a draft recommendation record requiring subsequent human approval.

    Args:
        request: Validated draft recommendation request.
        scope: Authenticated requester scope.

    Returns:
        AIDraftRecommendationResponse: Created draft action with recommendation summary.

    Raises:
        HTTPException: For permission, validation, or server errors.
    """
    try:
        logger.info("Calling POST /v1/ai/drafts/recommendation endpoint")
        response = await ai_controller.create_draft_recommendation(scope, request)
        return AIDraftRecommendationResponse.model_validate(response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error(
            "Error in POST /v1/ai/drafts/recommendation: %s",
            error,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.get(
    "/drafts",
    response_model=AIDraftActionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List AI draft recommendations for manager/admin review",
)
async def list_draft_actions(
    status_filter: str | None = Query(default=None, alias="status"),
    action_type: str | None = Query(default=None),
    interaction_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    scope: dict = Depends(get_warehouse_scope),
) -> AIDraftActionListResponse:
    """
    List AI draft actions with filtering and pagination.

    Args:
        status_filter: Optional status filter (e.g. DRAFTED, REJECTED, APPROVED).
        action_type: Optional recommendation type filter.
        interaction_id: Optional parent interaction UUID filter.
        limit: Maximum number of rows.
        offset: Rows to skip.
        scope: Authenticated requester scope.

    Returns:
        AIDraftActionListResponse: Paginated draft actions list.

    Raises:
        HTTPException: For permission or safe server errors.
    """
    try:
        logger.info("Calling GET /v1/ai/drafts endpoint")
        response = await ai_controller.list_draft_actions(
            scope,
            status=status_filter,
            action_type=action_type,
            interaction_id=interaction_id,
            limit=limit,
            offset=offset,
        )
        return AIDraftActionListResponse.model_validate(response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error("Error in GET /v1/ai/drafts: %s", error, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error") from error


@router.post(
    "/drafts/{draft_id}/reject",
    response_model=AIDraftActionDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject an AI draft recommendation",
)
async def reject_draft_action(
    draft_id: UUID,
    request: AIDraftRejectRequest,
    scope: dict = Depends(get_warehouse_scope),
) -> AIDraftActionDetailResponse:
    """
    Reject an AI draft recommendation without executing any mutations.

    Args:
        draft_id: Draft action UUID.
        request: Validated reject request with reason.
        scope: Authenticated requester scope.

    Returns:
        AIDraftActionDetailResponse: Updated draft action record.

    Raises:
        HTTPException: For not-found, conflict, or permission errors.
    """
    try:
        logger.info("Calling POST /v1/ai/drafts/%s/reject endpoint", draft_id)
        response = await ai_controller.reject_draft_action(scope, draft_id, request)
        return AIDraftActionDetailResponse.model_validate(response)
    except HTTPException:
        raise
    except Exception as error:
        logger.error(
            "Error in POST /v1/ai/drafts/%s/reject: %s",
            draft_id,
            error,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal Server Error") from error
