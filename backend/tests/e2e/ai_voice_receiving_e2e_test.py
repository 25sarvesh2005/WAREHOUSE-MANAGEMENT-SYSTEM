"""
--------------------------------------------------------------------------------
File        : tests/e2e/ai_voice_receiving_e2e_test.py
Purpose     : Run live HTTP E2E smoke tests for AI Release C voice-assisted receiving drafts.

Responsibilities:
    - Verify /health/status exposes voice provider configuration and alembic head.
    - Test authenticated transcript parsing into structured receiving drafts.
    - Test safety guardrail enforcement refusing direct mutation commands.
    - Test draft discard lifecycle transition.
    - Test voice interaction audit log retrieval.
    - Test speech synthesis graceful fallback when provider key is unconfigured.

Flow:
    Operator starts API
        ->
    python -m tests.e2e.ai_voice_receiving_e2e_test
        ->
    HTTP checks against /api/v1/voice endpoints

Used By:
    - CI/CD validation and deployment health checks.

Returns:
    None. Exits 0 on success, non-zero on failure.

Raises:
    RuntimeError: When an assertion fails.
    httpx.HTTPStatusError: On unexpected HTTP response.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass
from typing import Any

import httpx
from dotenv import load_dotenv

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000/api/v1"


@dataclass(frozen=True, slots=True)
class VoiceE2EContext:
    """Runtime context for Voice E2E smoke tests."""

    api_base_url: str
    admin_email: str
    admin_password: str
    token: str


class VoiceE2ERunner:
    """HTTP client runner for live voice receiving assistant endpoints."""

    def __init__(self, client: httpx.AsyncClient, context: VoiceE2EContext) -> None:
        self.client = client
        self.context = context

    @property
    def auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.context.token}"}

    async def test_health_status(self) -> None:
        """Verify health check includes voice metadata and correct alembic head."""
        root_url = self.context.api_base_url.removesuffix("/api/v1")
        response = await self.client.get(f"{root_url}/health/status")
        response.raise_for_status()
        data = response.json()

        assert "voice" in data, "Expected 'voice' key in /health/status response"
        assert data["alembic_head"] == "d2e3f4a5b6c7", f"Unexpected alembic head: {data.get('alembic_head')}"
        voice_info = data["voice"]
        assert "stt_provider" in voice_info
        assert "tts_provider" in voice_info
        print("  ✓ /health/status contains valid voice provider metadata and alembic head d2e3f4a5b6c7")

    async def test_parse_valid_transcript(self) -> str:
        """Verify parsing valid spoken transcript returns structured receiving lines."""
        payload = {
            "transcript": "received 12 available and 2 damaged note box crushed",
            "language_code": "en-IN",
        }
        response = await self.client.post(
            f"{self.context.api_base_url}/voice/receiving/parse-transcript",
            json=payload,
            headers=self.auth_headers,
        )
        response.raise_for_status()
        data = response.json()

        assert "draft_id" in data
        assert data["status"] == "DRAFTED"
        assert data["safety_decision"] == "ALLOW_DRAFT_ONLY"
        assert len(data["lines"]) == 2
        assert data["lines"][0]["quantity"] == "12.00"
        assert data["lines"][0]["inventory_state"] == "AVAILABLE"
        assert data["lines"][1]["quantity"] == "2.00"
        assert data["lines"][1]["inventory_state"] == "DAMAGED"
        assert data["lines"][1]["condition_note"] == "box crushed"

        print(f"  ✓ /voice/receiving/parse-transcript created draft {data['draft_id']} with 2 lines")
        return str(data["draft_id"])

    async def test_safety_refusal(self) -> None:
        """Verify voice safety guard blocks mutation command."""
        payload = {
            "transcript": "complete the receipt and adjust balance immediately",
            "language_code": "en-IN",
        }
        response = await self.client.post(
            f"{self.context.api_base_url}/voice/receiving/parse-transcript",
            json=payload,
            headers=self.auth_headers,
        )
        assert response.status_code == 400, f"Expected 400 Bad Request, got {response.status_code}"
        err = response.json()
        assert "strictly draft-only" in err.get("detail", "")
        print("  ✓ /voice/receiving/parse-transcript correctly refused mutation command with safety explanation")

    async def test_discard_voice_draft(self, draft_id: str) -> None:
        """Verify discarding a voice draft marks it as DISCARDED."""
        response = await self.client.post(
            f"{self.context.api_base_url}/voice/drafts/{draft_id}/discard",
            json={"reason": "Testing E2E discard flow"},
            headers=self.auth_headers,
        )
        response.raise_for_status()
        data = response.json()

        assert data["status"] == "DISCARDED"
        assert data["safety_decision"] == "DISCARDED"
        print(f"  ✓ /voice/drafts/{draft_id}/discard marked draft as DISCARDED")

    async def test_list_interactions(self) -> None:
        """Verify audit listing returns voice interactions."""
        response = await self.client.get(
            f"{self.context.api_base_url}/voice/interactions?limit=10",
            headers=self.auth_headers,
        )
        response.raise_for_status()
        data = response.json()

        assert "total" in data
        assert "items" in data
        assert data["total"] >= 1
        print(f"  ✓ /voice/interactions returned {data['total']} recorded interactions")

    async def test_voice_synthesis_fallback(self) -> None:
        """Verify TTS endpoint gracefully reports status when provider key is unconfigured or configured."""
        payload = {
            "text": "Draft created with 12 available and 2 damaged units.",
            "language_code": "en-IN",
        }
        response = await self.client.post(
            f"{self.context.api_base_url}/voice/speak",
            json=payload,
            headers=self.auth_headers,
        )
        # Either 200 (if SARVAM_API_KEY is configured in env) or 503 (if missing placeholder)
        assert response.status_code in {200, 503}, f"Unexpected TTS status: {response.status_code}"
        if response.status_code == 200:
            data = response.json()
            assert "audio_base64" in data
            print("  ✓ /voice/speak successfully synthesized audio")
        else:
            print("  ✓ /voice/speak gracefully returned 503 Service Unavailable when TTS unconfigured")

    async def run(self) -> None:
        """Execute all voice E2E smoke tests in sequence."""
        print("\nStarting AI Release C Voice Receiving E2E Smoke Tests...")
        await self.test_health_status()
        draft_id = await self.test_parse_valid_transcript()
        await self.test_safety_refusal()
        await self.test_discard_voice_draft(draft_id)
        await self.test_list_interactions()
        await self.test_voice_synthesis_fallback()
        print("\nAll AI Release C Voice E2E Smoke Tests Passed Successfully!\n")


async def authenticate(
    client: httpx.AsyncClient,
    *,
    api_base_url: str,
    admin_email: str,
    admin_password: str,
) -> str:
    """Authenticate administrator to obtain bearer token."""
    response = await client.post(
        f"{api_base_url}/auth/login",
        json={"email": admin_email, "password": admin_password},
    )
    response.raise_for_status()
    return str(response.json()["access_token"])


async def async_main() -> None:
    """Entry point for running voice E2E checks."""
    load_dotenv()
    parser = argparse.ArgumentParser(description="Run AI Release C Voice E2E smoke tests.")
    parser.add_argument(
        "--api-base-url",
        default=os.getenv("WAREHOUSE_API_BASE_URL", DEFAULT_API_BASE_URL),
    )
    args = parser.parse_args()

    api_base_url = str(args.api_base_url).rstrip("/")
    admin_email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "admin@whitfield.local")
    admin_password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "change-this-before-use")

    async with httpx.AsyncClient(timeout=30.0) as client:
        token = await authenticate(
            client,
            api_base_url=api_base_url,
            admin_email=admin_email,
            admin_password=admin_password,
        )
        context = VoiceE2EContext(
            api_base_url=api_base_url,
            admin_email=admin_email,
            admin_password=admin_password,
            token=token,
        )
        await VoiceE2ERunner(client, context).run()


def main() -> None:
    """Synchronous runner."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
