"""
--------------------------------------------------------------------------------
File        : core/services/voice/transcript_parser.py
Purpose     : Parse spoken receiving transcripts into structured receiving draft lines.

Responsibilities:
    - Extract quantities, inventory states (AVAILABLE, DAMAGED, QUARANTINED), and notes.
    - Leverage Gemini LLM provider when configured for complex conversational utterances.
    - Provide a robust, deterministic rule-based fallback parser for high-reliability offline/no-key usage.
    - Guarantee product identity is NOT invented from speech; only operational quantities/states are drafted.

Flow:
    Voice Controller
        ->
    parse_receiving_transcript(transcript, context, ai_provider)
        ->
    VoiceParsedReceivingDraft

Used By:
    - core/controllers/voice_controller.py

Returns:
    VoiceParsedReceivingDraft - Structured draft lines and condition notes.

Raises:
    None.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

from common.logger import get_logger
from core.services.ai.provider import AIProvider, DisabledAIProvider
from core.services.ai.types import AIProviderRequest

logger = get_logger(__name__)

# Word-to-number dictionary for spoken numerals
NUMBER_WORDS: dict[str, str] = {
    "zero": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
    "eleven": "11",
    "twelve": "12",
    "thirteen": "13",
    "fourteen": "14",
    "fifteen": "15",
    "sixteen": "16",
    "seventeen": "17",
    "eighteen": "18",
    "nineteen": "19",
    "twenty": "20",
    "thirty": "30",
    "forty": "40",
    "fifty": "50",
    "sixty": "60",
    "seventy": "70",
    "eighty": "80",
    "ninety": "90",
    "hundred": "100",
}


@dataclass
class VoiceParsedLine:
    """Individual receiving draft line parsed from voice transcript."""

    quantity: str
    inventory_state: str = "AVAILABLE"  # AVAILABLE, DAMAGED, QUARANTINED
    condition_note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert line to dictionary."""
        return {
            "quantity": self.quantity,
            "inventory_state": self.inventory_state,
            "condition_note": self.condition_note,
        }


@dataclass
class VoiceParsedReceivingDraft:
    """Complete receiving draft parsed from speech transcript."""

    lines: list[VoiceParsedLine] = field(default_factory=list)
    general_notes: str | None = None
    needs_manual_review: bool = False
    warnings: list[str] = field(default_factory=list)
    raw_transcript: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert draft to dictionary."""
        return {
            "lines": [line.to_dict() for line in self.lines],
            "general_notes": self.general_notes,
            "needs_manual_review": self.needs_manual_review,
            "warnings": self.warnings,
            "raw_transcript": self.raw_transcript,
        }


def _replace_number_words(text: str) -> str:
    """Replace spoken English number words with numeric digits."""
    tokens = text.split()
    converted_tokens = []
    for token in tokens:
        clean_token = token.lower().strip(",.;:!?")
        if clean_token in NUMBER_WORDS:
            converted_tokens.append(NUMBER_WORDS[clean_token])
        else:
            converted_tokens.append(token)
    return " ".join(converted_tokens)


def _format_quantity(qty_str: str) -> str:
    """Format quantity to 2 decimal places string."""
    try:
        val = Decimal(qty_str)
        if val <= 0:
            return "1.00"
        return f"{val:.2f}"
    except (InvalidOperation, ValueError):
        return "1.00"


def parse_deterministic_transcript(transcript: str) -> VoiceParsedReceivingDraft:
    """
    Parse a speech transcript deterministically using regex and grammar heuristics.

    Handles phrases such as:
      - "received twelve available and two damaged note box crushed"
      - "ten available, one quarantined"
      - "5 damaged, note leaking bottle"
      - "received 50 units"

    Args:
        transcript: Raw speech-to-text transcript.

    Returns:
        VoiceParsedReceivingDraft: Structured lines and condition notes.

    Raises:
        None.
    """
    normalized_text = _replace_number_words(transcript.strip())
    if not normalized_text:
        return VoiceParsedReceivingDraft(
            lines=[],
            needs_manual_review=True,
            warnings=["Transcript was empty. Please enter receiving quantities manually."],
            raw_transcript=transcript,
        )

    lines: list[VoiceParsedLine] = []
    warnings: list[str] = []
    general_notes: str | None = None

    # Check for general condition notes in transcript
    note_match = re.search(r"\bnote\b[:\s]+(.+)", normalized_text, re.IGNORECASE)
    extracted_note = note_match.group(1).strip() if note_match else None

    # Pattern: Match <number> followed by state keywords (available, good, damaged, broken, quarantine, etc.)
    # Example: "12 available", "2 damaged", "1 quarantined"
    clause_pattern = re.compile(
        r"(\d+(?:\.\d+)?)\s*(?:units?|pieces?|boxes?|items?|qty)?\s*"
        r"(available|good|intact|clean|damaged?|broken|crushed|quarantined?|hold|inspection)?",
        re.IGNORECASE,
    )

    matches = list(clause_pattern.finditer(normalized_text))
    if matches:
        for match in matches:
            qty_raw = match.group(1)
            state_raw = (match.group(2) or "").lower()

            if state_raw in {"damaged", "damage", "broken", "crushed"}:
                inv_state = "DAMAGED"
                line_note = extracted_note
            elif state_raw in {"quarantine", "quarantined", "hold", "inspection"}:
                inv_state = "QUARANTINED"
                line_note = extracted_note
            else:
                inv_state = "AVAILABLE"
                line_note = None

            lines.append(
                VoiceParsedLine(
                    quantity=_format_quantity(qty_raw),
                    inventory_state=inv_state,
                    condition_note=line_note,
                )
            )

    # If no state matches were parsed, look for simple quantity e.g. "received 50 units"
    if not lines:
        single_num = re.search(r"\b(\d+(?:\.\d+)?)\b", normalized_text)
        if single_num:
            lines.append(
                VoiceParsedLine(
                    quantity=_format_quantity(single_num.group(1)),
                    inventory_state="AVAILABLE",
                    condition_note=extracted_note,
                )
            )

    if not lines:
        warnings.append("Could not parse quantity from speech transcript. Manual review required.")
        return VoiceParsedReceivingDraft(
            lines=[],
            needs_manual_review=True,
            warnings=warnings,
            raw_transcript=transcript,
        )

    return VoiceParsedReceivingDraft(
        lines=lines,
        general_notes=extracted_note,
        needs_manual_review=False,
        warnings=warnings,
        raw_transcript=transcript,
    )


async def parse_receiving_transcript(
    transcript: str,
    *,
    ai_provider: AIProvider | None = None,
) -> VoiceParsedReceivingDraft:
    """
    Parse a speech transcript into a structured receiving draft.

    Tries Gemini LLM parser first when available and enabled; falls back to
    the deterministic regex parser on any provider unavailability or error.

    Args:
        transcript: Raw speech-to-text transcript.
        ai_provider: Optional configured AIProvider instance.

    Returns:
        VoiceParsedReceivingDraft: Standardized structured receiving lines.

    Raises:
        None.
    """
    clean_transcript = transcript.strip()
    if not clean_transcript:
        return parse_deterministic_transcript("")

    # Try LLM if configured and not disabled
    if ai_provider and not isinstance(ai_provider, DisabledAIProvider):
        try:
            system_prompt = (
                "You are an expert warehouse receiving parser. "
                "Parse the operator's spoken receipt description into a JSON structure.\n"
                "Allowed inventory_state values: 'AVAILABLE', 'DAMAGED', 'QUARANTINED'.\n"
                "Format numbers as decimal strings with 2 decimal places (e.g., '12.00').\n"
                "DO NOT invent product identity or SKU. Only parse quantities, states, and condition notes.\n"
                "Return ONLY valid JSON with keys: lines (array of {quantity, inventory_state, condition_note}), "
                "general_notes (string or null), needs_manual_review (boolean), warnings (array of strings)."
            )
            request = AIProviderRequest(
                prompt=f"Spoken transcript: \"{clean_transcript}\"",
                model_name="gemini-3.1-flash-lite-preview",
                system_instruction=system_prompt,
            )
            response = await ai_provider.generate_text(request)
            text_resp = response.text.strip()
            
            # Clean markdown codeblocks if returned
            if text_resp.startswith("```"):
                text_resp = re.sub(r"^```(?:json)?\n?", "", text_resp)
                text_resp = re.sub(r"\n?```$", "", text_resp)

            parsed_json = json.loads(text_resp)
            lines = [
                VoiceParsedLine(
                    quantity=_format_quantity(str(item.get("quantity", "1.00"))),
                    inventory_state=str(item.get("inventory_state", "AVAILABLE")).upper(),
                    condition_note=item.get("condition_note"),
                )
                for item in parsed_json.get("lines", [])
            ]
            if lines:
                return VoiceParsedReceivingDraft(
                    lines=lines,
                    general_notes=parsed_json.get("general_notes"),
                    needs_manual_review=bool(parsed_json.get("needs_manual_review", False)),
                    warnings=parsed_json.get("warnings", []),
                    raw_transcript=clean_transcript,
                )
        except Exception as exc:
            logger.info("AI LLM transcript parsing failed (%s); falling back to deterministic parser.", exc)

    # Deterministic fallback
    return parse_deterministic_transcript(clean_transcript)
