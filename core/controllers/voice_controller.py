"""
--------------------------------------------------------------------------------
File        : core/controllers/voice_controller.py
Purpose     : Orchestrate voice-assisted receiving drafts, transcription, and speech synthesis.

Responsibilities:
    - Authorize warehouse operators and enforce warehouse/seller scope.
    - Validate audio payloads against size, MIME type, and duration limits.
    - Run strict safety checks preventing direct mutations and unauthorized commands.
    - Coordinate STT transcription (Deepgram/Sarvam) and transcript parsing (Gemini/rules).
    - Persist audited voice interactions and drafts without mutating inventory or receipts.
    - Provide text-to-speech audio summaries using Sarvam Bulbul.
    - Convert domain and provider exceptions into safe, user-friendly HTTP responses.

Flow:
    Voice Route
        ->
    VoiceController method
        ->
    Safety check / Providers / transaction_session() -> voice_crud / audit_crud
        ->
    Response schemas

Used By:
    - core/apis/routes/voice_routes.py

Returns:
    VoiceReceivingDraftResponse, VoiceSynthesisResponse, VoiceInteractionListResponse

Raises:
    HTTPException: On authorization, validation, safety refusal, or provider failures.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Sequence
from uuid import UUID, uuid4

from fastapi import HTTPException, status

from common.logger import get_logger
from common.warehouse_scope import assert_warehouse_access, require_roles
from core.config.settings import Settings, get_settings
from core.constants import AuditActionType, UserRole, VoiceInteractionStatus, VoiceReceivingDraftStatus
from core.cruds import audit_crud, voice_crud
from core.database.database import transaction_session
from core.models.voice_model import VoiceInteraction, VoiceReceivingDraft
from core.services.ai.provider import build_ai_provider
from core.services.voice.provider import (
    SpeechToTextProvider,
    TextToSpeechProvider,
    VoiceProviderUnavailableError,
    VoiceSynthesisError,
    VoiceTranscriptionError,
    build_stt_provider,
    build_tts_provider,
)
from core.services.voice.safety import check_voice_receiving_safety
from core.services.voice.transcript_parser import VoiceParsedReceivingDraft, parse_receiving_transcript

logger = get_logger(__name__)


class VoiceController:
    """Controller orchestrating voice-assisted receiving workflows."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        stt_provider: SpeechToTextProvider | None = None,
        tts_provider: TextToSpeechProvider | None = None,
    ) -> None:
        """
        Initialize the voice controller with settings and provider adapters.

        Args:
            settings: Optional settings override.
            stt_provider: Optional STT provider override (e.g. for testing).
            tts_provider: Optional TTS provider override (e.g. for testing).
        """
        self._settings = settings or get_settings()
        self._stt_provider = stt_provider
        self._tts_provider = tts_provider

    def _get_stt_provider(self) -> SpeechToTextProvider:
        """Return configured STT provider instance."""
        return self._stt_provider or build_stt_provider(self._settings)

    def _get_tts_provider(self) -> TextToSpeechProvider:
        """Return configured TTS provider instance."""
        return self._tts_provider or build_tts_provider(self._settings)

    async def transcribe_and_draft_receiving_audio(
        self,
        *,
        scope: dict[str, Any],
        audio_bytes: bytes,
        mime_type: str,
        warehouse_id: UUID | None = None,
        product_id: UUID | None = None,
        receipt_id: UUID | None = None,
        language_code: str = "en-IN",
        correlation_id: str | None = None,
    ) -> tuple[VoiceReceivingDraft, VoiceInteraction, VoiceParsedReceivingDraft]:
        """
        Transcribe uploaded audio clip, evaluate safety, and generate structured receiving draft.

        Args:
            scope: Authenticated warehouse user scope dictionary.
            audio_bytes: Binary audio data.
            mime_type: Audio MIME type.
            warehouse_id: Optional warehouse ID.
            product_id: Optional selected product ID.
            receipt_id: Optional linked receipt ID.
            language_code: Target language code.
            correlation_id: Optional request correlation ID.

        Returns:
            tuple[VoiceReceivingDraft, VoiceInteraction, VoiceParsedReceivingDraft]: Persisted records.

        Raises:
            HTTPException: On validation failure, safety refusal, or provider error.
        """
        # 1. Authorize role
        require_roles(scope, {UserRole.RECEIVER, UserRole.WAREHOUSE_MANAGER, UserRole.ADMINISTRATOR})
        if warehouse_id:
            assert_warehouse_access(scope, str(warehouse_id))

        actor_user_id = UUID(str(scope["user_id"]))

        # 2. Validate payload bounds
        if not audio_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded audio file is empty.",
            )

        max_bytes = self._settings.voice_max_audio_bytes
        if len(audio_bytes) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Audio payload exceeds maximum limit of {max_bytes // 1024 // 1024}MB.",
            )

        allowed_types = [t.strip().lower() for t in self._settings.voice_allowed_mime_types.split(",")]
        clean_mime = mime_type.lower().split(";")[0].strip()
        if clean_mime not in allowed_types:
            logger.warning("Rejected audio MIME type: %s", clean_mime)
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Audio type '{clean_mime}' is not supported. Allowed: {', '.join(allowed_types)}.",
            )

        cid = correlation_id or str(uuid4())
        stt_engine = self._get_stt_provider()

        # 3. Transcribe audio
        try:
            transcription = await stt_engine.transcribe(
                audio_bytes=audio_bytes,
                mime_type=clean_mime,
                language_code=language_code,
            )
        except VoiceProviderUnavailableError as exc:
            logger.warning("Voice STT provider unavailable: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Voice speech-to-text service is currently unavailable. Please enter quantities manually.",
            ) from exc
        except VoiceTranscriptionError as exc:
            logger.warning("Voice STT failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to transcribe audio. Please speak clearly or enter manually.",
            ) from exc

        transcript_text = transcription.transcript.strip()
        confidence_dec = (
            Decimal(str(round(transcription.confidence, 4)))
            if transcription.confidence is not None
            else None
        )

        # 4. Check Safety Boundaries
        safety = check_voice_receiving_safety(transcript_text)
        if not safety.is_safe:
            logger.warning("Voice command refused by safety guard: %s", safety.refusal_code)
            async with transaction_session() as session:
                await voice_crud.create_voice_interaction(
                    session,
                    actor_user_id=actor_user_id,
                    warehouse_id=warehouse_id,
                    receipt_id=receipt_id,
                    provider_name=stt_engine.provider_name,
                    stt_provider=stt_engine.provider_name,
                    tts_provider=self._settings.voice_tts_provider,
                    language_code=language_code,
                    status=VoiceInteractionStatus.FAILED.value,
                    correlation_id=cid,
                    transcript_text=transcript_text,
                    transcript_confidence=confidence_dec,
                    safety_flags=safety.safety_flags,
                    error_code=safety.refusal_code,
                    error_message=safety.refusal_reason,
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=safety.refusal_reason,
            )

        # 5. Parse transcript into structured draft lines
        ai_provider = build_ai_provider(self._settings)
        parsed_draft = await parse_receiving_transcript(
            transcript_text,
            ai_provider=ai_provider,
        )

        # 6. Persist Interaction, Receiving Draft, and Audit Record
        async with transaction_session() as session:
            interaction = await voice_crud.create_voice_interaction(
                session,
                actor_user_id=actor_user_id,
                warehouse_id=warehouse_id,
                receipt_id=receipt_id,
                provider_name=stt_engine.provider_name,
                stt_provider=stt_engine.provider_name,
                tts_provider=self._settings.voice_tts_provider,
                language_code=language_code,
                status=VoiceInteractionStatus.PARSED.value,
                correlation_id=cid,
                transcript_text=transcript_text,
                transcript_confidence=confidence_dec,
                parsed_payload=parsed_draft.to_dict(),
                safety_flags=safety.safety_flags,
            )

            draft_record = await voice_crud.create_voice_receiving_draft(
                session,
                voice_interaction_id=interaction.id,
                actor_user_id=actor_user_id,
                warehouse_id=warehouse_id,
                product_id=product_id,
                receipt_id=receipt_id,
                structured_lines=[line.to_dict() for line in parsed_draft.lines],
                notes=parsed_draft.general_notes,
                status=VoiceReceivingDraftStatus.DRAFTED.value,
            )

            await audit_crud.create_audit_event(
                session,
                actor_user_id=actor_user_id,
                action_type=AuditActionType.VOICE_RECEIVING_DRAFT_CREATED.value,
                source_record_type="voice_receiving_drafts",
                source_record_id=draft_record.id,
                reason="Voice receiving draft transcribed and parsed",
                metadata_json={
                    "interaction_id": str(interaction.id),
                    "line_count": len(parsed_draft.lines),
                    "confidence": str(confidence_dec) if confidence_dec else None,
                },
            )

        return draft_record, interaction, parsed_draft

    async def parse_receiving_transcript(
        self,
        *,
        scope: dict[str, Any],
        transcript: str,
        warehouse_id: UUID | None = None,
        product_id: UUID | None = None,
        receipt_id: UUID | None = None,
        language_code: str = "en-IN",
        correlation_id: str | None = None,
    ) -> tuple[VoiceReceivingDraft, VoiceInteraction, VoiceParsedReceivingDraft]:
        """
        Parse an existing text transcript directly without audio upload.

        Args:
            scope: Authenticated warehouse operator scope.
            transcript: Text string to parse.
            warehouse_id: Optional warehouse ID.
            product_id: Optional product ID.
            receipt_id: Optional receipt ID.
            language_code: Language tag.
            correlation_id: Request correlation ID.

        Returns:
            tuple[VoiceReceivingDraft, VoiceInteraction, VoiceParsedReceivingDraft]: Created draft records.

        Raises:
            HTTPException: On authorization, safety refusal, or parsing errors.
        """
        require_roles(scope, {UserRole.RECEIVER, UserRole.WAREHOUSE_MANAGER, UserRole.ADMINISTRATOR})
        if warehouse_id:
            assert_warehouse_access(scope, str(warehouse_id))

        actor_user_id = UUID(str(scope["user_id"]))
        clean_transcript = transcript.strip()
        if not clean_transcript:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Transcript must not be empty.",
            )

        cid = correlation_id or str(uuid4())

        # Safety boundary evaluation
        safety = check_voice_receiving_safety(clean_transcript)
        if not safety.is_safe:
            logger.warning("Voice transcript refused by safety guard: %s", safety.refusal_code)
            async with transaction_session() as session:
                await voice_crud.create_voice_interaction(
                    session,
                    actor_user_id=actor_user_id,
                    warehouse_id=warehouse_id,
                    receipt_id=receipt_id,
                    provider_name="transcript_input",
                    stt_provider="direct_text",
                    tts_provider=self._settings.voice_tts_provider,
                    language_code=language_code,
                    status=VoiceInteractionStatus.FAILED.value,
                    correlation_id=cid,
                    transcript_text=clean_transcript,
                    transcript_confidence=Decimal("1.0000"),
                    safety_flags=safety.safety_flags,
                    error_code=safety.refusal_code,
                    error_message=safety.refusal_reason,
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=safety.refusal_reason,
            )

        ai_provider = build_ai_provider(self._settings)
        parsed_draft = await parse_receiving_transcript(
            clean_transcript,
            ai_provider=ai_provider,
        )

        async with transaction_session() as session:
            interaction = await voice_crud.create_voice_interaction(
                session,
                actor_user_id=actor_user_id,
                warehouse_id=warehouse_id,
                receipt_id=receipt_id,
                provider_name="transcript_input",
                stt_provider="direct_text",
                tts_provider=self._settings.voice_tts_provider,
                language_code=language_code,
                status=VoiceInteractionStatus.PARSED.value,
                correlation_id=cid,
                transcript_text=clean_transcript,
                transcript_confidence=Decimal("1.0000"),
                parsed_payload=parsed_draft.to_dict(),
                safety_flags=safety.safety_flags,
            )

            draft_record = await voice_crud.create_voice_receiving_draft(
                session,
                voice_interaction_id=interaction.id,
                actor_user_id=actor_user_id,
                warehouse_id=warehouse_id,
                product_id=product_id,
                receipt_id=receipt_id,
                structured_lines=[line.to_dict() for line in parsed_draft.lines],
                notes=parsed_draft.general_notes,
                status=VoiceReceivingDraftStatus.DRAFTED.value,
            )

            await audit_crud.create_audit_event(
                session,
                actor_user_id=actor_user_id,
                action_type=AuditActionType.VOICE_RECEIVING_DRAFT_CREATED.value,
                source_record_type="voice_receiving_drafts",
                source_record_id=draft_record.id,
                reason="Direct transcript parsed into voice receiving draft",
                metadata_json={
                    "interaction_id": str(interaction.id),
                    "line_count": len(parsed_draft.lines),
                },
            )

        return draft_record, interaction, parsed_draft

    async def synthesize_voice_response(
        self,
        *,
        scope: dict[str, Any],
        text: str,
        language_code: str = "en-IN",
    ) -> tuple[str, str, str, str]:
        """
        Synthesize text into read-back audio using Sarvam AI Bulbul.

        Args:
            scope: Authenticated user scope.
            text: Text script to synthesize.
            language_code: Language code.

        Returns:
            tuple[str, str, str, str]: (audio_base64, mime_type, provider_name, language_code).

        Raises:
            HTTPException: If provider is unconfigured or synthesis fails.
        """
        require_roles(scope, {UserRole.RECEIVER, UserRole.WAREHOUSE_MANAGER, UserRole.ADMINISTRATOR})

        tts_engine = self._get_tts_provider()
        try:
            result = await tts_engine.synthesize(text=text, language_code=language_code)
            return (
                result.audio_base64,
                result.mime_type,
                result.provider_name,
                result.language_code,
            )
        except VoiceProviderUnavailableError as exc:
            logger.info("Voice TTS unavailable: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Text-to-speech audio synthesis is currently unavailable.",
            ) from exc
        except VoiceSynthesisError as exc:
            logger.warning("Voice TTS synthesis failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to synthesize voice audio.",
            ) from exc

    async def discard_voice_draft(
        self,
        *,
        scope: dict[str, Any],
        draft_id: UUID,
        reason: str | None = None,
    ) -> VoiceReceivingDraft:
        """
        Mark a voice receiving draft as discarded.

        Args:
            scope: Authenticated user scope.
            draft_id: Draft primary key UUID.
            reason: Optional discard rationale.

        Returns:
            VoiceReceivingDraft: Updated draft instance.

        Raises:
            HTTPException: If draft is not found or user lacks permission.
        """
        require_roles(scope, {UserRole.RECEIVER, UserRole.WAREHOUSE_MANAGER, UserRole.ADMINISTRATOR})
        actor_user_id = UUID(str(scope["user_id"]))
        role = str(scope.get("role", ""))

        async with transaction_session() as session:
            draft = await voice_crud.get_voice_draft_by_id(session, draft_id)
            if not draft:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Voice receiving draft not found.",
                )

            # Enforce actor ownership or manager/admin authority
            if draft.actor_user_id != actor_user_id and role not in {
                UserRole.ADMINISTRATOR.value,
                UserRole.WAREHOUSE_MANAGER.value,
            }:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only discard your own voice drafts.",
                )

            updated_draft = await voice_crud.update_voice_receiving_draft_status(
                session,
                draft_id=draft_id,
                status=VoiceReceivingDraftStatus.DISCARDED.value,
            )

            await audit_crud.create_audit_event(
                session,
                actor_user_id=actor_user_id,
                action_type=AuditActionType.VOICE_RECEIVING_DRAFT_DISCARDED.value,
                source_record_type="voice_receiving_drafts",
                source_record_id=draft_id,
                reason=reason or "Operator discarded voice receiving draft",
                metadata_json={"previous_status": draft.status},
            )

        return updated_draft or draft

    async def list_voice_interactions(
        self,
        *,
        scope: dict[str, Any],
        limit: int = 50,
        offset: int = 0,
        status: str | None = None,
    ) -> tuple[Sequence[VoiceInteraction], int]:
        """
        List voice interaction audit records for administrator and manager review.

        Args:
            scope: Authenticated user scope (Administrator or Warehouse Manager).
            limit: Limit count.
            offset: Offset index.
            status: Optional status filter.

        Returns:
            tuple[Sequence[VoiceInteraction], int]: List of interactions and total count.

        Raises:
            HTTPException: If actor lacks required admin or manager role.
        """
        require_roles(scope, {UserRole.ADMINISTRATOR, UserRole.WAREHOUSE_MANAGER})

        async with transaction_session() as session:
            return await voice_crud.list_voice_interactions(
                session,
                limit=limit,
                offset=offset,
                status=status,
            )


# Singleton controller instance for routes
voice_controller = VoiceController()
