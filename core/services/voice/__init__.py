"""Voice assistant services supporting voice-assisted receiving drafts."""

from core.services.voice.provider import (
    SpeechToTextProvider,
    TextToSpeechProvider,
    VoiceProviderError,
    VoiceProviderUnavailableError,
    VoiceSynthesisError,
    VoiceSynthesisResult,
    VoiceTranscriptionError,
    VoiceTranscriptionResult,
    build_stt_provider,
    build_tts_provider,
)
from core.services.voice.safety import VoiceSafetyDecision, check_voice_receiving_safety
from core.services.voice.transcript_parser import (
    VoiceParsedLine,
    VoiceParsedReceivingDraft,
    parse_deterministic_transcript,
    parse_receiving_transcript,
)

__all__ = [
    "SpeechToTextProvider",
    "TextToSpeechProvider",
    "VoiceProviderError",
    "VoiceProviderUnavailableError",
    "VoiceSynthesisError",
    "VoiceSynthesisResult",
    "VoiceTranscriptionError",
    "VoiceTranscriptionResult",
    "build_stt_provider",
    "build_tts_provider",
    "VoiceSafetyDecision",
    "check_voice_receiving_safety",
    "VoiceParsedLine",
    "VoiceParsedReceivingDraft",
    "parse_deterministic_transcript",
    "parse_receiving_transcript",
]
