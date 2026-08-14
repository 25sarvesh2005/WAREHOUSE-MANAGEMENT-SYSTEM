"""
--------------------------------------------------------------------------------
File        : core/services/voice/safety.py
Purpose     : Enforce strict read-only / draft-only safety rules for voice interactions.

Responsibilities:
    - Inspect speech transcripts for prohibited mutation or bypass commands.
    - Refuse commands attempting to finalize receipts, adjust stock, or dispatch shipments.
    - Prevent prompt injection and secret exfiltration over voice channels.
    - Return clear, non-punitive refusal decisions and safety metadata.

Flow:
    Voice Controller
        ->
    check_voice_receiving_safety(transcript)
        ->
    VoiceSafetyDecision(is_safe=True/False, refusal_reason=...)

Used By:
    - core/controllers/voice_controller.py
    - core/services/voice/transcript_parser.py

Returns:
    VoiceSafetyDecision - Safety evaluation outcome and refusal details.

Raises:
    None.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Final

# Prohibited action patterns
PROHIBITED_MUTATION_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(r"\b(complete|finalize|finish|submit)\s+(the\s+)?(receipt|order|shipment|transfer|return)\b", re.IGNORECASE),
    re.compile(r"\b(adjust|modify|override|delete|drop)\s+(the\s+)?(inventory|balance|stock|ledger)\b", re.IGNORECASE),
    re.compile(r"\b(ship|dispatch)\s+(the\s+)?(order|shipment|transfer)\b", re.IGNORECASE),
    re.compile(r"\b(approve|reject)\s+(the\s+)?(transfer|adjustment|return|order)\b", re.IGNORECASE),
    re.compile(r"\b(send\s+message|email|notify)\s+(the\s+)?(seller|customer)\b", re.IGNORECASE),
    re.compile(r"\b(bypass|skip|ignore|override)\s+(the\s+)?(scan|barcode|upc|verification)\b", re.IGNORECASE),
]

PROHIBITED_SECRET_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(r"\b(show|tell|reveal|give|export|print)\s+(me\s+)?(the\s+)?(api\s*key|jwt|secret|token|password|credential)\b", re.IGNORECASE),
    re.compile(r"\b(supabase|database|postgres)\s+(url|connection|password|secret)\b", re.IGNORECASE),
]

PROHIBITED_CROSS_TENANT_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(r"\b(switch|change|access|view)\s+(to\s+)?(other|different|all)\s+(seller|warehouse|tenant)\b", re.IGNORECASE),
]


@dataclass(frozen=True)
class VoiceSafetyDecision:
    """Outcome of safety evaluation for a voice transcript."""

    is_safe: bool
    refusal_code: str | None = None
    refusal_reason: str | None = None
    matched_pattern: str | None = None
    safety_flags: dict[str, object] = field(default_factory=dict)


def check_voice_receiving_safety(transcript: str) -> VoiceSafetyDecision:
    """
    Evaluate a transcript against warehouse voice safety boundaries.

    Args:
        transcript: Raw speech-to-text transcript.

    Returns:
        VoiceSafetyDecision: Safe approval or specific refusal explanation.

    Raises:
        None.
    """
    clean_text = transcript.strip()
    if not clean_text:
        return VoiceSafetyDecision(is_safe=True)

    # 1. Check prohibited mutation commands
    for pattern in PROHIBITED_MUTATION_PATTERNS:
        if match := pattern.search(clean_text):
            return VoiceSafetyDecision(
                is_safe=False,
                refusal_code="REFUSE_MUTATION",
                refusal_reason=(
                    "Voice AI is strictly draft-only. Autonomous receipt completion, "
                    "inventory adjustment, and transfer/shipment approval are blocked. "
                    "Please apply draft lines and complete through standard UI controls."
                ),
                matched_pattern=match.group(0),
                safety_flags={"category": "mutation_attempt", "matched": match.group(0)},
            )

    # 2. Check secret exfiltration attempts
    for pattern in PROHIBITED_SECRET_PATTERNS:
        if match := pattern.search(clean_text):
            return VoiceSafetyDecision(
                is_safe=False,
                refusal_code="REFUSE_SECRET",
                refusal_reason="System credentials, tokens, and secrets cannot be accessed via voice.",
                matched_pattern=match.group(0),
                safety_flags={"category": "secret_exfiltration", "matched": match.group(0)},
            )

    # 3. Check cross-tenant/cross-warehouse manipulation
    for pattern in PROHIBITED_CROSS_TENANT_PATTERNS:
        if match := pattern.search(clean_text):
            return VoiceSafetyDecision(
                is_safe=False,
                refusal_code="REFUSE_CROSS_TENANT",
                refusal_reason="Tenant and warehouse scope cannot be switched through voice commands.",
                matched_pattern=match.group(0),
                safety_flags={"category": "cross_tenant_attempt", "matched": match.group(0)},
            )

    return VoiceSafetyDecision(is_safe=True)
