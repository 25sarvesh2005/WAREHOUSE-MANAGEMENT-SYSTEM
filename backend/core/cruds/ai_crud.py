"""
--------------------------------------------------------------------------------
File        : core/cruds/ai_crud.py
Purpose     : Persist audited AI interaction records.

Responsibilities:
    - Insert and update AI interaction audit records inside caller-owned transactions.
    - Record read-tool calls and draft actions without executing operational mutations.
    - Keep AI persistence free of HTTP exceptions and business authorization policy.

Flow:
    Controller or approved service boundary
        ->
    ai_crud function
        ->
    SQLAlchemy session flush

Used By:
    - future read-only AI controllers and services

Returns:
    AIInteraction, AIToolCall, or AIDraftAction persistence records.

Raises:
    sqlalchemy.exc.SQLAlchemyError: On database failures.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Sequence
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.logger import get_logger
from core.models.ai_model import AIDraftAction, AIFeedback, AIInteraction, AIToolCall

logger = get_logger(__name__)


async def create_ai_interaction(
    session: AsyncSession,
    *,
    actor_user_id: UUID,
    correlation_id: str,
    request_category: str,
    status: str,
    provider_name: str,
    model_name: str,
    prompt_hash: str,
    safety_decision: str,
    prompt_excerpt: str | None = None,
    response_excerpt: str | None = None,
    refusal_reason: str | None = None,
    seller_scope: list[object] | None = None,
    warehouse_scope: list[object] | None = None,
    retrieved_references: list[object] | None = None,
    metadata_json: dict[str, object] | None = None,
) -> AIInteraction:
    """
    Create an audited AI interaction record.

    The caller owns the transaction and decides whether prompt/response
    excerpts are safe to persist before passing values into this function.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        actor_user_id: Authenticated user that requested the AI action.
        correlation_id: Request correlation identifier.
        request_category: AI request category.
        status: Initial AI interaction status.
        provider_name: AI provider name or disabled provider marker.
        model_name: Provider model name.
        prompt_hash: SHA-256 hash of the raw prompt.
        safety_decision: Safety guard decision for the request.
        prompt_excerpt: Optional redacted prompt excerpt.
        response_excerpt: Optional redacted response excerpt.
        refusal_reason: Optional safety or provider refusal reason.
        seller_scope: Seller IDs/codes visible to the actor.
        warehouse_scope: Warehouse IDs/codes visible to the actor.
        retrieved_references: Application records referenced by the answer.
        metadata_json: Safe structured metadata.

    Returns:
        AIInteraction: Persisted interaction record.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If persistence fails.
    """
    logger.debug("Creating AI interaction audit record %s", correlation_id)
    interaction = AIInteraction(
        actor_user_id=actor_user_id,
        correlation_id=correlation_id,
        request_category=request_category,
        status=status,
        provider_name=provider_name,
        model_name=model_name,
        prompt_hash=prompt_hash,
        prompt_excerpt=prompt_excerpt,
        response_excerpt=response_excerpt,
        safety_decision=safety_decision,
        refusal_reason=refusal_reason,
        seller_scope=seller_scope or [],
        warehouse_scope=warehouse_scope or [],
        retrieved_references=retrieved_references or [],
        metadata_json=metadata_json or {},
    )
    session.add(interaction)
    await session.flush()
    return interaction


async def get_ai_interaction_by_id(
    session: AsyncSession,
    interaction_id: UUID,
) -> AIInteraction | None:
    """
    Fetch an AI interaction by ID.

    Scope and permission checks stay in controllers or approved service
    boundaries; this function only performs persistence lookup.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        interaction_id: AI interaction UUID.

    Returns:
        AIInteraction | None: Matching interaction or None.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If the query fails.
    """
    result = await session.execute(
        select(AIInteraction).where(AIInteraction.id == interaction_id)
    )
    return result.scalar_one_or_none()


async def complete_ai_interaction(
    session: AsyncSession,
    interaction: AIInteraction,
    *,
    status: str,
    safety_decision: str,
    response_excerpt: str | None = None,
    refusal_reason: str | None = None,
    retrieved_references: list[object] | None = None,
    metadata_json: dict[str, object] | None = None,
    completed_at: datetime | None = None,
) -> AIInteraction:
    """
    Mark an AI interaction as completed, refused, or failed.

    Updates remain inside the caller-owned transaction so provider and audit
    evidence commit atomically with any surrounding read-only workflow records.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        interaction: Existing interaction model to update.
        status: Final interaction status.
        safety_decision: Final safety guard decision.
        response_excerpt: Optional redacted response excerpt.
        refusal_reason: Optional safe refusal or failure reason.
        retrieved_references: Application record references used in the answer.
        metadata_json: Safe structured metadata.
        completed_at: Completion timestamp supplied by the caller.

    Returns:
        AIInteraction: Updated interaction record.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If persistence fails.
    """
    interaction.status = status
    interaction.safety_decision = safety_decision
    interaction.response_excerpt = response_excerpt
    interaction.refusal_reason = refusal_reason
    if retrieved_references is not None:
        interaction.retrieved_references = retrieved_references
    if metadata_json is not None:
        interaction.metadata_json = metadata_json
    interaction.completed_at = completed_at or datetime.now(UTC)
    await session.flush()
    return interaction


async def create_ai_tool_call(
    session: AsyncSession,
    *,
    ai_interaction_id: UUID,
    tool_name: str,
    status: str,
    permission_scope: dict[str, object],
    input_hash: str,
    input_excerpt: str | None = None,
    output_reference_count: int = 0,
    error_message: str | None = None,
    started_at: datetime | None = None,
) -> AIToolCall:
    """
    Create an audited AI read-tool call record.

    This function records evidence only. It does not execute tool logic and it
    does not allow mutation behavior.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        ai_interaction_id: Parent AI interaction UUID.
        tool_name: Approved read-only tool name.
        status: Tool call status.
        permission_scope: Seller and warehouse scope applied to the tool.
        input_hash: SHA-256 hash of the tool input.
        input_excerpt: Optional redacted tool input excerpt.
        output_reference_count: Number of referenced application records.
        error_message: Optional safe error summary.
        started_at: Optional caller-supplied start timestamp.

    Returns:
        AIToolCall: Persisted tool call audit record.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If persistence fails.
    """
    tool_call = AIToolCall(
        ai_interaction_id=ai_interaction_id,
        tool_name=tool_name,
        status=status,
        permission_scope=permission_scope,
        input_hash=input_hash,
        input_excerpt=input_excerpt,
        output_reference_count=output_reference_count,
        error_message=error_message,
        started_at=started_at or datetime.now(UTC),
    )
    session.add(tool_call)
    await session.flush()
    return tool_call


async def complete_ai_tool_call(
    session: AsyncSession,
    tool_call: AIToolCall,
    *,
    status: str,
    output_reference_count: int,
    error_message: str | None = None,
    completed_at: datetime | None = None,
) -> AIToolCall:
    """
    Mark an AI tool call as completed, denied, or failed.

    The caller supplies safe counts and error summaries rather than raw provider
    or database payloads.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        tool_call: Existing tool call model to update.
        status: Final tool call status.
        output_reference_count: Number of referenced application records.
        error_message: Optional safe error summary.
        completed_at: Optional caller-supplied completion timestamp.

    Returns:
        AIToolCall: Updated tool call audit record.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If persistence fails.
    """
    tool_call.status = status
    tool_call.output_reference_count = output_reference_count
    tool_call.error_message = error_message
    tool_call.completed_at = completed_at or datetime.now(UTC)
    await session.flush()
    return tool_call


async def create_ai_draft_action(
    session: AsyncSession,
    *,
    ai_interaction_id: UUID,
    action_type: str,
    status: str,
    draft_payload_hash: str,
    target_record_type: str | None = None,
    target_record_id: UUID | None = None,
    draft_payload_excerpt: str | None = None,
    requires_approval: bool = True,
    metadata_json: dict[str, object] | None = None,
) -> AIDraftAction:
    """
    Create an audited draft action record without executing the action.

    Release A does not expose mutation tooling, but the audit table supports
    later human-approved draft workflows without redesigning persistence.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        ai_interaction_id: Parent AI interaction UUID.
        action_type: Draft action category.
        status: Draft action status.
        draft_payload_hash: SHA-256 hash of the raw draft payload.
        target_record_type: Optional application record type.
        target_record_id: Optional application record UUID.
        draft_payload_excerpt: Optional redacted draft payload excerpt.
        requires_approval: Whether human approval is required before execution.
        metadata_json: Safe structured metadata.

    Returns:
        AIDraftAction: Persisted draft action audit record.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If persistence fails.
    """
    draft_action = AIDraftAction(
        ai_interaction_id=ai_interaction_id,
        action_type=action_type,
        status=status,
        target_record_type=target_record_type,
        target_record_id=target_record_id,
        draft_payload_hash=draft_payload_hash,
        draft_payload_excerpt=draft_payload_excerpt,
        requires_approval=requires_approval,
        metadata_json=metadata_json or {},
    )
    session.add(draft_action)
    await session.flush()
    return draft_action


async def create_ai_feedback(
    session: AsyncSession,
    *,
    ai_interaction_id: UUID,
    actor_user_id: UUID,
    is_helpful: bool,
    comment: str | None = None,
    metadata_json: dict[str, object] | None = None,
) -> AIFeedback:
    """
    Create an audited user feedback record for an AI interaction.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        ai_interaction_id: AI interaction UUID receiving feedback.
        actor_user_id: Authenticated user submitting the feedback.
        is_helpful: True if interaction was helpful, False otherwise.
        comment: Optional textual explanation or feedback comment.
        metadata_json: Optional structured metadata.

    Returns:
        AIFeedback: Persisted feedback record.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If persistence fails.
    """
    feedback = AIFeedback(
        ai_interaction_id=ai_interaction_id,
        actor_user_id=actor_user_id,
        is_helpful=is_helpful,
        comment=comment,
        metadata_json=metadata_json or {},
    )
    session.add(feedback)
    await session.flush()
    return feedback


async def get_ai_feedbacks_for_interaction(
    session: AsyncSession,
    interaction_id: UUID,
) -> Sequence[AIFeedback]:
    """
    Fetch all feedback entries submitted for an interaction.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        interaction_id: AI interaction UUID.

    Returns:
        Sequence[AIFeedback]: Matching feedback records ordered by creation date.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If query execution fails.
    """
    result = await session.execute(
        select(AIFeedback)
        .where(AIFeedback.ai_interaction_id == interaction_id)
        .order_by(AIFeedback.created_at.asc())
    )
    return result.scalars().all()


async def list_ai_interactions(
    session: AsyncSession,
    *,
    actor_user_id: UUID | None = None,
    status: str | None = None,
    provider_name: str | None = None,
    request_category: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[Sequence[AIInteraction], int]:
    """
    List audited AI interactions with optional filtering and pagination.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        actor_user_id: Optional user filter.
        status: Optional status filter.
        provider_name: Optional provider name filter.
        request_category: Optional request category filter.
        start_date: Optional inclusive start timestamp.
        end_date: Optional inclusive end timestamp.
        limit: Maximum number of rows to return.
        offset: Number of rows to skip.

    Returns:
        tuple[Sequence[AIInteraction], int]: Page of interactions and total matching count.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If query execution fails.
    """
    query = select(AIInteraction)
    count_query = select(func.count(AIInteraction.id))

    if actor_user_id is not None:
        query = query.where(AIInteraction.actor_user_id == actor_user_id)
        count_query = count_query.where(AIInteraction.actor_user_id == actor_user_id)
    if status is not None:
        query = query.where(AIInteraction.status == status)
        count_query = count_query.where(AIInteraction.status == status)
    if provider_name is not None:
        query = query.where(AIInteraction.provider_name == provider_name)
        count_query = count_query.where(AIInteraction.provider_name == provider_name)
    if request_category is not None:
        query = query.where(AIInteraction.request_category == request_category)
        count_query = count_query.where(AIInteraction.request_category == request_category)
    if start_date is not None:
        query = query.where(AIInteraction.created_at >= start_date)
        count_query = count_query.where(AIInteraction.created_at >= start_date)
    if end_date is not None:
        query = query.where(AIInteraction.created_at <= end_date)
        count_query = count_query.where(AIInteraction.created_at <= end_date)

    total_count_result = await session.execute(count_query)
    total_count = total_count_result.scalar_one()

    result = await session.execute(
        query.order_by(desc(AIInteraction.created_at)).limit(limit).offset(offset)
    )
    items = result.scalars().all()
    return items, total_count


async def get_ai_interaction_detail(
    session: AsyncSession,
    interaction_id: UUID,
) -> tuple[AIInteraction | None, Sequence[AIToolCall], Sequence[AIDraftAction], Sequence[AIFeedback]]:
    """
    Fetch comprehensive audit detail for an interaction including tools, drafts, and feedback.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        interaction_id: AI interaction UUID.

    Returns:
        tuple[AIInteraction | None, Sequence[AIToolCall], Sequence[AIDraftAction], Sequence[AIFeedback]]:
            Parent interaction, child tool calls, draft actions, and feedbacks.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If queries fail.
    """
    interaction = await get_ai_interaction_by_id(session, interaction_id)
    if interaction is None:
        return None, [], [], []

    tool_calls_result = await session.execute(
        select(AIToolCall)
        .where(AIToolCall.ai_interaction_id == interaction_id)
        .order_by(AIToolCall.created_at.asc())
    )
    tool_calls = tool_calls_result.scalars().all()

    draft_actions_result = await session.execute(
        select(AIDraftAction)
        .where(AIDraftAction.ai_interaction_id == interaction_id)
        .order_by(AIDraftAction.created_at.asc())
    )
    draft_actions = draft_actions_result.scalars().all()

    feedbacks_result = await session.execute(
        select(AIFeedback)
        .where(AIFeedback.ai_interaction_id == interaction_id)
        .order_by(AIFeedback.created_at.asc())
    )
    feedbacks = feedbacks_result.scalars().all()

    return interaction, tool_calls, draft_actions, feedbacks


async def get_interaction_tool_and_draft_counts(
    session: AsyncSession,
    interaction_ids: Sequence[UUID],
) -> tuple[dict[UUID, int], dict[UUID, int], dict[UUID, dict[str, int]]]:
    """
    Batch aggregate tool call counts, draft action counts, and feedback stats for interaction IDs.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        interaction_ids: Sequence of AI interaction UUIDs.

    Returns:
        tuple[dict[UUID, int], dict[UUID, int], dict[UUID, dict[str, int]]]:
            Maps of interaction ID to tool count, draft count, and feedback stats dict.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If aggregation queries fail.
    """
    if not interaction_ids:
        return {}, {}, {}

    tool_counts: dict[UUID, int] = {i_id: 0 for i_id in interaction_ids}
    draft_counts: dict[UUID, int] = {i_id: 0 for i_id in interaction_ids}
    feedback_stats: dict[UUID, dict[str, int]] = {
        i_id: {"total": 0, "helpful": 0, "unhelpful": 0} for i_id in interaction_ids
    }

    tool_res = await session.execute(
        select(AIToolCall.ai_interaction_id, func.count(AIToolCall.id))
        .where(AIToolCall.ai_interaction_id.in_(interaction_ids))
        .group_by(AIToolCall.ai_interaction_id)
    )
    for i_id, count in tool_res.all():
        tool_counts[i_id] = count

    draft_res = await session.execute(
        select(AIDraftAction.ai_interaction_id, func.count(AIDraftAction.id))
        .where(AIDraftAction.ai_interaction_id.in_(interaction_ids))
        .group_by(AIDraftAction.ai_interaction_id)
    )
    for i_id, count in draft_res.all():
        draft_counts[i_id] = count

    feedback_res = await session.execute(
        select(
            AIFeedback.ai_interaction_id,
            func.count(AIFeedback.id),
            func.count(AIFeedback.id).filter(AIFeedback.is_helpful.is_(True)),
            func.count(AIFeedback.id).filter(AIFeedback.is_helpful.is_(False)),
        )
        .where(AIFeedback.ai_interaction_id.in_(interaction_ids))
        .group_by(AIFeedback.ai_interaction_id)
    )
    for i_id, total, helpful, unhelpful in feedback_res.all():
        feedback_stats[i_id] = {
            "total": total,
            "helpful": helpful,
            "unhelpful": unhelpful,
        }

    return tool_counts, draft_counts, feedback_stats


async def list_ai_draft_actions(
    session: AsyncSession,
    *,
    status: str | None = None,
    action_type: str | None = None,
    interaction_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[Sequence[AIDraftAction], int]:
    """
    List AI draft actions with filtering and pagination.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        status: Optional status filter.
        action_type: Optional action type filter.
        interaction_id: Optional parent interaction filter.
        limit: Maximum number of rows to return.
        offset: Number of rows to skip.

    Returns:
        tuple[Sequence[AIDraftAction], int]: Page of draft actions and total matching count.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If query execution fails.
    """
    query = select(AIDraftAction)
    count_query = select(func.count(AIDraftAction.id))

    if status is not None:
        query = query.where(AIDraftAction.status == status)
        count_query = count_query.where(AIDraftAction.status == status)
    if action_type is not None:
        query = query.where(AIDraftAction.action_type == action_type)
        count_query = count_query.where(AIDraftAction.action_type == action_type)
    if interaction_id is not None:
        query = query.where(AIDraftAction.ai_interaction_id == interaction_id)
        count_query = count_query.where(AIDraftAction.ai_interaction_id == interaction_id)

    total_count_result = await session.execute(count_query)
    total_count = total_count_result.scalar_one()

    result = await session.execute(
        query.order_by(desc(AIDraftAction.created_at)).limit(limit).offset(offset)
    )
    items = result.scalars().all()
    return items, total_count


async def get_ai_draft_action_by_id(
    session: AsyncSession,
    draft_id: UUID,
) -> AIDraftAction | None:
    """
    Fetch an AI draft action by its UUID.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        draft_id: Draft action UUID.

    Returns:
        AIDraftAction | None: Matching record or None.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If query fails.
    """
    result = await session.execute(
        select(AIDraftAction).where(AIDraftAction.id == draft_id)
    )
    return result.scalar_one_or_none()


async def update_ai_draft_action_status(
    session: AsyncSession,
    draft_action: AIDraftAction,
    *,
    status: str,
    rejected_at: datetime | None = None,
    rejection_reason: str | None = None,
    approved_by_user_id: UUID | None = None,
    approved_at: datetime | None = None,
) -> AIDraftAction:
    """
    Update the status and approval/rejection details of an AI draft action.

    Args:
        session: Transaction-scoped SQLAlchemy async session.
        draft_action: Existing draft action record to update.
        status: Target status value (e.g. REJECTED, APPROVED).
        rejected_at: Timestamp when rejection occurred.
        rejection_reason: Human-provided reason for rejecting the recommendation.
        approved_by_user_id: User UUID if approved.
        approved_at: Timestamp when approval occurred.

    Returns:
        AIDraftAction: Updated record.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If database update fails.
    """
    draft_action.status = status
    if rejected_at is not None:
        draft_action.rejected_at = rejected_at
    if rejection_reason is not None:
        draft_action.rejection_reason = rejection_reason
    if approved_by_user_id is not None:
        draft_action.approved_by_user_id = approved_by_user_id
    if approved_at is not None:
        draft_action.approved_at = approved_at
    await session.flush()
    return draft_action

