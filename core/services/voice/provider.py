"""
--------------------------------------------------------------------------------
File        : core/services/voice/provider.py
Purpose     : Define abstract voice provider protocols, domain results, and exceptions.

Responsibilities:
    - Define SpeechToTextProvider and TextToSpeechProvider protocols.
    - Encapsulate transcription and synthesis data transfer objects.
    - Provide domain exceptions that decouple provider implementations from HTTP layer.
    - Provide factory builders for configured STT and TTS providers.

Flow:
    Voice Controller / Services
        ->
    build_stt_provider(settings) / build_tts_provider(settings)
        ->
    Provider.transcribe(...) / Provider.synthesize(...)

Used By:
    - core/services/voice/deepgram_provider.py
    - core/services/voice/sarvam_provider.py
    - core/controllers/voice_controller.py

Returns:
    VoiceTranscriptionResult, VoiceSynthesisResult - Standardized voice results.

Raises:
    VoiceProviderUnavailableError: When keys or provider services are unconfigured.
    VoiceTranscriptionError: When audio transcription fails safely.
    VoiceSynthesisError: When speech synthesis fails safely.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from common.logger import get_logger

logger = get_logger(__name__)


class VoiceProviderError(RuntimeError):
    """Base domain exception for voice subsystem failures."""


class VoiceProviderUnavailableError(VoiceProviderError):
    """Raised when the requested voice provider is unconfigured or disabled."""


class VoiceTranscriptionError(VoiceProviderError):
    """Raised when audio transcription fails safely."""


class VoiceSynthesisError(VoiceProviderError):
    """Raised when speech synthesis fails safely."""


@dataclass(frozen=True)
class VoiceTranscriptionResult:
    """Standardized result returned by speech-to-text providers."""

    transcript: str
    confidence: float | None = None
    provider_name: str = ""
    language_code: str = "en-IN"
    raw_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VoiceSynthesisResult:
    """Standardized result returned by text-to-speech providers."""

    audio_bytes: bytes
    audio_base64: str
    mime_type: str = "audio/wav"
    provider_name: str = ""
    language_code: str = "en-IN"


class SpeechToTextProvider(Protocol):
    """Protocol implemented by speech-to-text provider adapters."""

    provider_name: str

    async def transcribe(
        self,
        *,
        audio_bytes: bytes,
        mime_type: str,
        language_code: str = "en-IN",
    ) -> VoiceTranscriptionResult:
        """
        Transcribe raw audio bytes into text.

        Args:
            audio_bytes: Binary audio payload.
            mime_type: Audio MIME type (e.g. audio/webm, audio/wav).
            language_code: Target BCP-47 language tag.

        Returns:
            VoiceTranscriptionResult: Normalized transcript and confidence.

        Raises:
            VoiceProviderUnavailableError: If provider is unconfigured.
            VoiceTranscriptionError: If transcription fails.
        """
        ...


class TextToSpeechProvider(Protocol):
    """Protocol implemented by text-to-speech provider adapters."""

    provider_name: str

    async def synthesize(
        self,
        *,
        text: str,
        language_code: str = "en-IN",
    ) -> VoiceSynthesisResult:
        """
        Synthesize text into speech audio.

        Args:
            text: Plain text to synthesize.
            language_code: Target language code.

        Returns:
            VoiceSynthesisResult: Binary/base64 audio result and MIME type.

        Raises:
            VoiceProviderUnavailableError: If provider is unconfigured.
            VoiceSynthesisError: If synthesis fails.
        """
        ...


class DisabledSpeechToTextProvider:
    """Fallback provider when STT is disabled or unconfigured."""

    provider_name = "disabled"

    async def transcribe(
        self,
        *,
        audio_bytes: bytes,
        mime_type: str,
        language_code: str = "en-IN",
    ) -> VoiceTranscriptionResult:
        """
        Raise provider unavailable error.

        Raises:
            VoiceProviderUnavailableError: Always raised.
        """
        raise VoiceProviderUnavailableError(
            "Speech-to-text provider is not configured. Manual entry is available."
        )


class DisabledTextToSpeechProvider:
    """Fallback provider when TTS is disabled or unconfigured."""

    provider_name = "disabled"

    async def synthesize(
        self,
        *,
        text: str,
        language_code: str = "en-IN",
    ) -> VoiceSynthesisResult:
        """
        Raise provider unavailable error.

        Raises:
            VoiceProviderUnavailableError: Always raised.
        """
        raise VoiceProviderUnavailableError(
            "Text-to-speech provider is not configured."
        )


def build_stt_provider(settings: Any) -> SpeechToTextProvider:
    """
    Build the configured Speech-to-Text provider from application settings.

    Args:
        settings: Application runtime settings.

    Returns:
        SpeechToTextProvider: Deepgram, Sarvam, or Disabled STT provider.

    Raises:
        None.
    """
    from core.services.voice.deepgram_provider import DeepgramSTTProvider
    from core.services.voice.sarvam_provider import SarvamSTTProvider

    provider_choice = str(
        getattr(settings, "voice_stt_provider", "deepgram")
    ).lower().strip()
    deepgram_key = str(getattr(settings, "deepgram_api_key", "")).strip()
    sarvam_key = str(getattr(settings, "sarvam_api_key", "")).strip()

    if provider_choice == "deepgram":
        if deepgram_key:
            return DeepgramSTTProvider(api_key=deepgram_key)
        if sarvam_key:
            logger.info("Deepgram key missing; falling back to Sarvam STT.")
            return SarvamSTTProvider(api_key=sarvam_key)
        return DisabledSpeechToTextProvider()

    if provider_choice == "sarvam":
        if sarvam_key:
            return SarvamSTTProvider(api_key=sarvam_key)
        if deepgram_key:
            logger.info("Sarvam key missing; falling back to Deepgram STT.")
            return DeepgramSTTProvider(api_key=deepgram_key)
        return DisabledSpeechToTextProvider()

    return DisabledSpeechToTextProvider()


def build_tts_provider(settings: Any) -> TextToSpeechProvider:
    """
    Build the configured Text-to-Speech provider from application settings.

    Args:
        settings: Application runtime settings.

    Returns:
        TextToSpeechProvider: Sarvam or Disabled TTS provider.

    Raises:
        None.
    """
    from core.services.voice.sarvam_provider import SarvamTTSProvider

    provider_choice = str(
        getattr(settings, "voice_tts_provider", "sarvam")
    ).lower().strip()
    sarvam_key = str(getattr(settings, "sarvam_api_key", "")).strip()

    if provider_choice == "sarvam" and sarvam_key:
        return SarvamTTSProvider(api_key=sarvam_key)

    return DisabledTextToSpeechProvider()
