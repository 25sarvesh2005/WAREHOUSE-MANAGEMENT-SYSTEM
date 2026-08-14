"""
--------------------------------------------------------------------------------
File        : core/services/voice/deepgram_provider.py
Purpose     : Implement speech-to-text transcription using Deepgram Nova REST API.

Responsibilities:
    - Transcribe audio clips via Deepgram REST API using httpx.
    - Extract normalized transcript and confidence score.
    - Never log raw audio bytes or API credentials.
    - Handle network errors and map HTTP status codes to domain exceptions.

Flow:
    Voice Controller / Services
        ->
    DeepgramSTTProvider.transcribe(audio_bytes, mime_type, language_code)
        ->
    POST https://api.deepgram.com/v1/listen
        ->
    VoiceTranscriptionResult

Used By:
    - core/services/voice/provider.py

Returns:
    VoiceTranscriptionResult - Normalized transcript and confidence.

Raises:
    VoiceProviderUnavailableError: If API key is empty or invalid.
    VoiceTranscriptionError: If Deepgram API request fails.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from typing import Any

import httpx

from common.logger import get_logger
from core.services.voice.provider import (
    SpeechToTextProvider,
    VoiceProviderUnavailableError,
    VoiceTranscriptionError,
    VoiceTranscriptionResult,
)

logger = get_logger(__name__)

DEEPGRAM_API_URL = "https://api.deepgram.com/v1/listen"


class DeepgramSTTProvider(SpeechToTextProvider):
    """Deepgram speech-to-text adapter using the official REST listen endpoint."""

    provider_name = "deepgram"

    def __init__(self, *, api_key: str, default_model: str = "nova-3") -> None:
        """
        Initialize the Deepgram STT provider adapter.

        Args:
            api_key: Deepgram API token.
            default_model: Deepgram model identifier (defaults to nova-3).

        Returns:
            None.

        Raises:
            VoiceProviderUnavailableError: If api_key is empty.
        """
        if not api_key.strip():
            raise VoiceProviderUnavailableError("Deepgram API key is not configured.")
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
        Transcribe audio payload via Deepgram REST API.

        Args:
            audio_bytes: Binary audio bytes.
            mime_type: Audio MIME type (e.g. audio/webm, audio/wav).
            language_code: Target BCP-47 language tag (e.g. en-IN, en-US).

        Returns:
            VoiceTranscriptionResult: Extracted transcript and confidence.

        Raises:
            VoiceProviderUnavailableError: On authentication rejection.
            VoiceTranscriptionError: On network or parsing failures.
        """
        if not audio_bytes:
            raise VoiceTranscriptionError("Audio payload is empty.")

        # Normalize language tag for Deepgram (e.g., en-IN or en)
        lang = language_code.split("-")[0] if language_code not in {"en-IN", "en-US", "en-GB"} else language_code

        headers = {
            "Authorization": f"Token {self._api_key}",
            "Content-Type": mime_type or "audio/webm",
        }
        params: dict[str, str | bool] = {
            "model": self._default_model,
            "smart_format": "true",
            "punctuate": "true",
            "language": lang,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    DEEPGRAM_API_URL,
                    params=params,
                    headers=headers,
                    content=audio_bytes,
                )
        except httpx.TimeoutException as exc:
            logger.warning("Deepgram API request timed out.")
            raise VoiceTranscriptionError("Voice transcription service timed out.") from exc
        except Exception as exc:
            logger.warning("Deepgram API connection error: %s", exc.__class__.__name__)
            raise VoiceTranscriptionError("Could not connect to voice transcription service.") from exc

        if response.status_code in {401, 403}:
            logger.error("Deepgram authentication failed with status %s", response.status_code)
            raise VoiceProviderUnavailableError("Deepgram authentication failed. Verify API key.")

        if response.status_code != 200:
            logger.warning("Deepgram API returned HTTP %s: %s", response.status_code, response.text[:200])
            raise VoiceTranscriptionError(f"Deepgram transcription failed with status {response.status_code}.")

        try:
            data: dict[str, Any] = response.json()
            channels = data.get("results", {}).get("channels", [])
            if not channels:
                return VoiceTranscriptionResult(
                    transcript="",
                    confidence=0.0,
                    provider_name=self.provider_name,
                    language_code=language_code,
                )

            alt = channels[0].get("alternatives", [{}])[0]
            transcript = str(alt.get("transcript", "") or "").strip()
            confidence = float(alt.get("confidence", 0.0) or 0.0)

            return VoiceTranscriptionResult(
                transcript=transcript,
                confidence=confidence,
                provider_name=self.provider_name,
                language_code=language_code,
                raw_metadata={"model": self._default_model},
            )
        except Exception as exc:
            logger.error("Failed to parse Deepgram response JSON: %s", exc)
            raise VoiceTranscriptionError("Failed to parse transcription service response.") from exc
