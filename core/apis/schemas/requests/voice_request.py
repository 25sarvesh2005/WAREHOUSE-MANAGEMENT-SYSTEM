"""
--------------------------------------------------------------------------------
File        : core/apis/schemas/requests/voice_request.py
Purpose     : Request schemas for voice-assisted receiving drafts and synthesis.

Responsibilities:
    - Validate transcript parsing payloads.
    - Validate text-to-speech synthesis requests.
    - Validate voice draft discard requests.

Flow:
    FastAPI Route
        ->
    Pydantic Request Validation
        ->
    Voice Controller

Used By:
    - core/apis/routes/voice_routes.py
    - core/controllers/voice_controller.py

Returns:
    Validated Pydantic models.

Raises:
    pydantic.ValidationError: On schema validation failure.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ParseReceivingTranscriptRequest(BaseModel):
    """Payload for parsing an existing text transcript into structured receiving lines."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    transcript: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Spoken text transcript to parse into receiving draft lines.",
        examples=["Received 12 available and 2 damaged note box crushed"],
    )
    warehouse_id: UUID | None = Field(
        default=None,
        description="Optional warehouse identifier scope.",
    )
    product_id: UUID | None = Field(
        default=None,
        description="Optional selected product ID from barcode scan/lookup.",
    )
    receipt_id: UUID | None = Field(
        default=None,
        description="Optional staged receipt ID.",
    )
    language_code: str = Field(
        default="en-IN",
        max_length=20,
        description="BCP-47 language tag.",
    )


class SynthesizeVoiceRequest(BaseModel):
    """Payload for requesting text-to-speech synthesis of a receiving summary."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    text: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Text script to read back to the operator.",
        examples=["Draft created with 12 available and 2 damaged units."],
    )
    language_code: str = Field(
        default="en-IN",
        max_length=20,
        description="Target BCP-47 language tag for TTS voice profile.",
    )


class DiscardVoiceDraftRequest(BaseModel):
    """Optional payload when discarding a voice-generated draft."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reason: str | None = Field(
        default=None,
        max_length=500,
        description="Optional operator reason for discarding the voice draft.",
    )
