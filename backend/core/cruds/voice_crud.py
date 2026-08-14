"""
--------------------------------------------------------------------------------
File        : core/cruds/voice_crud.py
Purpose     : Provide database persistence operations for voice interactions and drafts.

Responsibilities:
    - Persist voice interaction records and transcription results.
    - Persist voice-generated receiving drafts with proposed lines.
    - Update interaction and draft statuses (e.g. APPLIED, DISCARDED).
    - List and retrieve voice audit interactions with pagination.
    - Never raise HTTPException directly; accept AsyncSession as the first parameter.

Flow:
    Voice Controller
        ->
    voice_crud functions
        ->
    Database session queries

Used By:
    - core/controllers/voice_controller.py

Returns:
    VoiceInteraction, VoiceReceivingDraft, or sequences of models.

Raises:
    SQLAlchemyError: On low-level database failure.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.voice_model import VoiceInteraction, VoiceReceivingDraft


async def create_voice_interaction(
    session: AsyncSession,
    *,
    actor_user_id: UUID,
    warehouse_id: UUID | None,
    receipt_id: UUID | None,
    provider_name: str,
    stt_provider: str,
    tts_provider: str | None,
    language_code: str = "en-IN",
    status: str = "TRANSCRIBED",
    correlation_id: str | None = None,
    transcript_text: str | None = None,
    transcript_confidence: Decimal | None = None,
    parsed_payload: dict[str, Any] | None = None,
    safety_flags: dict[str, Any] | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
) -> VoiceInteraction:
    """
    Create and persist a new voice interaction record.

    Args:
        session: Active async database session.
        actor_user_id: Authenticated user identifier.
        warehouse_id: Optional warehouse scope ID.
        receipt_id: Optional target receipt ID.
        provider_name: Overall voice provider name.
        stt_provider: Concrete STT provider used.
        tts_provider: Concrete TTS provider configured.
        language_code: Language code.
        status: Lifecycle status.
        correlation_id: Request tracing ID.
        transcript_text: Transcribed speech text.
        transcript_confidence: Confidence score between 0.0 and 1.0.
        parsed_payload: Parsed draft JSON.
        safety_flags: Safety audit metadata.
        error_code: Safe error code if failed.
        error_message: Safe error message if failed.

    Returns:
        VoiceInteraction: Persisted model instance.

    Raises:
        SQLAlchemyError: If insertion fails.
    """
    interaction = VoiceInteraction(
        actor_user_id=actor_user_id,
        warehouse_id=warehouse_id,
        receipt_id=receipt_id,
        provider_name=provider_name,
        stt_provider=stt_provider,
        tts_provider=tts_provider,
        language_code=language_code,
        status=status,
        correlation_id=correlation_id,
        transcript_text=transcript_text,
        transcript_confidence=transcript_confidence,
        parsed_payload=parsed_payload,
        safety_flags=safety_flags,
        error_code=error_code,
        error_message=error_message,
    )
    session.add(interaction)
    await session.flush()
    return interaction


async def update_voice_interaction_result(
    session: AsyncSession,
    *,
    interaction_id: UUID,
    status: str,
    transcript_text: str | None = None,
    transcript_confidence: Decimal | None = None,
    parsed_payload: dict[str, Any] | None = None,
    safety_flags: dict[str, Any] | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
) -> VoiceInteraction | None:
    """
    Update an existing voice interaction record with final transcription or parsing results.

    Args:
        session: Active async database session.
        interaction_id: ID of the voice interaction.
        status: New status string.
        transcript_text: Final transcript.
        transcript_confidence: Final confidence.
        parsed_payload: Parsed draft payload.
        safety_flags: Safety decision metadata.
        error_code: Error code if failed.
        error_message: Safe error description.

    Returns:
        VoiceInteraction | None: Updated model instance or None if not found.

    Raises:
        SQLAlchemyError: On database error.
    """
    stmt = select(VoiceInteraction).where(VoiceInteraction.id == interaction_id)
    result = await session.execute(stmt)
    interaction = result.scalar_one_or_none()
    if not interaction:
        return None

    interaction.status = status
    if transcript_text is not None:
        interaction.transcript_text = transcript_text
    if transcript_confidence is not None:
        interaction.transcript_confidence = transcript_confidence
    if parsed_payload is not None:
        interaction.parsed_payload = parsed_payload
    if safety_flags is not None:
        interaction.safety_flags = safety_flags
    if error_code is not None:
        interaction.error_code = error_code
    if error_message is not None:
        interaction.error_message = error_message

    await session.flush()
    return interaction


async def create_voice_receiving_draft(
    session: AsyncSession,
    *,
    voice_interaction_id: UUID,
    actor_user_id: UUID,
    warehouse_id: UUID | None,
    product_id: UUID | None,
    receipt_id: UUID | None,
    structured_lines: list[dict[str, Any]],
    notes: str | None = None,
    status: str = "DRAFTED",
) -> VoiceReceivingDraft:
    """
    Persist a new voice receiving draft proposal.

    Args:
        session: Active async database session.
        voice_interaction_id: Originating voice interaction ID.
        actor_user_id: User who recorded the voice draft.
        warehouse_id: Scoped warehouse ID.
        product_id: Selected product ID if known.
        receipt_id: Staged receipt ID if linked.
        structured_lines: List of parsed line dicts.
        notes: Extracted condition or general notes.
        status: Draft lifecycle status (default DRAFTED).

    Returns:
        VoiceReceivingDraft: Persisted draft instance.

    Raises:
        SQLAlchemyError: On database error.
    """
    draft = VoiceReceivingDraft(
        voice_interaction_id=voice_interaction_id,
        actor_user_id=actor_user_id,
        warehouse_id=warehouse_id,
        product_id=product_id,
        receipt_id=receipt_id,
        structured_lines=structured_lines,
        notes=notes,
        status=status,
    )
    session.add(draft)
    await session.flush()
    return draft


async def get_voice_draft_by_id(
    session: AsyncSession,
    draft_id: UUID,
) -> VoiceReceivingDraft | None:
    """
    Retrieve a voice receiving draft by primary key.

    Args:
        session: Active database session.
        draft_id: Draft primary key UUID.

    Returns:
        VoiceReceivingDraft | None: Found draft or None.

    Raises:
        SQLAlchemyError: On database query failure.
    """
    stmt = select(VoiceReceivingDraft).where(VoiceReceivingDraft.id == draft_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_voice_interaction_by_id(
    session: AsyncSession,
    interaction_id: UUID,
) -> VoiceInteraction | None:
    """
    Retrieve a voice interaction by primary key.

    Args:
        session: Active database session.
        interaction_id: Interaction primary key UUID.

    Returns:
        VoiceInteraction | None: Found interaction or None.

    Raises:
        SQLAlchemyError: On database query failure.
    """
    stmt = select(VoiceInteraction).where(VoiceInteraction.id == interaction_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update_voice_receiving_draft_status(
    session: AsyncSession,
    *,
    draft_id: UUID,
    status: str,
) -> VoiceReceivingDraft | None:
    """
    Update the lifecycle status of a voice receiving draft (e.g. APPLIED, DISCARDED).

    Args:
        session: Active database session.
        draft_id: Draft UUID.
        status: Target status string.

    Returns:
        VoiceReceivingDraft | None: Updated draft or None.

    Raises:
        SQLAlchemyError: On database update failure.
    """
    draft = await get_voice_draft_by_id(session, draft_id)
    if not draft:
        return None
    draft.status = status
    await session.flush()
    return draft


async def list_voice_interactions(
    session: AsyncSession,
    *,
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
    actor_user_id: UUID | None = None,
    warehouse_id: UUID | None = None,
) -> tuple[Sequence[VoiceInteraction], int]:
    """
    List voice interaction audit records with pagination and optional filters.

    Args:
        session: Active database session.
        limit: Max items to return.
        offset: Offset index for pagination.
        status: Optional status filter.
        actor_user_id: Optional actor filter.
        warehouse_id: Optional warehouse filter.

    Returns:
        tuple[Sequence[VoiceInteraction], int]: (Records, total_count).

    Raises:
        SQLAlchemyError: On query failure.
    """
    query = select(VoiceInteraction)
    count_query = select(func.count(VoiceInteraction.id))

    if status:
        query = query.where(VoiceInteraction.status == status)
        count_query = count_query.where(VoiceInteraction.status == status)
    if actor_user_id:
        query = query.where(VoiceInteraction.actor_user_id == actor_user_id)
        count_query = count_query.where(VoiceInteraction.actor_user_id == actor_user_id)
    if warehouse_id:
        query = query.where(VoiceInteraction.warehouse_id == warehouse_id)
        count_query = count_query.where(VoiceInteraction.warehouse_id == warehouse_id)

    total = await session.scalar(count_query) or 0
    query = query.order_by(desc(VoiceInteraction.created_at)).limit(limit).offset(offset)
    result = await session.execute(query)
    items = result.scalars().all()

    return items, total
