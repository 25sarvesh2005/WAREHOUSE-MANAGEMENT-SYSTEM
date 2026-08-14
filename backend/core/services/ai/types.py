"""
--------------------------------------------------------------------------------
File        : core/services/ai/types.py
Purpose     : Define provider-neutral AI request and response value objects.

Responsibilities:
    - Keep AI provider inputs independent from a concrete SDK.
    - Return normalized text responses and safe metadata to callers.

Flow:
    Caller constructs AIProviderRequest
        ->
    AIProvider.generate_text()
        ->
    AIProviderResponse

Used By:
    - core/services/ai/provider.py

Returns:
    Dataclass instances for provider requests and responses.

Raises:
    None.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class AIProviderRequest:
    """Provider-neutral text generation request."""

    prompt: str
    model_name: str
    system_instruction: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AIProviderResponse:
    """Provider-neutral text generation response."""

    text: str
    provider_name: str
    model_name: str
    raw_metadata: dict[str, Any] = field(default_factory=dict)
