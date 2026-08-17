"""
--------------------------------------------------------------------------------
File        : core/services/ai/provider.py
Purpose     : Provide an SDK-isolated AI provider abstraction.

Responsibilities:
    - Hide concrete AI SDK details behind a small text-generation protocol.
    - Keep AI disabled by default unless runtime settings explicitly enable it.
    - Wrap provider failures in safe application exceptions.

Flow:
    Controller/service
        ->
    build_ai_provider(settings)
        ->
    AIProvider.generate_text(request)

Used By:
    - future read-only AI controllers and tools

Returns:
    AIProviderResponse - Provider-normalized text response.

Raises:
    AIProviderUnavailableError: When AI is disabled or the SDK is unavailable.
    AIProviderExecutionError: When a provider request fails.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import asyncio
from typing import Any, Protocol

from common.logger import get_logger
from core.services.ai.types import AIProviderRequest, AIProviderResponse

logger = get_logger(__name__)


class AIProviderUnavailableError(RuntimeError):
    """Raised when no AI provider is configured for the current environment."""


class AIProviderExecutionError(RuntimeError):
    """Raised when an AI provider request fails safely."""


class AIProvider(Protocol):
    """Protocol implemented by AI text-generation providers."""

    provider_name: str

    async def generate_text(self, request: AIProviderRequest) -> AIProviderResponse:
        """
        Generate provider text for an approved read-only request.

        Args:
            request: Provider-neutral generation request.

        Returns:
            AIProviderResponse: Normalized provider text response.

        Raises:
            AIProviderUnavailableError: If provider credentials or SDK are unavailable.
            AIProviderExecutionError: If the provider request fails.
        """


class DisabledAIProvider:
    """Provider implementation used when AI is intentionally disabled."""

    provider_name = "disabled"

    async def generate_text(self, request: AIProviderRequest) -> AIProviderResponse:
        """
        Reject generation because AI is disabled.

        Args:
            request: Provider-neutral generation request.

        Returns:
            AIProviderResponse: Never returned.

        Raises:
            AIProviderUnavailableError: Always raised for disabled providers.
        """
        raise AIProviderUnavailableError("AI provider is disabled.")


class GoogleGenAIProvider:
    """Google Gen AI provider wrapper using the official google-genai SDK."""

    provider_name = "google_genai"

    def __init__(self, *, api_key: str, default_model_name: str) -> None:
        """
        Initialize the Google Gen AI provider wrapper.

        Args:
            api_key: Google Gen AI API key supplied by backend secrets.
            default_model_name: Model used when a request omits a model name.

        Returns:
            None.

        Raises:
            AIProviderUnavailableError: If the API key is empty.
        """
        if not api_key.strip():
            raise AIProviderUnavailableError("Google Gen AI API key is not configured.")
        self._api_key = api_key
        self._default_model_name = default_model_name

    async def generate_text(self, request: AIProviderRequest) -> AIProviderResponse:
        """
        Generate text through Google Gen AI without leaking SDK details.

        The synchronous SDK call is executed in a worker thread so FastAPI's
        event loop remains available for other requests.

        Args:
            request: Provider-neutral generation request.

        Returns:
            AIProviderResponse: Normalized provider response.

        Raises:
            AIProviderUnavailableError: If the google-genai package is missing.
            AIProviderExecutionError: If Google generation fails.
        """
        try:
            response_text = await asyncio.to_thread(self._generate_text_sync, request)
        except ImportError as error:
            raise AIProviderUnavailableError(
                "google-genai is not installed. Install backend requirements."
            ) from error
        except Exception as error:
            logger.warning("Google Gen AI request failed: %s", error.__class__.__name__)
            raise AIProviderExecutionError("AI provider request failed.") from error

        model_name = request.model_name or self._default_model_name
        return AIProviderResponse(
            text=response_text,
            provider_name=self.provider_name,
            model_name=model_name,
            raw_metadata={},
        )

    def _generate_text_sync(self, request: AIProviderRequest) -> str:
        """
        Execute the blocking Google Gen AI SDK request with multi-model resilience.

        Args:
            request: Provider-neutral generation request.

        Returns:
            str: Generated response text.

        Raises:
            ImportError: If google-genai is unavailable.
            Exception: If all candidate models fail.
        """
        from google import genai

        client = genai.Client(api_key=self._api_key)
        candidate_models = [preferred_model, "gemini-2.5-flash"]
        # Deduplicate while preserving order
        unique_models = list(dict.fromkeys(candidate_models))

        config: dict[str, Any] = {}
        if request.system_instruction:
            config["system_instruction"] = request.system_instruction

        last_error: Exception | None = None
        for model in unique_models:
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=request.prompt,
                    config=config or None,
                )
                text = str(getattr(response, "text", "") or "").strip()
                if text:
                    return text
            except Exception as error:
                last_error = error
                logger.warning("Gemini model %s failed, attempting fallback: %s", model, error)

        if last_error:
            raise last_error
        return ""


def build_ai_provider(settings: Any) -> AIProvider:
    """
    Build the configured AI provider from runtime settings.

    AI remains disabled unless both ``AI_ENABLED=true`` and a supported provider
    name are configured. This keeps Release A safe by default.

    Args:
        settings: Application settings object.

    Returns:
        AIProvider: Configured provider or disabled provider.

    Raises:
        None.
    """
    if not getattr(settings, "ai_enabled", False):
        return DisabledAIProvider()

    provider_name = str(getattr(settings, "ai_provider", "disabled")).lower()
    if provider_name != "google_genai":
        return DisabledAIProvider()

    google_genai_api_key = str(getattr(settings, "google_genai_api_key", "")).strip()
    fallback_google_api_key = str(getattr(settings, "google_api_key", "")).strip()
    active_key = google_genai_api_key or fallback_google_api_key
    if not active_key:
        return DisabledAIProvider()

    return GoogleGenAIProvider(
        api_key=active_key,
        default_model_name=str(getattr(settings, "ai_model", "gemini-2.5-flash")),
    )
