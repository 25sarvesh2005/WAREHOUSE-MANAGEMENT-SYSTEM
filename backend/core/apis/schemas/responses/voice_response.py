"""
--------------------------------------------------------------------------------
File        : core/apis/schemas/responses/voice_response.py
Purpose     : Response schemas for voice-assisted receiving drafts and synthesis.

Responsibilities:
    - Serialize structured voice receiving draft proposals.
    - Serialize voice synthesis audio payloads (base64).
    - Serialize voice interaction audit log items and pagination lists.

Flow:
    Voice Controller
        ->
    Pydantic Response Serialization
        ->
    Client API Response

Used By:
    - core/apis/routes/voice_routes.py
    - core/controllers/voice_controller.py

Returns:
    Serialized response data models.

Raises:
    None.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class VoiceParsedLineResponse(BaseModel):
    """Individual parsed receiving line proposal."""

    model_config = ConfigDict(from_attributes=True)

    quantity: str = Field(..., description="Decimal quantity string.")
    inventory_state: str = Field(..., description="Target inventory state: AVAILABLE, DAMAGED, QUARANTINED.")
    condition_note: str | None = Field(default=None, description="Extracted condition note.")


class VoiceReceivingDraftResponse(BaseModel):
    """Structured response containing proposed receiving draft lines."""

    model_config = ConfigDict(from_attributes=True)

    draft_id: UUID = Field(..., description="Voice draft primary key UUID.")
    interaction_id: UUID = Field(..., description="Voice interaction audit UUID.")
    transcript: str = Field(..., description="Spoken transcript parsed into draft.")
    confidence: float | None = Field(default=None, description="STT transcription confidence.")
    lines: list[VoiceParsedLineResponse] = Field(..., description="Proposed receiving lines.")
    general_notes: str | None = Field(default=None, description="General receipt notes.")
    needs_manual_review: bool = Field(..., description="Flag if speech was ambiguous.")
    warnings: list[str] = Field(default_factory=list, description="Parsing warnings or notices.")
    product_id: UUID | None = Field(default=None, description="Selected product ID if known.")
    warehouse_id: UUID | None = Field(default=None, description="Warehouse location ID.")
    receipt_id: UUID | None = Field(default=None, description="Linked receipt ID if present.")
    status: str = Field(..., description="Draft status: DRAFTED, APPLIED_TO_RECEIPT_DRAFT, DISCARDED.")
    safety_decision: str = Field(default="ALLOW_DRAFT_ONLY", description="Safety guard outcome.")
    created_at: datetime = Field(..., description="Draft creation timestamp.")


class VoiceSynthesisResponse(BaseModel):
    """Response containing synthesized speech audio."""

    model_config = ConfigDict(from_attributes=True)

    audio_base64: str = Field(..., description="Base64-encoded audio payload.")
    mime_type: str = Field(..., description="MIME type of synthesized audio (e.g. audio/wav).")
    provider_name: str = Field(..., description="TTS provider name (e.g. sarvam).")
    language_code: str = Field(..., description="Language tag used during synthesis.")


class VoiceInteractionItemResponse(BaseModel):
    """Audit summary item for a voice interaction."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Voice interaction UUID.")
    actor_user_id: UUID = Field(..., description="Actor user UUID.")
    warehouse_id: UUID | None = Field(default=None, description="Warehouse UUID.")
    receipt_id: UUID | None = Field(default=None, description="Receipt UUID.")
    provider_name: str = Field(..., description="Voice provider name.")
    stt_provider: str = Field(..., description="STT engine used.")
    tts_provider: str | None = Field(default=None, description="TTS engine configured.")
    language_code: str = Field(..., description="Language code.")
    transcript_text: str | None = Field(default=None, description="Transcribed speech text.")
    transcript_confidence: float | None = Field(default=None, description="Confidence score.")
    status: str = Field(..., description="Status: TRANSCRIBED, PARSED, FAILED, DISCARDED, APPLIED_TO_DRAFT.")
    created_at: datetime = Field(..., description="Creation timestamp.")


class VoiceInteractionListResponse(BaseModel):
    """Paginated list of voice interaction audit records."""

    model_config = ConfigDict(from_attributes=True)

    total: int = Field(..., description="Total matching interactions.")
    items: list[VoiceInteractionItemResponse] = Field(..., description="List of interaction items.")
