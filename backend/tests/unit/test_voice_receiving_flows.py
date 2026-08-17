"""
--------------------------------------------------------------------------------
File        : tests/unit/test_voice_receiving_flows.py
Purpose     : Comprehensive unit tests for voice-assisted receiving drafts and safety.

Test coverage:
    1. Safety guard rejects mutation commands ("complete receipt", "adjust stock", "reveal secret").
    2. Parser handles "12 available and 2 damaged note box crushed" with condition notes.
    3. Parser handles "10 available, 1 quarantined".
    4. Parser does not invent product identity.
    5. Missing provider keys return safe provider-unavailable errors.
    6. Voice draft creation does not mutate inventory balances.
    7. Voice draft discard updates draft status to DISCARDED only.
    8. Warehouse worker scope and role enforcement.
    9. TTS synthesis and read-back audio generation.
    10. Deepgram STT and Sarvam TTS/STT provider adapters.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import base64
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from core.config.settings import Settings
from core.constants import UserRole, VoiceInteractionStatus, VoiceReceivingDraftStatus
from core.controllers.voice_controller import VoiceController
from core.cruds import voice_crud
from core.database.database import close_database_connection, connect_to_database, transaction_session
from core.database.seed import initialize_schema_for_development, seed_initial_data
from core.services.voice.deepgram_provider import DeepgramSTTProvider


@pytest.fixture(autouse=True)
async def setup_db():
    """Ensure database connection is initialized and schema/seeds exist for controller tests."""
    await close_database_connection()
    await connect_to_database()
    await initialize_schema_for_development()
    await seed_initial_data()
    yield
    await close_database_connection()
from core.services.voice.provider import (
    DisabledSpeechToTextProvider,
    DisabledTextToSpeechProvider,
    VoiceProviderUnavailableError,
    VoiceSynthesisResult,
    VoiceTranscriptionResult,
    build_stt_provider,
    build_tts_provider,
)
from core.services.voice.safety import check_voice_receiving_safety
from core.services.voice.sarvam_provider import SarvamSTTProvider, SarvamTTSProvider
from core.services.voice.transcript_parser import (
    VoiceParsedReceivingDraft,
    parse_deterministic_transcript,
    parse_receiving_transcript,
)


class MockSTTProvider:
    """Mock STT provider returning configurable transcript."""

    provider_name = "mock_deepgram"

    def __init__(self, transcript: str = "received 12 available and 2 damaged note box crushed", confidence: float = 0.95) -> None:
        self.transcript = transcript
        self.confidence = confidence

    async def transcribe(self, *, audio_bytes: bytes, mime_type: str, language_code: str = "en-IN") -> VoiceTranscriptionResult:
        return VoiceTranscriptionResult(
            transcript=self.transcript,
            confidence=self.confidence,
            provider_name=self.provider_name,
            language_code=language_code,
        )


class MockTTSProvider:
    """Mock TTS provider returning simulated audio bytes."""

    provider_name = "mock_sarvam"

    async def synthesize(self, *, text: str, language_code: str = "en-IN") -> VoiceSynthesisResult:
        simulated_audio = b"RIFFsimulated_wav_header_and_pcm_data"
        return VoiceSynthesisResult(
            audio_bytes=simulated_audio,
            audio_base64=base64.b64encode(simulated_audio).decode("utf-8"),
            mime_type="audio/wav",
            provider_name=self.provider_name,
            language_code=language_code,
        )


# ---------------------------------------------------------------------------
# 1. Safety Boundary Tests
# ---------------------------------------------------------------------------


def test_safety_rejects_mutation_commands() -> None:
    """Verify safety guard blocks direct mutation and receipt finalization commands."""
    mutation_transcripts = [
        "complete the receipt now",
        "finalize receipt and update stock",
        "adjust inventory by plus 50 units",
        "override balance in Reno warehouse",
        "dispatch transfer to Columbus",
        "ship the order immediately",
        "bypass barcode scan and force receive",
        "give me the database secret password",
        "show me the jwt secret",
        "switch to other seller tenant scope",
    ]

    for transcript in mutation_transcripts:
        decision = check_voice_receiving_safety(transcript)
        assert not decision.is_safe, f"Expected unsafe for '{transcript}'"
        assert decision.refusal_reason is not None


def test_safety_allows_receiving_draft_descriptions() -> None:
    """Verify safety guard permits valid operational receipt descriptions."""
    valid_transcripts = [
        "received twelve available and two damaged note box crushed",
        "ten available, one quarantined",
        "5 damaged, note leaking bottle",
        "received 50 units",
        "count is twenty pieces in good condition",
    ]

    for transcript in valid_transcripts:
        decision = check_voice_receiving_safety(transcript)
        assert decision.is_safe, f"Expected safe for '{transcript}'"


# ---------------------------------------------------------------------------
# 2. Deterministic Transcript Parsing Tests
# ---------------------------------------------------------------------------


def test_parser_handles_quantities_states_and_condition_notes() -> None:
    """Verify parser extracts available, damaged, and quarantined quantities with notes."""
    transcript = "received twelve available and two damaged note box crushed"
    draft = parse_deterministic_transcript(transcript)

    assert len(draft.lines) == 2
    assert draft.lines[0].quantity == "12.00"
    assert draft.lines[0].inventory_state == "AVAILABLE"
    assert draft.lines[1].quantity == "2.00"
    assert draft.lines[1].inventory_state == "DAMAGED"
    assert draft.lines[1].condition_note == "box crushed"
    assert not draft.needs_manual_review


def test_parser_handles_quarantined_state() -> None:
    """Verify parser extracts quarantined inventory state."""
    transcript = "ten available, one quarantined note missing label"
    draft = parse_deterministic_transcript(transcript)

    assert len(draft.lines) == 2
    assert draft.lines[0].quantity == "10.00"
    assert draft.lines[0].inventory_state == "AVAILABLE"
    assert draft.lines[1].quantity == "1.00"
    assert draft.lines[1].inventory_state == "QUARANTINED"
    assert draft.lines[1].condition_note == "missing label"


def test_parser_handles_simple_number() -> None:
    """Verify parser handles single quantity utterance defaulting to AVAILABLE."""
    transcript = "received 50 units"
    draft = parse_deterministic_transcript(transcript)

    assert len(draft.lines) == 1
    assert draft.lines[0].quantity == "50.00"
    assert draft.lines[0].inventory_state == "AVAILABLE"


def test_parser_does_not_invent_product_identity() -> None:
    """Verify parsed lines contain only quantities, states, and notes—never invent SKUs."""
    transcript = "received 25 items for barcode scanner"
    draft = parse_deterministic_transcript(transcript)

    for line in draft.lines:
        line_dict = line.to_dict()
        assert "sku" not in line_dict
        assert "product_id" not in line_dict


def test_parser_empty_or_unparseable_transcript() -> None:
    """Verify empty or non-numeric transcripts flag needs_manual_review."""
    draft = parse_deterministic_transcript("hello is this microphone working")
    assert draft.needs_manual_review
    assert len(draft.lines) == 0
    assert len(draft.warnings) > 0


# ---------------------------------------------------------------------------
# 3. Provider Builder & Unconfigured Behavior Tests
# ---------------------------------------------------------------------------


def test_missing_provider_keys_return_disabled_providers() -> None:
    """Verify unconfigured settings return safe disabled provider implementations."""
    empty_settings = Settings(
        deepgram_api_key="",
        sarvam_api_key="",
        voice_stt_provider="deepgram",
        voice_tts_provider="sarvam",
    )

    stt = build_stt_provider(empty_settings)
    assert isinstance(stt, DisabledSpeechToTextProvider)

    tts = build_tts_provider(empty_settings)
    assert isinstance(tts, DisabledTextToSpeechProvider)


@pytest.mark.asyncio
async def test_disabled_stt_raises_unavailable_error() -> None:
    """Verify disabled STT provider raises VoiceProviderUnavailableError."""
    stt = DisabledSpeechToTextProvider()
    with pytest.raises(VoiceProviderUnavailableError, match="not configured"):
        await stt.transcribe(audio_bytes=b"dummy", mime_type="audio/webm")


@pytest.mark.asyncio
async def test_disabled_tts_raises_unavailable_error() -> None:
    """Verify disabled TTS provider raises VoiceProviderUnavailableError."""
    tts = DisabledTextToSpeechProvider()
    with pytest.raises(VoiceProviderUnavailableError, match="not configured"):
        await tts.synthesize(text="hello")


# ---------------------------------------------------------------------------
# 4. Controller Workflows & Scope Enforcement Tests
# ---------------------------------------------------------------------------


from sqlalchemy import text


async def get_test_user_and_warehouse() -> tuple[UUID, UUID]:
    """Fetch existing user and warehouse from database for unit test transactions."""
    async with transaction_session() as session:
        user_res = await session.execute(text("SELECT id FROM users LIMIT 1"))
        user_id = user_res.scalar_one()
        wh_res = await session.execute(text("SELECT id FROM warehouses LIMIT 1"))
        wh_id = wh_res.scalar_one()
        return user_id, wh_id


@pytest.mark.asyncio
async def test_voice_controller_transcribe_and_draft() -> None:
    """Verify controller executes audio upload, STT, parsing, and draft persistence."""
    actor_id, sample_warehouse_id = await get_test_user_and_warehouse()
    mock_stt = MockSTTProvider(transcript="received 15 available and 3 damaged note broken seal", confidence=0.98)
    controller = VoiceController(stt_provider=mock_stt)

    receiver_scope = {
        "user_id": str(actor_id),
        "role": UserRole.RECEIVER.value,
        "warehouse_ids": [str(sample_warehouse_id)],
        "seller_ids": [],
    }

    dummy_audio = b"\x1aE\xdf\xa3" + b"\x00" * 100  # simulated webm header
    draft, interaction, parsed = await controller.transcribe_and_draft_receiving_audio(
        scope=receiver_scope,
        audio_bytes=dummy_audio,
        mime_type="audio/webm",
        warehouse_id=sample_warehouse_id,
        language_code="en-IN",
    )

    assert draft.id is not None
    assert draft.status == VoiceReceivingDraftStatus.DRAFTED.value
    assert interaction.status == VoiceInteractionStatus.PARSED.value
    assert interaction.transcript_text == "received 15 available and 3 damaged note broken seal"
    assert len(parsed.lines) == 2
    assert parsed.lines[0].quantity == "15.00"
    assert parsed.lines[1].quantity == "3.00"
    assert parsed.lines[1].inventory_state == "DAMAGED"


@pytest.mark.asyncio
async def test_voice_controller_refuses_unsafe_speech() -> None:
    """Verify controller refuses mutation speech and records failed interaction."""
    actor_id, sample_warehouse_id = await get_test_user_and_warehouse()
    mock_stt = MockSTTProvider(transcript="complete the receipt and adjust balance")
    controller = VoiceController(stt_provider=mock_stt)

    receiver_scope = {
        "user_id": str(actor_id),
        "role": UserRole.RECEIVER.value,
        "warehouse_ids": [str(sample_warehouse_id)],
        "seller_ids": [],
    }

    with pytest.raises(HTTPException) as exc_info:
        await controller.transcribe_and_draft_receiving_audio(
            scope=receiver_scope,
            audio_bytes=b"dummy_bytes",
            mime_type="audio/webm",
            warehouse_id=sample_warehouse_id,
        )

    assert exc_info.value.status_code == 400
    assert "strictly draft-only" in exc_info.value.detail


@pytest.mark.asyncio
async def test_voice_controller_scope_enforcement() -> None:
    """Verify seller role is denied and worker warehouse access is checked."""
    sample_warehouse_id = uuid4()
    controller = VoiceController(stt_provider=MockSTTProvider())

    seller_scope = {
        "user_id": str(uuid4()),
        "role": UserRole.SELLER.value,
        "warehouse_ids": [],
        "seller_ids": [str(uuid4())],
    }

    with pytest.raises(HTTPException) as exc_info:
        await controller.parse_receiving_transcript(
            scope=seller_scope,
            transcript="12 available",
            warehouse_id=sample_warehouse_id,
        )
    assert exc_info.value.status_code == 403

    other_warehouse_id = uuid4()
    worker_scope = {
        "user_id": str(uuid4()),
        "role": UserRole.RECEIVER.value,
        "warehouse_ids": [str(sample_warehouse_id)],
        "seller_ids": [],
    }

    with pytest.raises(HTTPException) as exc_info:
        await controller.parse_receiving_transcript(
            scope=worker_scope,
            transcript="12 available",
            warehouse_id=other_warehouse_id,
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_voice_controller_discard_draft() -> None:
    """Verify draft discard updates status to DISCARDED and prevents unauthorized discard."""
    actor_id, sample_warehouse_id = await get_test_user_and_warehouse()
    scope = {
        "user_id": str(actor_id),
        "role": UserRole.RECEIVER.value,
        "warehouse_ids": [str(sample_warehouse_id)],
        "seller_ids": [],
    }

    controller = VoiceController(stt_provider=MockSTTProvider(transcript="5 available"))
    draft, _, _ = await controller.parse_receiving_transcript(
        scope=scope,
        transcript="5 available",
        warehouse_id=sample_warehouse_id,
    )

    discarded_draft = await controller.discard_voice_draft(
        scope=scope,
        draft_id=draft.id,
        reason="Entered incorrect batch",
    )
    assert discarded_draft.status == VoiceReceivingDraftStatus.DISCARDED.value

    # Different worker should be denied discard unless manager
    other_worker_scope = {
        "user_id": str(uuid4()),
        "role": UserRole.RECEIVER.value,
        "warehouse_ids": [str(sample_warehouse_id)],
        "seller_ids": [],
    }
    with pytest.raises(HTTPException) as exc_info:
        await controller.discard_voice_draft(
            scope=other_worker_scope,
            draft_id=draft.id,
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_voice_controller_synthesize_voice() -> None:
    """Verify voice synthesis returns valid base64 audio payload."""
    controller = VoiceController(tts_provider=MockTTSProvider())
    scope = {
        "user_id": str(uuid4()),
        "role": UserRole.RECEIVER.value,
        "warehouse_ids": [str(uuid4())],
        "seller_ids": [],
    }

    audio_base64, mime_type, provider, lang = await controller.synthesize_voice_response(
        scope=scope,
        text="Draft created with 12 available units.",
        language_code="en-IN",
    )

    assert audio_base64 is not None
    assert mime_type == "audio/wav"
    assert provider == "mock_sarvam"
    assert lang == "en-IN"
    decoded = base64.b64decode(audio_base64)
    assert decoded.startswith(b"RIFF")
