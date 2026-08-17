"""
AI Operations Controller.

Orchestrates read-only AI operations assistance, intent safety guardrails, and audit tracking.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Sequence
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from common.logger import get_logger
from common.warehouse_scope import assert_seller_access, assert_warehouse_access
from core.apis.schemas.requests.ai_request import (
    AIDraftRecommendationRequest,
    AIDraftRejectRequest,
    AIExceptionSummaryRequest,
    AIFeedbackRequest,
    AIInventoryAvailabilityRequest,
    AILedgerExplanationRequest,
    AIOperationalStatusRequest,
)
from core.config.settings import Settings, get_settings
from core.constants import (
    AIDraftActionStatus,
    AIInteractionStatus,
    AIRequestCategory,
    AISafetyDecision,
    AIToolCallStatus,
    AuditActionType,
    UserRole,
)
from core.cruds import ai_crud, audit_crud, identity_crud
from core.database.database import transaction_session
from core.models.ai_model import AIDraftAction, AIFeedback, AIInteraction, AIToolCall
from core.services.ai.provider import (
    AIProviderExecutionError,
    AIProviderUnavailableError,
    build_ai_provider,
)
from core.services.ai.read_tools import (
    AvailableInventoryEvidence,
    LedgerMovementEvidence,
    OperationalExceptionEvidence,
    OperationalStatusEvidence,
    lookup_available_inventory,
    lookup_operational_exceptions,
    lookup_order_status,
    lookup_receipt_status,
    lookup_recent_ledger_movements,
    lookup_return_status,
    lookup_shipment_status,
    lookup_transfer_status,
)
from core.services.ai.safety import AISafetyGuard, hash_sensitive_text, make_safe_excerpt
from core.services.ai.types import AIProviderRequest

logger = get_logger(__name__)


class AIController:
    """Controller for read-only AI operations assistance."""

    def __init__(self) -> None:
        """
        Initialize read-only AI controller dependencies.

        Args:
            None.

        Returns:
            None.

        Raises:
            None.
        """
        self._safety_guard = AISafetyGuard()

    async def answer_available_inventory(
        self,
        scope: dict[str, Any],
        request: AIInventoryAvailabilityRequest,
    ) -> dict[str, object]:
        """
        Answer a read-only available inventory question.

        Args:
            scope: Authenticated requester scope.
            request: Validated available inventory request.

        Returns:
            dict[str, object]: Response-ready answer and evidence rows.

        Raises:
            HTTPException: If scope or validation checks fail.
        """
        settings = get_settings()
        raw_query = (request.sku or "").strip()
        if request.prompt:
            prompt = request.prompt
        elif raw_query.upper().startswith("SKU-") or raw_query.upper().startswith("PROD-"):
            prompt = f"Answer available quantity for SKU {raw_query} by warehouse."
        else:
            prompt = raw_query
        safety = self._safety_guard.evaluate_prompt(prompt)
        if not safety.allowed:
            return await self._record_refusal(
                scope,
                settings=settings,
                category=AIRequestCategory.INVENTORY_LOOKUP.value,
                prompt=prompt,
                safety_decision=safety.decision,
                refusal_reason=safety.reason,
            )

        self._safety_guard.ensure_read_only_tool("inventory_lookup")
        async with transaction_session() as session:
            seller_id = await self._resolve_seller_id(
                session,
                scope,
                seller_id=request.seller_id,
                seller_code=request.seller_code,
            )
            warehouse_id = await self._resolve_warehouse_id(
                session,
                scope,
                warehouse_id=request.warehouse_id,
                warehouse_code=request.warehouse_code,
            )
            interaction = await self._create_interaction(
                session,
                scope,
                settings=settings,
                category=AIRequestCategory.INVENTORY_LOOKUP.value,
                prompt=prompt,
            )
            tool_call = await ai_crud.create_ai_tool_call(
                session,
                ai_interaction_id=interaction.id,
                tool_name="inventory_lookup",
                status=AIToolCallStatus.PENDING.value,
                permission_scope=self._permission_scope_metadata(
                    scope,
                    seller_id=seller_id,
                    warehouse_id=warehouse_id,
                ),
                input_hash=hash_sensitive_text(self._tool_input_json(request)),
                input_excerpt=self._safe_excerpt(settings, self._tool_input_json(request)),
            )
            rows = await lookup_available_inventory(
                session,
                sku=request.sku,
                seller_id=seller_id,
                seller_ids=self._allowed_seller_ids(scope),
                warehouse_id=warehouse_id,
                warehouse_ids=self._allowed_warehouse_ids(scope),
            )
            references = self._availability_references(rows)
            await ai_crud.complete_ai_tool_call(
                session,
                tool_call,
                status=AIToolCallStatus.COMPLETED.value,
                output_reference_count=len(references),
            )
            await audit_crud.create_audit_event(
                session,
                actor_user_id=UUID(str(scope["user_id"])),
                action_type=AuditActionType.AI_TOOL_CALL_RECORDED.value,
                source_record_type="ai_tool_calls",
                source_record_id=tool_call.id,
                metadata_json={"tool_name": "inventory_lookup"},
            )
            interaction_id = interaction.id

        fallback_answer = self._availability_fallback_answer(request.sku, rows)
        answer, provider_name, model_name, provider_metadata = await self._provider_answer(
            settings,
            prompt=prompt,
            fallback_answer=fallback_answer,
            evidence_payload={"rows": [self._availability_row(row) for row in rows]},
        )
        await self._complete_interaction(
            interaction_id,
            status_value=AIInteractionStatus.COMPLETED.value,
            safety_decision=AISafetyDecision.ALLOW_READ_ONLY.value,
            answer=answer,
            references=references,
            metadata_json=provider_metadata,
        )
        return {
            "interaction_id": interaction_id,
            "status": AIInteractionStatus.COMPLETED.value,
            "safety_decision": AISafetyDecision.ALLOW_READ_ONLY.value,
            "provider_name": provider_name,
            "model_name": model_name,
            "answer": answer,
            "references": references,
            "rows": [self._availability_row(row) for row in rows],
        }

    async def explain_ledger_changes(
        self,
        scope: dict[str, Any],
        request: AILedgerExplanationRequest,
    ) -> dict[str, object]:
        """
        Explain recent read-only movement ledger changes for a SKU.

        Args:
            scope: Authenticated requester scope.
            request: Validated ledger explanation request.

        Returns:
            dict[str, object]: Response-ready explanation and movement evidence.

        Raises:
            HTTPException: If scope or validation checks fail.
        """
        settings = get_settings()
        prompt = request.prompt or (
            f"Explain recent inventory ledger changes for SKU {request.sku}."
        )
        safety = self._safety_guard.evaluate_prompt(prompt)
        if not safety.allowed:
            return await self._record_refusal(
                scope,
                settings=settings,
                category=AIRequestCategory.LEDGER_EXPLANATION.value,
                prompt=prompt,
                safety_decision=safety.decision,
                refusal_reason=safety.reason,
            )

        self._safety_guard.ensure_read_only_tool("ledger_explanation")
        async with transaction_session() as session:
            seller_id = await self._resolve_seller_id(
                session,
                scope,
                seller_id=request.seller_id,
                seller_code=request.seller_code,
            )
            warehouse_id = await self._resolve_warehouse_id(
                session,
                scope,
                warehouse_id=request.warehouse_id,
                warehouse_code=request.warehouse_code,
            )
            interaction = await self._create_interaction(
                session,
                scope,
                settings=settings,
                category=AIRequestCategory.LEDGER_EXPLANATION.value,
                prompt=prompt,
            )
            tool_call = await ai_crud.create_ai_tool_call(
                session,
                ai_interaction_id=interaction.id,
                tool_name="ledger_explanation",
                status=AIToolCallStatus.PENDING.value,
                permission_scope=self._permission_scope_metadata(
                    scope,
                    seller_id=seller_id,
                    warehouse_id=warehouse_id,
                ),
                input_hash=hash_sensitive_text(self._tool_input_json(request)),
                input_excerpt=self._safe_excerpt(settings, self._tool_input_json(request)),
            )
            movements = await lookup_recent_ledger_movements(
                session,
                sku=request.sku,
                seller_id=seller_id,
                seller_ids=self._allowed_seller_ids(scope),
                warehouse_id=warehouse_id,
                warehouse_ids=self._allowed_warehouse_ids(scope),
                limit=request.limit,
            )
            references = self._ledger_references(movements)
            await ai_crud.complete_ai_tool_call(
                session,
                tool_call,
                status=AIToolCallStatus.COMPLETED.value,
                output_reference_count=len(references),
            )
            await audit_crud.create_audit_event(
                session,
                actor_user_id=UUID(str(scope["user_id"])),
                action_type=AuditActionType.AI_TOOL_CALL_RECORDED.value,
                source_record_type="ai_tool_calls",
                source_record_id=tool_call.id,
                metadata_json={"tool_name": "ledger_explanation"},
            )
            interaction_id = interaction.id

        fallback_answer = self._ledger_fallback_answer(request.sku, movements)
        answer, provider_name, model_name, provider_metadata = await self._provider_answer(
            settings,
            prompt=prompt,
            fallback_answer=fallback_answer,
            evidence_payload={
                "movements": [self._ledger_movement_row(row) for row in movements]
            },
        )
        await self._complete_interaction(
            interaction_id,
            status_value=AIInteractionStatus.COMPLETED.value,
            safety_decision=AISafetyDecision.ALLOW_READ_ONLY.value,
            answer=answer,
            references=references,
            metadata_json=provider_metadata,
        )
        return {
            "interaction_id": interaction_id,
            "status": AIInteractionStatus.COMPLETED.value,
            "safety_decision": AISafetyDecision.ALLOW_READ_ONLY.value,
            "provider_name": provider_name,
            "model_name": model_name,
            "answer": answer,
            "references": references,
            "movements": [self._ledger_movement_row(row) for row in movements],
        }

    async def answer_operational_status(
        self,
        scope: dict[str, Any],
        request: AIOperationalStatusRequest,
        *,
        record_type: str,
    ) -> dict[str, object]:
        """
        Answer a read-only operational record status question.

        Args:
            scope: Authenticated requester scope.
            request: Validated status request.
            record_type: Operational record type requested by the route.

        Returns:
            dict[str, object]: Response-ready status answer and evidence record.

        Raises:
            HTTPException: If scope, record type, or lookup checks fail.
        """
        settings = get_settings()
        tool_name, category = self._status_tool_config(record_type)
        prompt = request.prompt or self._status_prompt(record_type, request)
        safety = self._safety_guard.evaluate_prompt(prompt)
        if not safety.allowed:
            return await self._record_refusal(
                scope,
                settings=settings,
                category=category,
                prompt=prompt,
                safety_decision=safety.decision,
                refusal_reason=safety.reason,
            )

        self._safety_guard.ensure_read_only_tool(tool_name)
        async with transaction_session() as session:
            seller_id = await self._resolve_seller_id(
                session,
                scope,
                seller_id=request.seller_id,
                seller_code=request.seller_code,
            )
            warehouse_id = await self._resolve_warehouse_id(
                session,
                scope,
                warehouse_id=request.warehouse_id,
                warehouse_code=request.warehouse_code,
            )
            interaction = await self._create_interaction(
                session,
                scope,
                settings=settings,
                category=category,
                prompt=prompt,
            )
            tool_call = await ai_crud.create_ai_tool_call(
                session,
                ai_interaction_id=interaction.id,
                tool_name=tool_name,
                status=AIToolCallStatus.PENDING.value,
                permission_scope=self._permission_scope_metadata(
                    scope,
                    seller_id=seller_id,
                    warehouse_id=warehouse_id,
                ),
                input_hash=hash_sensitive_text(self._tool_input_json(request)),
                input_excerpt=self._safe_excerpt(settings, self._tool_input_json(request)),
            )
            evidence = await self._lookup_operational_status(
                session,
                record_type=record_type,
                request=request,
                seller_id=seller_id,
                warehouse_id=warehouse_id,
            )
            if evidence is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"{record_type.title()} not found",
                )
            self._assert_status_evidence_access(scope, evidence)
            references = self._status_references(evidence)
            await ai_crud.complete_ai_tool_call(
                session,
                tool_call,
                status=AIToolCallStatus.COMPLETED.value,
                output_reference_count=len(references),
            )
            await audit_crud.create_audit_event(
                session,
                actor_user_id=UUID(str(scope["user_id"])),
                action_type=AuditActionType.AI_TOOL_CALL_RECORDED.value,
                source_record_type="ai_tool_calls",
                source_record_id=tool_call.id,
                metadata_json={"tool_name": tool_name, "record_type": record_type},
            )
            interaction_id = interaction.id

        record_payload = self._status_record(evidence)
        fallback_answer = self._status_fallback_answer(evidence)
        answer, provider_name, model_name, provider_metadata = await self._provider_answer(
            settings,
            prompt=prompt,
            fallback_answer=fallback_answer,
            evidence_payload={"record": record_payload},
        )
        await self._complete_interaction(
            interaction_id,
            status_value=AIInteractionStatus.COMPLETED.value,
            safety_decision=AISafetyDecision.ALLOW_READ_ONLY.value,
            answer=answer,
            references=references,
            metadata_json=provider_metadata,
        )
        return {
            "interaction_id": interaction_id,
            "status": AIInteractionStatus.COMPLETED.value,
            "safety_decision": AISafetyDecision.ALLOW_READ_ONLY.value,
            "provider_name": provider_name,
            "model_name": model_name,
            "answer": answer,
            "references": references,
            "record": record_payload,
        }

    async def list_interactions(
        self,
        scope: dict[str, Any],
        *,
        status: str | None = None,
        provider_name: str | None = None,
        request_category: str | None = None,
        actor_user_id: UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, object]:
        """
        List audited AI interactions for administrators and managers.

        Args:
            scope: Authenticated requester scope.
            status: Optional status filter.
            provider_name: Optional provider name filter.
            request_category: Optional request category filter.
            actor_user_id: Optional actor user filter.
            start_date: Optional inclusive start timestamp.
            end_date: Optional inclusive end timestamp.
            limit: Maximum number of records to return.
            offset: Number of records to skip.

        Returns:
            dict[str, object]: Paginated interaction list and total count.

        Raises:
            HTTPException: If the user lacks administrator or manager role.
        """
        self._require_admin_or_manager(scope)
        async with transaction_session() as session:
            items, total_count = await ai_crud.list_ai_interactions(
                session,
                actor_user_id=actor_user_id,
                status=status,
                provider_name=provider_name,
                request_category=request_category,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
                offset=offset,
            )
            interaction_ids = [item.id for item in items]
            tool_counts, draft_counts, feedback_stats = (
                await ai_crud.get_interaction_tool_and_draft_counts(
                    session, interaction_ids
                )
            )

        summary_items = []
        for item in items:
            fb = feedback_stats.get(item.id, {"total": 0, "helpful": 0, "unhelpful": 0})
            summary_items.append(
                {
                    "id": item.id,
                    "actor_user_id": item.actor_user_id,
                    "correlation_id": item.correlation_id,
                    "request_category": item.request_category,
                    "status": item.status,
                    "provider_name": item.provider_name,
                    "model_name": item.model_name,
                    "prompt_excerpt": item.prompt_excerpt,
                    "response_excerpt": item.response_excerpt,
                    "safety_decision": item.safety_decision,
                    "refusal_reason": item.refusal_reason,
                    "tool_call_count": tool_counts.get(item.id, 0),
                    "draft_action_count": draft_counts.get(item.id, 0),
                    "feedback_count": fb["total"],
                    "helpful_count": fb["helpful"],
                    "unhelpful_count": fb["unhelpful"],
                    "created_at": item.created_at,
                    "completed_at": item.completed_at,
                }
            )
        return {
            "items": summary_items,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
        }

    async def get_interaction_detail(
        self,
        scope: dict[str, Any],
        interaction_id: UUID,
    ) -> dict[str, object]:
        """
        Fetch full audited details of an AI interaction.

        Args:
            scope: Authenticated requester scope.
            interaction_id: AI interaction UUID.

        Returns:
            dict[str, object]: Full interaction details with tool calls, drafts, and feedbacks.

        Raises:
            HTTPException: If not found or access is denied.
        """
        async with transaction_session() as session:
            interaction, tool_calls, draft_actions, feedbacks = (
                await ai_crud.get_ai_interaction_detail(session, interaction_id)
            )
            if interaction is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="AI interaction not found",
                )
            self._assert_interaction_access(scope, interaction)

        return {
            "id": interaction.id,
            "actor_user_id": interaction.actor_user_id,
            "correlation_id": interaction.correlation_id,
            "request_category": interaction.request_category,
            "status": interaction.status,
            "provider_name": interaction.provider_name,
            "model_name": interaction.model_name,
            "prompt_hash": interaction.prompt_hash,
            "prompt_excerpt": interaction.prompt_excerpt,
            "response_excerpt": interaction.response_excerpt,
            "safety_decision": interaction.safety_decision,
            "refusal_reason": interaction.refusal_reason,
            "seller_scope": interaction.seller_scope,
            "warehouse_scope": interaction.warehouse_scope,
            "retrieved_references": interaction.retrieved_references,
            "metadata_json": interaction.metadata_json,
            "tool_calls": [
                {
                    "id": tc.id,
                    "tool_name": tc.tool_name,
                    "status": tc.status,
                    "permission_scope": tc.permission_scope,
                    "input_excerpt": tc.input_excerpt,
                    "output_reference_count": tc.output_reference_count,
                    "error_message": tc.error_message,
                    "started_at": tc.started_at,
                    "completed_at": tc.completed_at,
                }
                for tc in tool_calls
            ],
            "draft_actions": [
                {
                    "id": da.id,
                    "action_type": da.action_type,
                    "status": da.status,
                    "target_record_type": da.target_record_type,
                    "target_record_id": da.target_record_id,
                    "draft_payload_excerpt": da.draft_payload_excerpt,
                    "requires_approval": da.requires_approval,
                    "approved_by_user_id": da.approved_by_user_id,
                    "approved_at": da.approved_at,
                    "rejected_at": da.rejected_at,
                    "rejection_reason": da.rejection_reason,
                    "metadata_json": da.metadata_json,
                    "created_at": da.created_at,
                }
                for da in draft_actions
            ],
            "feedbacks": [
                {
                    "feedback_id": fb.id,
                    "interaction_id": fb.ai_interaction_id,
                    "actor_user_id": fb.actor_user_id,
                    "is_helpful": fb.is_helpful,
                    "comment": fb.comment,
                    "created_at": fb.created_at,
                }
                for fb in feedbacks
            ],
            "created_at": interaction.created_at,
            "completed_at": interaction.completed_at,
        }

    async def get_provider_health(self, scope: dict[str, Any]) -> dict[str, object]:
        """
        Inspect AI provider configuration and runtime readiness.

        Args:
            scope: Authenticated requester scope.

        Returns:
            dict[str, object]: Provider health summary.

        Raises:
            HTTPException: If caller lacks admin or manager privileges.
        """
        self._require_admin_or_manager(scope)
        settings = get_settings()
        enabled = bool(getattr(settings, "ai_enabled", False))
        provider_name = str(getattr(settings, "ai_provider", "disabled")).lower()
        model_name = str(getattr(settings, "ai_model", "gemini-3.1-flash-lite-preview"))
        api_key = str(getattr(settings, "google_genai_api_key", "")).strip() or str(
            getattr(settings, "google_api_key", "")
        ).strip()
        configured = bool(api_key) if provider_name == "google_genai" else False

        if not enabled or provider_name == "disabled":
            health_status = "DISABLED"
        elif provider_name == "google_genai" and not configured:
            health_status = "KEY_MISSING"
        else:
            health_status = "HEALTHY"

        return {
            "enabled": enabled,
            "provider_name": provider_name,
            "model_name": model_name,
            "configured": configured,
            "status": health_status,
            "tested_at": datetime.now(UTC),
        }

    async def submit_feedback(
        self,
        scope: dict[str, Any],
        interaction_id: UUID,
        request: AIFeedbackRequest,
    ) -> dict[str, object]:
        """
        Capture user feedback (helpful/not helpful and comments) for an AI interaction.

        Args:
            scope: Authenticated requester scope.
            interaction_id: AI interaction UUID receiving feedback.
            request: Validated feedback request.

        Returns:
            dict[str, object]: Created feedback record.

        Raises:
            HTTPException: If interaction is not found or persistence fails.
        """
        user_id = UUID(str(scope["user_id"]))
        async with transaction_session() as session:
            interaction = await ai_crud.get_ai_interaction_by_id(session, interaction_id)
            if interaction is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="AI interaction not found",
                )
            feedback = await ai_crud.create_ai_feedback(
                session,
                ai_interaction_id=interaction_id,
                actor_user_id=user_id,
                is_helpful=request.is_helpful,
                comment=request.comment,
                metadata_json={"role": scope.get("role")},
            )
            await audit_crud.create_audit_event(
                session,
                actor_user_id=user_id,
                action_type=AuditActionType.AI_FEEDBACK_RECORDED.value,
                source_record_type="ai_feedbacks",
                source_record_id=feedback.id,
                metadata_json={
                    "interaction_id": str(interaction_id),
                    "is_helpful": request.is_helpful,
                },
            )
            return {
                "feedback_id": feedback.id,
                "interaction_id": feedback.ai_interaction_id,
                "actor_user_id": feedback.actor_user_id,
                "is_helpful": feedback.is_helpful,
                "comment": feedback.comment,
                "created_at": feedback.created_at,
            }

    async def summarize_exceptions(
        self,
        scope: dict[str, Any],
        request: AIExceptionSummaryRequest,
    ) -> dict[str, object]:
        """
        Summarize operational exceptions across warehouse subsystems.

        Args:
            scope: Authenticated requester scope.
            request: Validated exception summary request.

        Returns:
            dict[str, object]: Structured exceptions and AI narrative summary.

        Raises:
            HTTPException: If scope or lookup checks fail.
        """
        settings = get_settings()
        prompt = (
            request.prompt
            or "Summarize active operational exceptions across warehouse subsystems."
        )
        safety = self._safety_guard.evaluate_prompt(prompt)
        if not safety.allowed:
            return await self._record_refusal(
                scope,
                settings=settings,
                category=AIRequestCategory.EXCEPTION_SUMMARY.value,
                prompt=prompt,
                safety_decision=safety.decision,
                refusal_reason=safety.reason,
            )

        self._safety_guard.ensure_read_only_tool("exception_summary")
        async with transaction_session() as session:
            seller_id = await self._resolve_seller_id(
                session,
                scope,
                seller_id=request.seller_id,
                seller_code=request.seller_code,
            )
            warehouse_id = await self._resolve_warehouse_id(
                session,
                scope,
                warehouse_id=request.warehouse_id,
                warehouse_code=request.warehouse_code,
            )
            interaction = await self._create_interaction(
                session,
                scope,
                settings=settings,
                category=AIRequestCategory.EXCEPTION_SUMMARY.value,
                prompt=prompt,
            )
            tool_call = await ai_crud.create_ai_tool_call(
                session,
                ai_interaction_id=interaction.id,
                tool_name="exception_summary",
                status=AIToolCallStatus.PENDING.value,
                permission_scope=self._permission_scope_metadata(
                    scope,
                    seller_id=seller_id,
                    warehouse_id=warehouse_id,
                ),
                input_hash=hash_sensitive_text(self._tool_input_json(request)),
                input_excerpt=self._safe_excerpt(settings, self._tool_input_json(request)),
            )

            is_admin = scope.get("role") == UserRole.ADMINISTRATOR.value
            exceptions = await lookup_operational_exceptions(
                session,
                seller_id=seller_id,
                seller_ids=self._allowed_seller_ids(scope),
                warehouse_id=warehouse_id,
                warehouse_ids=self._allowed_warehouse_ids(scope),
                include_migration_failures=is_admin,
            )
            references = self._exception_references(exceptions)
            await ai_crud.complete_ai_tool_call(
                session,
                tool_call,
                status=AIToolCallStatus.COMPLETED.value,
                output_reference_count=len(references),
            )
            await audit_crud.create_audit_event(
                session,
                actor_user_id=UUID(str(scope["user_id"])),
                action_type=AuditActionType.AI_TOOL_CALL_RECORDED.value,
                source_record_type="ai_tool_calls",
                source_record_id=tool_call.id,
                metadata_json={
                    "tool_name": "exception_summary",
                    "exception_count": exceptions.total_exceptions,
                },
            )
            interaction_id = interaction.id

        categories = self._build_exception_categories(exceptions)
        fallback_narrative = self._build_exception_fallback_narrative(
            exceptions, categories
        )
        narrative, provider_name, model_name, provider_metadata = await self._provider_answer(
            settings,
            prompt=prompt,
            fallback_answer=fallback_narrative,
            evidence_payload={
                "total_exceptions": exceptions.total_exceptions,
                "categories": categories,
            },
        )
        await self._complete_interaction(
            interaction_id,
            status_value=AIInteractionStatus.COMPLETED.value,
            safety_decision=AISafetyDecision.ALLOW_READ_ONLY.value,
            answer=narrative,
            references=references,
            metadata_json=provider_metadata,
        )
        return {
            "interaction_id": interaction_id,
            "status": AIInteractionStatus.COMPLETED.value,
            "safety_decision": AISafetyDecision.ALLOW_READ_ONLY.value,
            "provider_name": provider_name,
            "model_name": model_name,
            "narrative_summary": narrative,
            "total_exceptions": exceptions.total_exceptions,
            "categories": categories,
            "references": references,
        }

    async def create_draft_recommendation(
        self,
        scope: dict[str, Any],
        request: AIDraftRecommendationRequest,
    ) -> dict[str, object]:
        """
        Generate a human-reviewable draft operational recommendation without executing mutations.

        Args:
            scope: Authenticated requester scope.
            request: Validated draft recommendation request.

        Returns:
            dict[str, object]: Created draft recommendation and parent interaction ID.

        Raises:
            HTTPException: If access is denied or safety checks fail.
        """
        self._require_admin_or_manager(scope)
        settings = get_settings()
        prompt = (
            request.prompt
            or f"Generate a draft recommendation for {request.recommendation_type}."
        )
        safety = self._safety_guard.evaluate_prompt(prompt)
        if not safety.allowed and safety.decision != AISafetyDecision.REFUSE_MUTATION:
            return await self._record_refusal(
                scope,
                settings=settings,
                category=AIRequestCategory.DRAFT_RECOMMENDATION.value,
                prompt=prompt,
                safety_decision=safety.decision,
                refusal_reason=safety.reason,
            )

        self._safety_guard.ensure_read_only_tool("draft_recommendation")
        async with transaction_session() as session:
            seller_id = await self._resolve_seller_id(
                session,
                scope,
                seller_id=request.seller_id,
                seller_code=request.seller_code,
            )
            warehouse_id = await self._resolve_warehouse_id(
                session,
                scope,
                warehouse_id=request.warehouse_id,
                warehouse_code=request.warehouse_code,
            )
            interaction = await self._create_interaction(
                session,
                scope,
                settings=settings,
                category=AIRequestCategory.DRAFT_RECOMMENDATION.value,
                prompt=prompt,
            )
            tool_call = await ai_crud.create_ai_tool_call(
                session,
                ai_interaction_id=interaction.id,
                tool_name="draft_recommendation",
                status=AIToolCallStatus.PENDING.value,
                permission_scope=self._permission_scope_metadata(
                    scope,
                    seller_id=seller_id,
                    warehouse_id=warehouse_id,
                ),
                input_hash=hash_sensitive_text(self._tool_input_json(request)),
                input_excerpt=self._safe_excerpt(settings, self._tool_input_json(request)),
            )

            draft_payload = {
                "recommendation_type": request.recommendation_type,
                "target_record_type": request.target_record_type,
                "target_record_id": str(request.target_record_id)
                if request.target_record_id
                else None,
                "details": request.details,
                "generated_reason": "Draft recommendation generated for human review.",
            }
            draft_payload_str = json.dumps(draft_payload, default=str)
            draft_action = await ai_crud.create_ai_draft_action(
                session,
                ai_interaction_id=interaction.id,
                action_type=request.recommendation_type,
                status=AIDraftActionStatus.DRAFTED.value,
                target_record_type=request.target_record_type,
                target_record_id=request.target_record_id,
                draft_payload_hash=hash_sensitive_text(draft_payload_str),
                draft_payload_excerpt=self._safe_excerpt(settings, draft_payload_str),
                requires_approval=True,
                metadata_json=request.details,
            )
            await ai_crud.complete_ai_tool_call(
                session,
                tool_call,
                status=AIToolCallStatus.COMPLETED.value,
                output_reference_count=1,
            )
            await audit_crud.create_audit_event(
                session,
                actor_user_id=UUID(str(scope["user_id"])),
                action_type=AuditActionType.AI_DRAFT_ACTION_CREATED.value,
                source_record_type="ai_draft_actions",
                source_record_id=draft_action.id,
                metadata_json={"action_type": request.recommendation_type},
            )
            draft_id = draft_action.id
            interaction_id = interaction.id

        recommendation_summary = (
            f"Draft recommendation '{request.recommendation_type}' created successfully. "
            f"Requires human approval before any operational execution."
        )
        references = []
        if request.target_record_type and request.target_record_id:
            references.append(
                {
                    "record_type": request.target_record_type,
                    "record_id": str(request.target_record_id),
                    "label": f"Target {request.target_record_type.title()}",
                    "metadata": {"draft_id": str(draft_id)},
                }
            )

        await self._complete_interaction(
            interaction_id,
            status_value=AIInteractionStatus.COMPLETED.value,
            safety_decision=AISafetyDecision.ALLOW_READ_ONLY.value,
            answer=recommendation_summary,
            references=references,
            metadata_json={"provider_used": False, "draft_only": True},
        )
        return {
            "interaction_id": interaction_id,
            "draft_id": draft_id,
            "action_type": request.recommendation_type,
            "status": AIDraftActionStatus.DRAFTED.value,
            "recommendation_summary": recommendation_summary,
            "draft_payload": draft_payload,
            "references": references,
        }

    async def list_draft_actions(
        self,
        scope: dict[str, Any],
        *,
        status: str | None = None,
        action_type: str | None = None,
        interaction_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, object]:
        """
        List AI draft actions for review by managers and administrators.

        Args:
            scope: Authenticated requester scope.
            status: Optional status filter.
            action_type: Optional action type filter.
            interaction_id: Optional parent interaction filter.
            limit: Maximum records to return.
            offset: Records to skip.

        Returns:
            dict[str, object]: Paginated list of draft actions.

        Raises:
            HTTPException: If access is denied.
        """
        self._require_admin_or_manager(scope)
        async with transaction_session() as session:
            items, total_count = await ai_crud.list_ai_draft_actions(
                session,
                status=status,
                action_type=action_type,
                interaction_id=interaction_id,
                limit=limit,
                offset=offset,
            )
            return {
                "items": [
                    {
                        "id": da.id,
                        "action_type": da.action_type,
                        "status": da.status,
                        "target_record_type": da.target_record_type,
                        "target_record_id": da.target_record_id,
                        "draft_payload_excerpt": da.draft_payload_excerpt,
                        "requires_approval": da.requires_approval,
                        "approved_by_user_id": da.approved_by_user_id,
                        "approved_at": da.approved_at,
                        "rejected_at": da.rejected_at,
                        "rejection_reason": da.rejection_reason,
                        "metadata_json": da.metadata_json,
                        "created_at": da.created_at,
                    }
                    for da in items
                ],
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
            }

    async def reject_draft_action(
        self,
        scope: dict[str, Any],
        draft_id: UUID,
        request: AIDraftRejectRequest,
    ) -> dict[str, object]:
        """
        Reject an AI draft recommendation without executing any mutation.

        Args:
            scope: Authenticated requester scope.
            draft_id: Draft action UUID.
            request: Validated reject request.

        Returns:
            dict[str, object]: Updated draft action details.

        Raises:
            HTTPException: If draft action is not found or access is denied.
        """
        self._require_admin_or_manager(scope)
        user_id = UUID(str(scope["user_id"]))
        async with transaction_session() as session:
            draft_action = await ai_crud.get_ai_draft_action_by_id(session, draft_id)
            if draft_action is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="AI draft action not found",
                )
            if draft_action.status != AIDraftActionStatus.DRAFTED.value:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot reject draft with status '{draft_action.status}'",
                )
            updated_draft = await ai_crud.update_ai_draft_action_status(
                session,
                draft_action,
                status=AIDraftActionStatus.REJECTED.value,
                rejected_at=datetime.now(UTC),
                rejection_reason=request.rejection_reason,
            )
            await audit_crud.create_audit_event(
                session,
                actor_user_id=user_id,
                action_type=AuditActionType.AI_DRAFT_ACTION_REJECTED.value,
                source_record_type="ai_draft_actions",
                source_record_id=updated_draft.id,
                metadata_json={"rejection_reason": request.rejection_reason},
            )
            return {
                "id": updated_draft.id,
                "action_type": updated_draft.action_type,
                "status": updated_draft.status,
                "target_record_type": updated_draft.target_record_type,
                "target_record_id": updated_draft.target_record_id,
                "draft_payload_excerpt": updated_draft.draft_payload_excerpt,
                "requires_approval": updated_draft.requires_approval,
                "approved_by_user_id": updated_draft.approved_by_user_id,
                "approved_at": updated_draft.approved_at,
                "rejected_at": updated_draft.rejected_at,
                "rejection_reason": updated_draft.rejection_reason,
                "metadata_json": updated_draft.metadata_json,
                "created_at": updated_draft.created_at,
            }

    def _require_admin_or_manager(self, scope: dict[str, Any]) -> None:
        """
        Enforce that caller has administrator or warehouse manager role.

        Args:
            scope: Authenticated requester scope.

        Returns:
            None.

        Raises:
            HTTPException: 403 Forbidden if not administrator or manager.
        """
        role = str(scope.get("role", ""))
        if role not in (UserRole.ADMINISTRATOR.value, UserRole.WAREHOUSE_MANAGER.value):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrator or Warehouse Manager access required",
            )

    def _assert_interaction_access(
        self, scope: dict[str, Any], interaction: AIInteraction
    ) -> None:
        """
        Verify that caller is allowed to view the interaction detail.

        Args:
            scope: Authenticated requester scope.
            interaction: Target AI interaction record.

        Returns:
            None.

        Raises:
            HTTPException: 403 Forbidden if unauthorized.
        """
        role = str(scope.get("role", ""))
        user_id = str(scope.get("user_id", ""))
        if role in (UserRole.ADMINISTRATOR.value, UserRole.WAREHOUSE_MANAGER.value):
            return
        if str(interaction.actor_user_id) == user_id:
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
        )

    def _exception_references(
        self, exceptions: OperationalExceptionEvidence
    ) -> list[dict[str, object]]:
        """
        Build reference records for operational exception items.

        Args:
            exceptions: Aggregated operational exceptions evidence.

        Returns:
            list[dict[str, object]]: Structured record references for response and audit.
        """
        refs: list[dict[str, object]] = []
        for rc in exceptions.overdue_receipts[:10]:
            refs.append(
                {
                    "record_type": "receipts",
                    "record_id": str(rc["receipt_id"]),
                    "label": f"Receipt {rc['receipt_number']}",
                    "metadata": {"status": rc["status"], "is_overdue": rc["is_overdue"]},
                }
            )
        for pt in exceptions.short_pick_exceptions[:10]:
            refs.append(
                {
                    "record_type": "pick_tasks",
                    "record_id": str(pt["pick_task_id"]),
                    "label": f"Pick Task {pt['pick_task_reference']}",
                    "metadata": {"status": pt["status"]},
                }
            )
        for tr in exceptions.transfer_variances[:10]:
            refs.append(
                {
                    "record_type": "transfers",
                    "record_id": str(tr["transfer_id"]),
                    "label": f"Transfer {tr['transfer_number']}",
                    "metadata": {"status": tr["status"]},
                }
            )
        for ret in exceptions.return_inspection_queues[:10]:
            refs.append(
                {
                    "record_type": "returns",
                    "record_id": str(ret["return_id"]),
                    "label": f"Return {ret['return_number']}",
                    "metadata": {"status": ret["status"]},
                }
            )
        return refs

    def _build_exception_categories(
        self, exceptions: OperationalExceptionEvidence
    ) -> list[dict[str, object]]:
        """
        Transform exception evidence into categorized UI summaries.

        Args:
            exceptions: Aggregated exceptions evidence.

        Returns:
            list[dict[str, object]]: Categorized exceptions with labels and severity.
        """
        return [
            {
                "category": "overdue_receipts",
                "label": "Overdue & Pending Receipts",
                "count": len(exceptions.overdue_receipts),
                "severity": "HIGH" if any(r.get("is_overdue") for r in exceptions.overdue_receipts) else "MEDIUM",
                "items": exceptions.overdue_receipts,
            },
            {
                "category": "short_picks",
                "label": "Short-Pick Exceptions",
                "count": len(exceptions.short_pick_exceptions),
                "severity": "HIGH" if exceptions.short_pick_exceptions else "LOW",
                "items": exceptions.short_pick_exceptions,
            },
            {
                "category": "expired_reservations",
                "label": "Expired & Expiring Reservations",
                "count": len(exceptions.expired_or_expiring_reservations),
                "severity": "HIGH" if any(r.get("is_expired") for r in exceptions.expired_or_expiring_reservations) else "MEDIUM",
                "items": exceptions.expired_or_expiring_reservations,
            },
            {
                "category": "transfer_variances",
                "label": "Transfer Discrepancies",
                "count": len(exceptions.transfer_variances),
                "severity": "HIGH" if exceptions.transfer_variances else "LOW",
                "items": exceptions.transfer_variances,
            },
            {
                "category": "return_inspections",
                "label": "Return Inspection Queue",
                "count": len(exceptions.return_inspection_queues),
                "severity": "MEDIUM" if exceptions.return_inspection_queues else "LOW",
                "items": exceptions.return_inspection_queues,
            },
            {
                "category": "migration_failures",
                "label": "Migration Validation Failures",
                "count": len(exceptions.migration_validation_failures),
                "severity": "HIGH" if exceptions.migration_validation_failures else "LOW",
                "items": exceptions.migration_validation_failures,
            },
        ]

    def _build_exception_fallback_narrative(
        self,
        exceptions: OperationalExceptionEvidence,
        categories: list[dict[str, object]],
    ) -> str:
        """
        Build deterministic exception summary text.

        Args:
            exceptions: Aggregated exceptions evidence.
            categories: Formatted category summaries.

        Returns:
            str: Deterministic narrative summary.
        """
        if exceptions.total_exceptions == 0:
            return "No active operational exceptions found across the specified scope. Operations are in normal status."

        parts = [
            f"Identified {exceptions.total_exceptions} active operational exception(s) across warehouse subsystems:"
        ]
        for cat in categories:
            count = int(cat["count"])
            if count > 0:
                parts.append(f"- {cat['label']}: {count} item(s) [Severity: {cat['severity']}]")
        return "\n".join(parts)

    async def _resolve_seller_id(
        self,
        session: AsyncSession,
        scope: dict[str, Any],
        *,
        seller_id: UUID | None,
        seller_code: str | None,
    ) -> UUID | None:
        """
        Resolve and authorize an optional seller filter.

        Args:
            session: Transaction-scoped SQLAlchemy async session.
            scope: Authenticated requester scope.
            seller_id: Optional seller UUID.
            seller_code: Optional seller code.

        Returns:
            UUID | None: Authorized seller UUID or None.

        Raises:
            HTTPException: If the seller is not found or access is denied.
        """
        resolved_id = seller_id
        if seller_code is not None:
            seller = await identity_crud.get_seller_by_code(session, seller_code)
            if seller is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Seller not found",
                )
            resolved_id = seller.id
        if resolved_id is not None:
            assert_seller_access(scope, str(resolved_id))
        return resolved_id

    async def _lookup_operational_status(
        self,
        session: AsyncSession,
        *,
        record_type: str,
        request: AIOperationalStatusRequest,
        seller_id: UUID | None,
        warehouse_id: UUID | None,
    ) -> OperationalStatusEvidence | None:
        """
        Dispatch a status lookup to the approved read-only application tool.

        Args:
            session: Transaction-scoped SQLAlchemy async session.
            record_type: Operational record type.
            request: Validated status request.
            seller_id: Optional resolved seller filter.
            warehouse_id: Optional resolved warehouse filter.

        Returns:
            OperationalStatusEvidence | None: Matching evidence or None.

        Raises:
            HTTPException: If record_type is unsupported.
        """
        lookup_args = {
            "record_id": request.record_id,
            "reference_number": request.reference_number,
            "seller_id": seller_id,
            "warehouse_id": warehouse_id,
        }
        if record_type == "order":
            return await lookup_order_status(session, **lookup_args)
        if record_type == "receipt":
            return await lookup_receipt_status(session, **lookup_args)
        if record_type == "transfer":
            return await lookup_transfer_status(session, **lookup_args)
        if record_type == "shipment":
            return await lookup_shipment_status(session, **lookup_args)
        if record_type == "return":
            return await lookup_return_status(session, **lookup_args)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI status tool not found",
        )

    def _assert_status_evidence_access(
        self,
        scope: dict[str, Any],
        evidence: OperationalStatusEvidence,
    ) -> None:
        """
        Require requester scope to match the retrieved operational record.

        Args:
            scope: Authenticated requester scope.
            evidence: Retrieved operational status evidence.

        Returns:
            None.

        Raises:
            HTTPException: If seller or warehouse access is denied.
        """
        role = str(scope.get("role", ""))
        if role == UserRole.ADMINISTRATOR.value:
            return

        if role == UserRole.SELLER.value or scope.get("seller_ids"):
            assert_seller_access(scope, str(evidence.seller_id))
            return

        scoped_warehouse_ids = {str(value) for value in scope.get("warehouse_ids", [])}
        record_warehouse_ids = {str(value) for value in evidence.warehouse_ids}
        if scoped_warehouse_ids and scoped_warehouse_ids.intersection(record_warehouse_ids):
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    def _status_tool_config(self, record_type: str) -> tuple[str, str]:
        """
        Return read-only tool name and AI category for an operational record type.

        Args:
            record_type: Operational record type.

        Returns:
            tuple[str, str]: Tool name and AI request category.

        Raises:
            HTTPException: If record_type is unsupported.
        """
        configs = {
            "order": ("order_status", AIRequestCategory.ORDER_STATUS.value),
            "receipt": ("receipt_status", AIRequestCategory.RECEIPT_STATUS.value),
            "transfer": ("transfer_status", AIRequestCategory.TRANSFER_STATUS.value),
            "shipment": ("shipment_status", AIRequestCategory.SHIPMENT_STATUS.value),
            "return": ("return_status", AIRequestCategory.RETURN_STATUS.value),
        }
        config = configs.get(record_type)
        if config is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="AI status tool not found",
            )
        return config

    def _status_prompt(
        self,
        record_type: str,
        request: AIOperationalStatusRequest,
    ) -> str:
        """
        Build a deterministic read-only status prompt when caller omits one.

        Args:
            record_type: Operational record type.
            request: Validated status request.

        Returns:
            str: Safe read-only prompt text.

        Raises:
            None.
        """
        lookup_value = request.record_id or request.reference_number
        return f"Answer the current {record_type} status for {lookup_value}."

    async def _resolve_warehouse_id(
        self,
        session: AsyncSession,
        scope: dict[str, Any],
        *,
        warehouse_id: UUID | None,
        warehouse_code: str | None,
    ) -> UUID | None:
        """
        Resolve and authorize an optional warehouse filter.

        Args:
            session: Transaction-scoped SQLAlchemy async session.
            scope: Authenticated requester scope.
            warehouse_id: Optional warehouse UUID.
            warehouse_code: Optional warehouse code.

        Returns:
            UUID | None: Authorized warehouse UUID or None.

        Raises:
            HTTPException: If the warehouse is not found or access is denied.
        """
        resolved_id = warehouse_id
        if warehouse_code is not None:
            warehouse = await identity_crud.get_warehouse_by_code(session, warehouse_code)
            if warehouse is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Warehouse not found",
                )
            resolved_id = warehouse.id
        if resolved_id is not None:
            assert_warehouse_access(scope, str(resolved_id))
        return resolved_id

    async def _create_interaction(
        self,
        session: AsyncSession,
        scope: dict[str, Any],
        *,
        settings: Settings,
        category: str,
        prompt: str,
    ) -> AIInteraction:
        """
        Create an AI interaction and top-level audit event.

        Args:
            session: Transaction-scoped SQLAlchemy async session.
            scope: Authenticated requester scope.
            settings: Application settings.
            category: AI request category.
            prompt: Raw user prompt or generated read-only prompt.

        Returns:
            AIInteraction: Persisted AI interaction record.

        Raises:
            sqlalchemy.exc.SQLAlchemyError: If persistence fails.
        """
        interaction = await ai_crud.create_ai_interaction(
            session,
            actor_user_id=UUID(str(scope["user_id"])),
            correlation_id=str(uuid4()),
            request_category=category,
            status=AIInteractionStatus.PENDING.value,
            provider_name=settings.ai_provider,
            model_name=settings.ai_model,
            prompt_hash=hash_sensitive_text(prompt),
            prompt_excerpt=self._safe_excerpt(settings, prompt),
            safety_decision=AISafetyDecision.ALLOW_READ_ONLY.value,
            seller_scope=list(scope.get("seller_ids", [])),
            warehouse_scope=list(scope.get("warehouse_ids", [])),
        )
        await audit_crud.create_audit_event(
            session,
            actor_user_id=UUID(str(scope["user_id"])),
            action_type=AuditActionType.AI_INTERACTION_CREATED.value,
            source_record_type="ai_interactions",
            source_record_id=interaction.id,
            metadata_json={"request_category": category},
        )
        return interaction

    async def _record_refusal(
        self,
        scope: dict[str, Any],
        *,
        settings: Settings,
        category: str,
        prompt: str,
        safety_decision: AISafetyDecision,
        refusal_reason: str | None,
    ) -> dict[str, object]:
        """
        Persist and return a safe AI refusal response.

        Args:
            scope: Authenticated requester scope.
            settings: Application settings.
            category: AI request category.
            prompt: Raw user prompt.
            safety_decision: Safety refusal decision.
            refusal_reason: Safe refusal reason.

        Returns:
            dict[str, object]: Response-ready refusal payload.

        Raises:
            sqlalchemy.exc.SQLAlchemyError: If audit persistence fails.
        """
        answer = refusal_reason or "The AI request was refused by safety guardrails."
        async with transaction_session() as session:
            interaction = await ai_crud.create_ai_interaction(
                session,
                actor_user_id=UUID(str(scope["user_id"])),
                correlation_id=str(uuid4()),
                request_category=category,
                status=AIInteractionStatus.REFUSED.value,
                provider_name="disabled",
                model_name=settings.ai_model,
                prompt_hash=hash_sensitive_text(prompt),
                prompt_excerpt=self._safe_excerpt(settings, prompt),
                response_excerpt=make_safe_excerpt(
                    answer,
                    max_chars=settings.ai_response_excerpt_chars,
                ),
                safety_decision=safety_decision.value,
                refusal_reason=answer,
                seller_scope=list(scope.get("seller_ids", [])),
                warehouse_scope=list(scope.get("warehouse_ids", [])),
            )
            await ai_crud.complete_ai_interaction(
                session,
                interaction,
                status=AIInteractionStatus.REFUSED.value,
                safety_decision=safety_decision.value,
                response_excerpt=make_safe_excerpt(
                    answer,
                    max_chars=settings.ai_response_excerpt_chars,
                ),
                refusal_reason=answer,
            )
            await audit_crud.create_audit_event(
                session,
                actor_user_id=UUID(str(scope["user_id"])),
                action_type=AuditActionType.AI_SAFETY_REFUSAL_RECORDED.value,
                source_record_type="ai_interactions",
                source_record_id=interaction.id,
                reason=answer,
                metadata_json={"request_category": category},
            )
            interaction_id = interaction.id

        return {
            "interaction_id": interaction_id,
            "status": AIInteractionStatus.REFUSED.value,
            "safety_decision": safety_decision.value,
            "provider_name": "disabled",
            "model_name": settings.ai_model,
            "answer": answer,
            "references": [],
            "record": None,
            "rows": [],
            "movements": [],
        }

    async def _provider_answer(
        self,
        settings: Settings,
        *,
        prompt: str,
        fallback_answer: str,
        evidence_payload: dict[str, object],
    ) -> tuple[str, str, str, dict[str, object]]:
        """
        Generate optional provider wording or return deterministic fallback text.

        Args:
            settings: Application settings.
            prompt: User prompt or generated read-only prompt.
            fallback_answer: Deterministic answer from application evidence.
            evidence_payload: Retrieved application evidence for provider context.

        Returns:
            tuple[str, str, str, dict[str, object]]: Answer, provider, model, metadata.

        Raises:
            None.
        """
        if not settings.ai_enabled:
            return fallback_answer, "disabled", settings.ai_model, {"provider_used": False}

        try:
            provider = build_ai_provider(settings)
            provider_prompt = self._provider_prompt(prompt, fallback_answer, evidence_payload)
            response = await provider.generate_text(
                AIProviderRequest(
                    prompt=provider_prompt,
                    model_name=settings.ai_model,
                    system_instruction=(
                        "You are a read-only warehouse operations assistant. "
                        "Use only supplied application evidence. Do not propose "
                        "or perform mutations, seller communications, SQL, or "
                        "scope bypasses."
                    ),
                )
            )
            if not response.text.strip():
                return fallback_answer, response.provider_name, response.model_name, {
                    "provider_used": True,
                    "provider_empty_response": True,
                }
            return response.text.strip(), response.provider_name, response.model_name, {
                "provider_used": True,
            }
        except (AIProviderExecutionError, AIProviderUnavailableError) as error:
            logger.warning("AI provider fallback used: %s", error.__class__.__name__)
            return fallback_answer, "disabled", settings.ai_model, {
                "provider_used": False,
                "provider_fallback_reason": error.__class__.__name__,
            }

    async def _complete_interaction(
        self,
        interaction_id: UUID,
        *,
        status_value: str,
        safety_decision: str,
        answer: str,
        references: list[dict[str, object]],
        metadata_json: dict[str, object],
    ) -> None:
        """
        Update an AI interaction with final answer evidence.

        Args:
            interaction_id: AI interaction UUID.
            status_value: Final interaction status.
            safety_decision: Final safety decision.
            answer: Final answer text.
            references: Retrieved application references.
            metadata_json: Safe provider metadata.

        Returns:
            None.

        Raises:
            sqlalchemy.exc.SQLAlchemyError: If persistence fails.
        """
        settings = get_settings()
        async with transaction_session() as session:
            interaction = await ai_crud.get_ai_interaction_by_id(session, interaction_id)
            if interaction is None:
                logger.warning("AI interaction missing during completion: %s", interaction_id)
                return
            await ai_crud.complete_ai_interaction(
                session,
                interaction,
                status=status_value,
                safety_decision=safety_decision,
                response_excerpt=make_safe_excerpt(
                    answer,
                    max_chars=settings.ai_response_excerpt_chars,
                ),
                retrieved_references=references,
                metadata_json=metadata_json,
            )

    def _allowed_seller_ids(self, scope: dict[str, Any]) -> list[UUID] | None:
        """
        Return seller UUIDs from scope for scoped roles.

        Args:
            scope: Authenticated requester scope.

        Returns:
            list[UUID] | None: Allowed seller IDs or None for unrestricted seller filter.

        Raises:
            ValueError: If a scoped ID is malformed.
        """
        if scope.get("role") == UserRole.ADMINISTRATOR.value:
            return None
        seller_ids = [UUID(str(value)) for value in scope.get("seller_ids", [])]
        return seller_ids or None

    def _allowed_warehouse_ids(self, scope: dict[str, Any]) -> list[UUID] | None:
        """
        Return warehouse UUIDs from scope for scoped roles.

        Args:
            scope: Authenticated requester scope.

        Returns:
            list[UUID] | None: Allowed warehouse IDs or None for unrestricted filter.

        Raises:
            ValueError: If a scoped ID is malformed.
        """
        if scope.get("role") == UserRole.ADMINISTRATOR.value:
            return None
        warehouse_ids = [UUID(str(value)) for value in scope.get("warehouse_ids", [])]
        return warehouse_ids or None

    def _permission_scope_metadata(
        self,
        scope: dict[str, Any],
        *,
        seller_id: UUID | None,
        warehouse_id: UUID | None,
    ) -> dict[str, object]:
        """
        Build safe scope metadata for AI tool call audit.

        Args:
            scope: Authenticated requester scope.
            seller_id: Optional requested seller filter.
            warehouse_id: Optional requested warehouse filter.

        Returns:
            dict[str, object]: Safe seller/warehouse scope metadata.

        Raises:
            None.
        """
        return {
            "role": str(scope.get("role", "")),
            "seller_ids": list(scope.get("seller_ids", [])),
            "warehouse_ids": list(scope.get("warehouse_ids", [])),
            "requested_seller_id": str(seller_id) if seller_id is not None else None,
            "requested_warehouse_id": str(warehouse_id) if warehouse_id is not None else None,
        }

    def _safe_excerpt(self, settings: Settings, value: str) -> str | None:
        """
        Return a safe prompt/input excerpt when excerpt logging is enabled.

        Args:
            settings: Application settings.
            value: Raw sensitive text.

        Returns:
            str | None: Redacted excerpt or None.

        Raises:
            None.
        """
        if not settings.ai_log_prompt_excerpts:
            return None
        return make_safe_excerpt(value, max_chars=settings.ai_prompt_excerpt_chars)

    def _tool_input_json(self, request: Any) -> str:
        """
        Serialize a Pydantic request model for hashing and optional redacted audit.

        Args:
            request: Pydantic request model.

        Returns:
            str: Stable JSON representation.

        Raises:
            TypeError: If the request cannot be serialized.
        """
        return request.model_dump_json()

    def _provider_prompt(
        self,
        prompt: str,
        fallback_answer: str,
        evidence_payload: dict[str, object],
    ) -> str:
        """
        Build a provider prompt constrained to application evidence.

        Args:
            prompt: User prompt or generated read-only prompt.
            fallback_answer: Deterministic application answer.
            evidence_payload: Retrieved application records.

        Returns:
            str: Provider prompt.

        Raises:
            TypeError: If evidence cannot be JSON serialized.
        """
        return (
            f"User inquiry:\n{prompt}\n\n"
            f"Warehouse evidence (live records):\n{json.dumps(evidence_payload, default=str)}\n\n"
            f"Guidance/Fallback context:\n{fallback_answer}\n\n"
            "Instructions for AI:\n"
            "- Answer the user's inquiry directly, conversationally, and accurately based on the supplied warehouse evidence.\n"
            "- If the user asks for items with 0 quantity, low stock, or category breakdowns (e.g. headphones, hoodies, sellers), analyze the evidence and give a clear, direct answer.\n"
            "- Keep your response professional, well-formatted (using bolding and bullet points where helpful), and strictly grounded in the live evidence."
        )

    def _availability_fallback_answer(
        self,
        sku: str,
        rows: Sequence[AvailableInventoryEvidence],
    ) -> str:
        """
        Build deterministic available inventory answer text.

        Args:
            sku: Product SKU or search query.
            rows: Available inventory evidence rows.

        Returns:
            str: Deterministic answer text.

        Raises:
            None.
        """
        if not rows:
            return f"No AVAILABLE inventory balance records were found matching '{sku}'."
        unique_skus = {row.sku for row in rows}
        if len(unique_skus) > 1:
            total_units = sum(row.available_quantity for row in rows)
            return (
                f"Found available inventory across {len(rows)} facility balance record(s) for {len(unique_skus)} product(s). "
                f"Total available stock is {total_units:.2f} units across warehouses."
            )
        parts = [
            f"{row.available_quantity} units at warehouse {row.warehouse_code} "
            f"for seller {row.seller_code}"
            for row in rows
        ]
        return f"Product {rows[0].sku} ({rows[0].product_name}) has " + "; ".join(parts) + "."

    def _ledger_fallback_answer(
        self,
        sku: str,
        movements: Sequence[LedgerMovementEvidence],
    ) -> str:
        """
        Build deterministic movement ledger explanation text.

        Args:
            sku: Product SKU.
            movements: Recent movement evidence rows.

        Returns:
            str: Deterministic explanation text.

        Raises:
            None.
        """
        if not movements:
            return f"No inventory movement ledger rows were found for SKU {sku}."

        total_delta = sum((row.quantity_delta for row in movements), Decimal("0.00"))
        newest = movements[0]
        return (
            f"Found {len(movements)} recent ledger movement(s) for SKU {sku}. "
            f"The net delta across returned rows is {total_delta}. "
            f"The latest movement is {newest.movement_type} with delta "
            f"{newest.quantity_delta} in state {newest.inventory_state} at "
            f"warehouse {newest.warehouse_code}."
        )

    def _availability_references(
        self,
        rows: Sequence[AvailableInventoryEvidence],
    ) -> list[dict[str, object]]:
        """
        Build application references for available inventory evidence.

        Args:
            rows: Available inventory evidence rows.

        Returns:
            list[dict[str, object]]: Response and audit references.

        Raises:
            None.
        """
        references: list[dict[str, object]] = []
        for row in rows:
            references.append(
                {
                    "record_type": "products",
                    "record_id": str(row.product_id),
                    "label": f"Product {row.sku}",
                    "metadata": {"seller_code": row.seller_code},
                }
            )
            references.append(
                {
                    "record_type": "warehouses",
                    "record_id": str(row.warehouse_id),
                    "label": f"Warehouse {row.warehouse_code}",
                    "metadata": {"seller_code": row.seller_code},
                }
            )
        return references

    def _ledger_references(
        self,
        movements: Sequence[LedgerMovementEvidence],
    ) -> list[dict[str, object]]:
        """
        Build application references for ledger movement evidence.

        Args:
            movements: Movement evidence rows.

        Returns:
            list[dict[str, object]]: Response and audit references.

        Raises:
            None.
        """
        return [
            {
                "record_type": "inventory_movements",
                "record_id": str(row.movement_id),
                "label": f"{row.movement_type} {row.quantity_delta} {row.inventory_state}",
                "metadata": {
                    "seller_code": row.seller_code,
                    "warehouse_code": row.warehouse_code,
                    "source_type": row.source_type,
                },
            }
            for row in movements
        ]

    def _status_references(
        self,
        evidence: OperationalStatusEvidence,
    ) -> list[dict[str, object]]:
        """
        Build application references for operational status evidence.

        Args:
            evidence: Operational status evidence.

        Returns:
            list[dict[str, object]]: Response and audit references.

        Raises:
            None.
        """
        references = [
            {
                "record_type": f"{evidence.record_type}s",
                "record_id": str(evidence.record_id),
                "label": f"{evidence.record_type.title()} {evidence.reference_number}",
                "metadata": {"status": evidence.status, "seller_code": evidence.seller_code},
            }
        ]
        for index, warehouse_id in enumerate(evidence.warehouse_ids):
            warehouse_code = evidence.warehouse_codes[index]
            references.append(
                {
                    "record_type": "warehouses",
                    "record_id": str(warehouse_id),
                    "label": f"Warehouse {warehouse_code}",
                    "metadata": {"record_type": evidence.record_type},
                }
            )
        return references

    def _status_record(self, evidence: OperationalStatusEvidence) -> dict[str, object]:
        """
        Convert operational status evidence to response dictionary.

        Args:
            evidence: Operational status evidence.

        Returns:
            dict[str, object]: Response record payload.

        Raises:
            None.
        """
        return {
            "record_type": evidence.record_type,
            "record_id": evidence.record_id,
            "reference_number": evidence.reference_number,
            "status": evidence.status,
            "seller_id": evidence.seller_id,
            "seller_code": evidence.seller_code,
            "warehouse_ids": evidence.warehouse_ids,
            "warehouse_codes": evidence.warehouse_codes,
            "summary": evidence.summary,
            "details": evidence.details,
        }

    def _status_fallback_answer(self, evidence: OperationalStatusEvidence) -> str:
        """
        Build deterministic operational status answer text.

        Args:
            evidence: Operational status evidence.

        Returns:
            str: Deterministic status answer.

        Raises:
            None.
        """
        warehouse_text = ", ".join(evidence.warehouse_codes)
        detail_count = len(evidence.details)
        return (
            f"{evidence.record_type.title()} {evidence.reference_number} is "
            f"{evidence.status} for seller {evidence.seller_code} at "
            f"warehouse scope {warehouse_text}. Returned {detail_count} "
            f"detail row(s) as supporting evidence."
        )

    def _availability_row(self, row: AvailableInventoryEvidence) -> dict[str, object]:
        """
        Convert available inventory evidence to response dictionary.

        Args:
            row: Available inventory evidence row.

        Returns:
            dict[str, object]: Response row.

        Raises:
            None.
        """
        return {
            "seller_id": row.seller_id,
            "seller_code": row.seller_code,
            "product_id": row.product_id,
            "sku": row.sku,
            "product_name": row.product_name,
            "warehouse_id": row.warehouse_id,
            "warehouse_code": row.warehouse_code,
            "available_quantity": row.available_quantity,
        }

    def _ledger_movement_row(self, row: LedgerMovementEvidence) -> dict[str, object]:
        """
        Convert ledger movement evidence to response dictionary.

        Args:
            row: Ledger movement evidence row.

        Returns:
            dict[str, object]: Response row.

        Raises:
            None.
        """
        return {
            "movement_id": row.movement_id,
            "seller_id": row.seller_id,
            "seller_code": row.seller_code,
            "product_id": row.product_id,
            "sku": row.sku,
            "product_name": row.product_name,
            "warehouse_id": row.warehouse_id,
            "warehouse_code": row.warehouse_code,
            "inventory_state": row.inventory_state,
            "quantity_delta": row.quantity_delta,
            "movement_type": row.movement_type,
            "source_type": row.source_type,
            "source_id": row.source_id,
            "reason_code": row.reason_code,
            "reason_text": row.reason_text,
            "recorded_at": row.recorded_at,
        }


ai_controller = AIController()
