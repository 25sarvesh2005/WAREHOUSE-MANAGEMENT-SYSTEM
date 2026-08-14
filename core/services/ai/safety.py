"""
--------------------------------------------------------------------------------
File        : core/services/ai/safety.py
Purpose     : Enforce read-only AI safety guardrails.

Responsibilities:
    - Refuse mutation, seller-communication, secret-disclosure, and cross-tenant prompts.
    - Allow only approved read-only AI application tool names.
    - Hash raw prompts and redact excerpts before audit persistence.

Flow:
    User prompt or tool request
        ->
    AISafetyGuard evaluation
        ->
    allow read-only response or refuse safely

Used By:
    - future read-only AI controllers and tools
    - tests/unit/test_ai_foundation.py

Returns:
    AISafetyEvaluation - Safety decision and optional reason.

Raises:
    AISafetyViolationError: When a requested tool is not read-only approved.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Final

from core.constants import AISafetyDecision

READ_ONLY_TOOL_NAMES: Final[frozenset[str]] = frozenset(
    {
        "inventory_lookup",
        "ledger_explanation",
        "order_status",
        "receipt_status",
        "transfer_status",
        "shipment_status",
        "return_status",
        "exception_summary",
        "draft_recommendation",
    }
)

MUTATION_PATTERNS: Final[tuple[re.Pattern[str], ...]] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b(create|place|submit)\s+(an?\s+)?order\b",
        r"\b(cancel|delete|void|close)\s+(an?\s+)?(order|receipt|transfer|return|shipment)\b",
        r"\b(approve|reject|apply)\s+(an?\s+)?(migration|transfer|return|adjustment)\b",
        r"\b(adjust|change|modify|update|set|fix)\s+(stock|inventory|quantity|balance)\b",
        r"\b(reserve|release|ship|dispatch|receive|inspect|dispose|restock)\b",
        r"\b(send|email|notify|message)\s+(the\s+)?seller\b",
        r"\bwrite\s+(to\s+)?(postgres|database|db)\b",
        r"\brun\s+(sql|migration|delete|update|insert)\b",
    )
)

SECRET_PATTERNS: Final[tuple[re.Pattern[str], ...]] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bservice[_-]?role\b",
        r"\bdatabase_url\b",
        r"\bmigration_database_url\b",
        r"\bjwt_secret\b",
        r"\bgoogle[_-]?(api|genai)[_-]?key\b",
        r"\bapi[_-]?secret\b",
        r"\bpassword\b",
        r"\bbearer\s+[a-z0-9._~+/=-]{12,}",
        r"\bpostgresql(?:\+\w+)?://\S+",
    )
)

CROSS_TENANT_PATTERNS: Final[tuple[re.Pattern[str], ...]] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\ball\s+sellers\b",
        r"\bevery\s+seller\b",
        r"\bother\s+sellers?\b",
        r"\banother\s+seller\b",
        r"\bcross[-\s]?tenant\b",
        r"\bignore\s+(seller|warehouse)\s+scope\b",
    )
)

UNSUPPORTED_PATTERNS: Final[tuple[re.Pattern[str], ...]] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bforecast\b",
        r"\boptimi[sz]e\s+(staffing|labor|pricing)\b",
        r"\blegal\s+advice\b",
        r"\bmedical\s+advice\b",
        r"\bfinancial\s+advice\b",
    )
)

REDACTION_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"postgresql(?:\+\w+)?://\S+", re.IGNORECASE),
    re.compile(r"bearer\s+[a-z0-9._~+/=-]{12,}", re.IGNORECASE),
    re.compile(
        r"(service[_-]?role|database_url|migration_database_url|jwt_secret|"
        r"google[_-]?(api|genai)[_-]?key|api[_-]?secret|password)\s*[=:]\s*\S+",
        re.IGNORECASE,
    ),
)


class AISafetyViolationError(RuntimeError):
    """Raised when a requested AI action violates read-only guardrails."""


@dataclass(frozen=True, slots=True)
class AISafetyEvaluation:
    """Result of evaluating an AI prompt or tool request."""

    decision: AISafetyDecision
    allowed: bool
    reason: str | None = None


def hash_sensitive_text(value: str) -> str:
    """
    Hash prompt, tool input, or draft payload text for audit correlation.

    Args:
        value: Raw sensitive text to hash.

    Returns:
        str: SHA-256 hexadecimal digest.

    Raises:
        None.
    """
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def make_safe_excerpt(value: str, *, max_chars: int) -> str:
    """
    Create a redacted and length-limited text excerpt for audit records.

    Args:
        value: Raw text that may contain secrets.
        max_chars: Maximum number of characters to keep.

    Returns:
        str: Redacted excerpt safe for operational audit storage.

    Raises:
        None.
    """
    cleaned_value = " ".join(value.split())
    for pattern in REDACTION_PATTERNS:
        cleaned_value = pattern.sub("[REDACTED]", cleaned_value)
    if len(cleaned_value) <= max_chars:
        return cleaned_value
    return f"{cleaned_value[: max(0, max_chars - 3)]}..."


class AISafetyGuard:
    """Warehouse-specific guard that allows only read-only AI behavior."""

    def evaluate_prompt(self, prompt: str) -> AISafetyEvaluation:
        """
        Evaluate whether a prompt is safe for Release A read-only handling.

        Args:
            prompt: User prompt submitted to the AI assistant.

        Returns:
            AISafetyEvaluation: Allow/refuse decision and safe reason.

        Raises:
            None.
        """
        if self._matches_any(prompt, SECRET_PATTERNS):
            return AISafetyEvaluation(
                decision=AISafetyDecision.REFUSE_SECRET,
                allowed=False,
                reason="The request asks for or includes sensitive secret material.",
            )
        if self._matches_any(prompt, CROSS_TENANT_PATTERNS):
            return AISafetyEvaluation(
                decision=AISafetyDecision.REFUSE_CROSS_TENANT,
                allowed=False,
                reason="The request appears to bypass seller or warehouse scope.",
            )
        if self._matches_any(prompt, MUTATION_PATTERNS):
            return AISafetyEvaluation(
                decision=AISafetyDecision.REFUSE_MUTATION,
                allowed=False,
                reason="AI Release A is read-only and cannot mutate operations.",
            )
        if self._matches_any(prompt, UNSUPPORTED_PATTERNS):
            return AISafetyEvaluation(
                decision=AISafetyDecision.REFUSE_UNSUPPORTED,
                allowed=False,
                reason="The request is outside the approved warehouse AI scope.",
            )
        return AISafetyEvaluation(
            decision=AISafetyDecision.ALLOW_READ_ONLY,
            allowed=True,
            reason=None,
        )

    def ensure_read_only_tool(self, tool_name: str) -> None:
        """
        Require an AI tool name to be explicitly approved as read-only.

        Args:
            tool_name: Application tool name requested by AI orchestration.

        Returns:
            None.

        Raises:
            AISafetyViolationError: If the tool is not in the approved read-only list.
        """
        if tool_name not in READ_ONLY_TOOL_NAMES:
            raise AISafetyViolationError(
                f"AI tool '{tool_name}' is not approved for Release A read-only use."
            )

    def _matches_any(self, value: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
        """
        Return whether text matches at least one compiled pattern.

        Args:
            value: Text to inspect.
            patterns: Compiled regular expressions.

        Returns:
            bool: True when any pattern matches.

        Raises:
            None.
        """
        return any(pattern.search(value) for pattern in patterns)
