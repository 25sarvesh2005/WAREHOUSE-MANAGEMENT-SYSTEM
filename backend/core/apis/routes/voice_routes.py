"""
FastAPI HTTP endpoints for voice-assisted receiving drafts, transcription, and speech synthesis.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from common.logger import get_logger
from common.rate_limit import voice_rate_limiter, voice_upload_rate_limiter
from common.warehouse_scope import get_warehouse_scope
from core.apis.schemas.requests.voice_request import (
    DiscardVoiceDraftRequest,
    ParseReceivingTranscriptRequest,
    SynthesizeVoiceRequest,
)
from core.apis.schemas.responses.voice_response import (
    VoiceInteractionItemResponse,
    VoiceInteractionListResponse,
    VoiceParsedLineResponse,
    VoiceReceivingDraftResponse,
    VoiceSynthesisResponse,
)
from core.controllers.voice_controller import voice_controller

logger = get_logger(__name__)

router = APIRouter(
    prefix="/v1/voice",
    tags=["Voice Receiving Assistant"],
    dependencies=[Depends(voice_rate_limiter)],
)


@router.post(
    "/receiving/transcribe",
    response_model=VoiceReceivingDraftResponse,
    status_code=status.HTTP_200_OK,
    summary="Transcribe audio clip and generate receiving draft",
    dependencies=[Depends(voice_upload_rate_limiter)],
)
async def transcribe_receiving_audio(
    file: UploadFile = File(..., description="Binary audio recording from push-to-talk."),
    warehouse_id: UUID | None = Form(default=None, description="Optional warehouse identifier."),
    product_id: UUID | None = Form(default=None, description="Optional selected product ID."),
    receipt_id: UUID | None = Form(default=None, description="Optional staged receipt ID."),
    language_code: str = Form(default="en-IN", description="BCP-47 language tag."),
    scope: dict[str, Any] = Depends(get_warehouse_scope),
) -> VoiceReceivingDraftResponse:
    """
    Upload recorded speech audio, transcribe via Deepgram/Sarvam, and generate receiving draft.

    Args:
        file: Multipart audio file payload.
        warehouse_id: Warehouse ID.
        product_id: Optional scanned product ID.
        receipt_id: Optional staged receipt ID.
        language_code: Target language code.
        scope: Authenticated warehouse scope.

    Returns:
        VoiceReceivingDraftResponse: Structured receiving lines and draft ID.

    Raises:
        HTTPException: If audio is invalid, safety is violated, or STT fails.
    """
    audio_bytes = await file.read()
    mime_type = file.content_type or "audio/webm"

    draft_record, interaction, parsed_draft = (
        await voice_controller.transcribe_and_draft_receiving_audio(
            scope=scope,
            audio_bytes=audio_bytes,
            mime_type=mime_type,
            warehouse_id=warehouse_id,
            product_id=product_id,
            receipt_id=receipt_id,
            language_code=language_code,
        )
    )

    return VoiceReceivingDraftResponse(
        draft_id=draft_record.id,
        interaction_id=interaction.id,
        transcript=parsed_draft.raw_transcript,
        confidence=float(interaction.transcript_confidence) if interaction.transcript_confidence else None,
        lines=[
            VoiceParsedLineResponse(
                quantity=line.quantity,
                inventory_state=line.inventory_state,
                condition_note=line.condition_note,
            )
            for line in parsed_draft.lines
        ],
        general_notes=parsed_draft.general_notes,
        needs_manual_review=parsed_draft.needs_manual_review,
        warnings=parsed_draft.warnings,
        product_id=draft_record.product_id,
        warehouse_id=draft_record.warehouse_id,
        receipt_id=draft_record.receipt_id,
        status=draft_record.status,
        safety_decision="ALLOW_DRAFT_ONLY",
        created_at=draft_record.created_at,
    )


@router.post(
    "/receiving/parse-transcript",
    response_model=VoiceReceivingDraftResponse,
    status_code=status.HTTP_200_OK,
    summary="Parse raw text transcript into structured receiving draft",
)
async def parse_receiving_transcript_endpoint(
    request: ParseReceivingTranscriptRequest,
    scope: dict[str, Any] = Depends(get_warehouse_scope),
) -> VoiceReceivingDraftResponse:
    """
    Parse a text transcript directly into structured receiving lines.

    Args:
        request: Transcript parsing payload.
        scope: Authenticated warehouse scope.

    Returns:
        VoiceReceivingDraftResponse: Structured draft lines and status.

    Raises:
        HTTPException: If transcript violates safety rules or fails parsing.
    """
    draft_record, interaction, parsed_draft = (
        await voice_controller.parse_receiving_transcript(
            scope=scope,
            transcript=request.transcript,
            warehouse_id=request.warehouse_id,
            product_id=request.product_id,
            receipt_id=request.receipt_id,
            language_code=request.language_code,
        )
    )

    return VoiceReceivingDraftResponse(
        draft_id=draft_record.id,
        interaction_id=interaction.id,
        transcript=parsed_draft.raw_transcript,
        confidence=1.0,
        lines=[
            VoiceParsedLineResponse(
                quantity=line.quantity,
                inventory_state=line.inventory_state,
                condition_note=line.condition_note,
            )
            for line in parsed_draft.lines
        ],
        general_notes=parsed_draft.general_notes,
        needs_manual_review=parsed_draft.needs_manual_review,
        warnings=parsed_draft.warnings,
        product_id=draft_record.product_id,
        warehouse_id=draft_record.warehouse_id,
        receipt_id=draft_record.receipt_id,
        status=draft_record.status,
        safety_decision="ALLOW_DRAFT_ONLY",
        created_at=draft_record.created_at,
    )


@router.post(
    "/speak",
    response_model=VoiceSynthesisResponse,
    status_code=status.HTTP_200_OK,
    summary="Synthesize read-back voice summary",
)
async def synthesize_voice_endpoint(
    request: SynthesizeVoiceRequest,
    scope: dict[str, Any] = Depends(get_warehouse_scope),
) -> VoiceSynthesisResponse:
    """
    Synthesize text into speech audio bytes (base64) using Sarvam AI Bulbul.

    Args:
        request: Voice synthesis text payload.
        scope: Authenticated user scope.

    Returns:
        VoiceSynthesisResponse: Base64 audio payload and MIME type.

    Raises:
        HTTPException: If TTS service is unconfigured or synthesis fails.
    """
    audio_base64, mime_type, provider_name, lang = (
        await voice_controller.synthesize_voice_response(
            scope=scope,
            text=request.text,
            language_code=request.language_code,
        )
    )

    return VoiceSynthesisResponse(
        audio_base64=audio_base64,
        mime_type=mime_type,
        provider_name=provider_name,
        language_code=lang,
    )


@router.post(
    "/drafts/{draft_id}/discard",
    response_model=VoiceReceivingDraftResponse,
    status_code=status.HTTP_200_OK,
    summary="Discard a voice receiving draft",
)
async def discard_voice_draft_endpoint(
    draft_id: UUID,
    request: DiscardVoiceDraftRequest | None = None,
    scope: dict[str, Any] = Depends(get_warehouse_scope),
) -> VoiceReceivingDraftResponse:
    """
    Mark a voice receiving draft proposal as discarded.

    Args:
        draft_id: Voice draft UUID.
        request: Optional discard reason.
        scope: Authenticated user scope.

    Returns:
        VoiceReceivingDraftResponse: Updated draft record.

    Raises:
        HTTPException: If draft is not found or user lacks permission.
    """
    reason = request.reason if request else None
    draft = await voice_controller.discard_voice_draft(
        scope=scope,
        draft_id=draft_id,
        reason=reason,
    )

    lines_raw = draft.structured_lines if isinstance(draft.structured_lines, list) else []
    lines_parsed = [
        VoiceParsedLineResponse(
            quantity=str(item.get("quantity", "0.00")),
            inventory_state=str(item.get("inventory_state", "AVAILABLE")),
            condition_note=item.get("condition_note"),
        )
        for item in lines_raw
        if isinstance(item, dict)
    ]

    return VoiceReceivingDraftResponse(
        draft_id=draft.id,
        interaction_id=draft.voice_interaction_id,
        transcript="",
        confidence=None,
        lines=lines_parsed,
        general_notes=draft.notes,
        needs_manual_review=False,
        warnings=[],
        product_id=draft.product_id,
        warehouse_id=draft.warehouse_id,
        receipt_id=draft.receipt_id,
        status=draft.status,
        safety_decision="DISCARDED",
        created_at=draft.created_at,
    )


@router.get(
    "/interactions",
    response_model=VoiceInteractionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List voice interaction audit log",
)
async def list_voice_interactions_endpoint(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: str | None = Query(default=None, alias="status"),
    scope: dict[str, Any] = Depends(get_warehouse_scope),
) -> VoiceInteractionListResponse:
    """
    List voice interaction audit records for administrators and warehouse managers.

    Args:
        limit: Max items.
        offset: Pagination offset.
        status_filter: Status filter.
        scope: Authenticated scope.

    Returns:
        VoiceInteractionListResponse: Paginated interaction list.

    Raises:
        HTTPException: If user is not administrator or warehouse manager.
    """
    items, total = await voice_controller.list_voice_interactions(
        scope=scope,
        limit=limit,
        offset=offset,
        status=status_filter,
    )

    return VoiceInteractionListResponse(
        total=total,
        items=[
            VoiceInteractionItemResponse(
                id=item.id,
                actor_user_id=item.actor_user_id,
                warehouse_id=item.warehouse_id,
                receipt_id=item.receipt_id,
                provider_name=item.provider_name,
                stt_provider=item.stt_provider,
                tts_provider=item.tts_provider,
                language_code=item.language_code,
                transcript_text=item.transcript_text,
                transcript_confidence=float(item.transcript_confidence) if item.transcript_confidence else None,
                status=item.status,
                created_at=item.created_at,
            )
            for item in items
        ],
    )
