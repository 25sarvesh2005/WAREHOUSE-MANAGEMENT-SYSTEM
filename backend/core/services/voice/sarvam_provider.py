"""
--------------------------------------------------------------------------------
File        : core/services/voice/sarvam_provider.py
Purpose     : Implement Sarvam AI Text-to-Speech (Bulbul) and Speech-to-Text (Saaras).

Responsibilities:
    - Synthesize read-back audio summaries using Sarvam Bulbul REST API.
    - Provide fallback STT transcription using Sarvam Saaras REST API.
    - Never log raw audio or subscription keys.
    - Safely convert API responses and errors into domain exceptions.

Flow:
    Voice Controller / Services
        ->
    SarvamTTSProvider.synthesize(text, language_code) / SarvamSTTProvider.transcribe(...)
        ->
    POST https://api.sarvam.ai/text-to-speech / https://api.sarvam.ai/speech-to-text
        ->
    VoiceSynthesisResult / VoiceTranscriptionResult

Used By:
    - core/services/voice/provider.py

Returns:
    VoiceSynthesisResult / VoiceTranscriptionResult - Standardized voice results.

Raises:
    VoiceProviderUnavailableError: If subscription key is unconfigured or rejected.
    VoiceSynthesisError: If speech synthesis fails.
    VoiceTranscriptionError: If STT transcription fails.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import base64
from typing import Any

import httpx

from common.logger import get_logger
from core.services.voice.provider import (
    SpeechToTextProvider,
    TextToSpeechProvider,
    VoiceProviderUnavailableError,
    VoiceSynthesisError,
    VoiceSynthesisResult,
    VoiceTranscriptionError,
    VoiceTranscriptionResult,
)

logger = get_logger(__name__)

SARVAM_TTS_API_URL = "https://api.sarvam.ai/text-to-speech"
SARVAM_STT_API_URL = "https://api.sarvam.ai/speech-to-text"


class SarvamTTSProvider(TextToSpeechProvider):
    """Sarvam AI Bulbul Text-to-Speech adapter."""

    provider_name = "sarvam"

    def __init__(
        self,
        *,
        api_key: str,
        speaker: str = "shubh",
        default_model: str = "bulbul:v3",
    ) -> None:
        """
        Initialize the Sarvam TTS provider.

        Args:
            api_key: Sarvam AI subscription key.
            speaker: Voice profile name (defaults to shubh for Bulbul v3).
            default_model: Model name (defaults to bulbul:v3).

        Returns:
            None.

        Raises:
            VoiceProviderUnavailableError: If api_key is empty.
        """
        if not api_key.strip():
            raise VoiceProviderUnavailableError("Sarvam API key is not configured.")
        self._api_key = api_key.strip()
        self._speaker = speaker
        self._default_model = default_model

    async def synthesize(
        self,
        *,
        text: str,
        language_code: str = "en-IN",
    ) -> VoiceSynthesisResult:
        """
        Synthesize text into speech audio bytes and base64 string.

        Args:
            text: Plain text script to read back (truncated to 500 chars).
            language_code: Target BCP-47 language tag (e.g. en-IN, hi-IN).

        Returns:
            VoiceSynthesisResult: Audio bytes, base64 payload, and MIME type.

        Raises:
            VoiceProviderUnavailableError: On authentication error.
            VoiceSynthesisError: On synthesis request failure.
        """
        clean_text = text.strip()[:500]
        if not clean_text:
            raise VoiceSynthesisError("Text to synthesize is empty.")

        # Map language code to Sarvam supported codes (e.g., en-IN, hi-IN)
        target_lang = language_code if "-" in language_code else f"{language_code}-IN"

        headers = {
            "api-subscription-key": self._api_key,
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "inputs": [clean_text],
            "target_language_code": target_lang,
            "speaker": self._speaker,
            "pace": 1.0,
            "speech_sample_rate": 24000,
            "model": self._default_model,
            "output_audio_codec": "wav",
        }
        if self._default_model == "bulbul:v3":
            payload["temperature"] = 0.6
        else:
            payload["pitch"] = 0
            payload["loudness"] = 1.0
            payload["enable_preprocessing"] = True

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    SARVAM_TTS_API_URL,
                    headers=headers,
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            logger.warning("Sarvam TTS request timed out.")
            raise VoiceSynthesisError("Voice synthesis service timed out.") from exc
        except Exception as exc:
            logger.warning("Sarvam TTS connection error: %s", exc.__class__.__name__)
            raise VoiceSynthesisError("Could not connect to voice synthesis service.") from exc

        if response.status_code in {401, 403}:
            logger.error("Sarvam authentication failed with status %s", response.status_code)
            raise VoiceProviderUnavailableError("Sarvam authentication failed. Verify API key.")

        if response.status_code != 200:
            logger.warning("Sarvam TTS returned HTTP %s: %s", response.status_code, response.text[:200])
            raise VoiceSynthesisError(f"Sarvam synthesis failed with status {response.status_code}.")

        try:
            data: dict[str, Any] = response.json()
            audios = data.get("audios", [])
            if not audios or not audios[0]:
                raise VoiceSynthesisError("Sarvam returned empty audio data.")

            audio_base64 = str(audios[0])
            audio_bytes = base64.b64decode(audio_base64)

            return VoiceSynthesisResult(
                audio_bytes=audio_bytes,
                audio_base64=audio_base64,
                mime_type="audio/wav",
                provider_name=self.provider_name,
                language_code=target_lang,
            )
        except Exception as exc:
            logger.error("Failed to parse Sarvam TTS response JSON: %s", exc)
            raise VoiceSynthesisError("Failed to parse voice synthesis response.") from exc


class SarvamSTTProvider(SpeechToTextProvider):
    """Sarvam AI Saaras Speech-to-Text adapter."""

    provider_name = "sarvam"

    def __init__(
        self,
        *,
        api_key: str,
        default_model: str = "saaras:v4",
    ) -> None:
        """
        Initialize the Sarvam STT provider.

        Args:
            api_key: Sarvam AI subscription key.
            default_model: Model name (defaults to saaras:v4).

        Returns:
            None.

        Raises:
            VoiceProviderUnavailableError: If api_key is empty.
        """
        if not api_key.strip():
            raise VoiceProviderUnavailableError("Sarvam API key is not configured.")
        self._api_key = api_key.strip()
        self._default_model = default_model

    async def transcribe(
        self,
        *,
        audio_bytes: bytes,
        mime_type: str,
        language_code: str = "en-IN",
    ) -> VoiceTranscriptionResult:
        """
        Transcribe audio payload via Sarvam Saaras STT endpoint.

        Args:
            audio_bytes: Binary audio bytes.
            mime_type: Audio MIME type.
            language_code: Target BCP-47 language tag (e.g. en-IN).

        Returns:
            VoiceTranscriptionResult: Extracted transcript and confidence.

        Raises:
            VoiceProviderUnavailableError: On authentication error.
            VoiceTranscriptionError: On STT request failure.
        """
        if not audio_bytes:
            raise VoiceTranscriptionError("Audio payload is empty.")

        target_lang = language_code if "-" in language_code else f"{language_code}-IN"
        headers = {"api-subscription-key": self._api_key}

        # Filename extension mapping
        ext = "wav" if "wav" in mime_type else "webm" if "webm" in mime_type else "mp4"
        files = {
            "file": (f"audio.{ext}", audio_bytes, mime_type or "audio/wav"),
        }
        data = {
            "model": self._default_model,
            "language_code": target_lang,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    SARVAM_STT_API_URL,
                    headers=headers,
                    data=data,
                    files=files,
                )
        except httpx.TimeoutException as exc:
            logger.warning("Sarvam STT request timed out.")
            raise VoiceTranscriptionError("Voice transcription service timed out.") from exc
        except Exception as exc:
            logger.warning("Sarvam STT connection error: %s", exc.__class__.__name__)
            raise VoiceTranscriptionError("Could not connect to voice transcription service.") from exc

        if response.status_code in {401, 403}:
            logger.error("Sarvam STT authentication failed with status %s", response.status_code)
            raise VoiceProviderUnavailableError("Sarvam authentication failed. Verify API key.")

        if response.status_code != 200:
            logger.warning("Sarvam STT returned HTTP %s: %s", response.status_code, response.text[:200])
            raise VoiceTranscriptionError(f"Sarvam transcription failed with status {response.status_code}.")

        try:
            res_data: dict[str, Any] = response.json()
            transcript = str(res_data.get("transcript", "") or "").strip()
            return VoiceTranscriptionResult(
                transcript=transcript,
                confidence=0.85,
                provider_name=self.provider_name,
                language_code=target_lang,
                raw_metadata={"model": self._default_model},
            )
        except Exception as exc:
            logger.error("Failed to parse Sarvam STT response JSON: %s", exc)
            raise VoiceTranscriptionError("Failed to parse transcription response.") from exc
