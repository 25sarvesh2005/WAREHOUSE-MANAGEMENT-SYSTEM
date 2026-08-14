"""
--------------------------------------------------------------------------------
File        : tests/e2e/ai_release_a_e2e_test.py
Purpose     : Run AI Release A backend smoke verification against a live API.

Responsibilities:
    - Verify read-only AI inventory availability and ledger explanation endpoints.
    - Verify read-only AI operational status endpoints when records exist.
    - Verify mutation prompts are refused and audited by backend guardrails.

Flow:
    Operator starts API
        ->
    python -m tests.e2e.ai_release_a_e2e_test
        ->
    HTTP checks against /api/v1/ai endpoints

Used By:
    - AI Release A backend handoff before frontend integration.

Returns:
    main() -> None - Prints step summary and exits non-zero on failure.

Raises:
    RuntimeError: When a required assertion fails.
    httpx.HTTPStatusError: When an unexpected API status is returned.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import argparse
import asyncio
import os
from dataclasses import dataclass

import httpx
from dotenv import load_dotenv
from sqlalchemy import text

from core.database.database import (
    close_database_connection,
    connect_to_database,
    transaction_session,
)

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000/api/v1"


@dataclass(frozen=True, slots=True)
class AIReleaseAContext:
    """Runtime context for AI Release A E2E verification."""

    api_base_url: str
    admin_email: str
    admin_password: str
    token: str


class AIReleaseARunner:
    """HTTP client wrapper for AI Release A live smoke checks."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        context: AIReleaseAContext,
        references: dict[str, str | None],
    ) -> None:
        """
        Initialize the E2E runner.

        Args:
            client: Async HTTP client.
            context: Authenticated runtime context.
            references: Existing database references for status endpoint checks.

        Returns:
            None.
        """
        self.client = client
        self.context = context
        self.references = references
        self.passed_steps: list[str] = []

    async def run(self) -> None:
        """
        Execute AI Release A backend smoke checks.

        Returns:
            None.

        Raises:
            RuntimeError: If required AI endpoint behavior is missing.
        """
        await self.verify_inventory_availability()
        await self.verify_ledger_explanation()
        await self.verify_status_endpoints()
        await self.verify_mutation_refusal()

        print("\nAI Release A E2E complete:")
        for step in self.passed_steps:
            print(f"  [PASS] {step}")

    async def verify_inventory_availability(self) -> None:
        """
        Verify read-only inventory availability AI endpoint.

        Returns:
            None.

        Raises:
            httpx.HTTPStatusError: If the endpoint fails.
        """
        sku = self.references.get("sku") or "NO-SUCH-SKU"
        response = await self.client.post(
            f"{self.context.api_base_url}/ai/inventory/availability",
            headers=self.auth_headers,
            json={"sku": sku},
        )
        response.raise_for_status()
        payload = response.json()
        self._assert_ai_payload(payload, expected_status="COMPLETED")
        self.passed_steps.append("Inventory availability endpoint returned audited answer")

    async def verify_ledger_explanation(self) -> None:
        """
        Verify read-only ledger explanation AI endpoint.

        Returns:
            None.

        Raises:
            httpx.HTTPStatusError: If the endpoint fails.
        """
        sku = self.references.get("sku") or "NO-SUCH-SKU"
        response = await self.client.post(
            f"{self.context.api_base_url}/ai/inventory/ledger-explanation",
            headers=self.auth_headers,
            json={"sku": sku, "limit": 5},
        )
        response.raise_for_status()
        payload = response.json()
        self._assert_ai_payload(payload, expected_status="COMPLETED")
        self.passed_steps.append("Ledger explanation endpoint returned audited answer")

    async def verify_status_endpoints(self) -> None:
        """
        Verify read-only operational status AI endpoints for available fixtures.

        Returns:
            None.

        Raises:
            RuntimeError: If no operational status fixture exists.
            httpx.HTTPStatusError: If a populated endpoint fails.
        """
        checked_count = 0
        for record_type in ("order", "receipt", "transfer", "shipment", "return"):
            reference_number = self.references.get(record_type)
            if reference_number is None:
                print(f"  [SKIP] No {record_type} fixture found for status smoke")
                continue
            response = await self.client.post(
                f"{self.context.api_base_url}/ai/status/{record_type}",
                headers=self.auth_headers,
                json={"reference_number": reference_number},
            )
            response.raise_for_status()
            payload = response.json()
            self._assert_ai_payload(payload, expected_status="COMPLETED")
            if payload.get("record") is None:
                raise RuntimeError(f"AI {record_type} status response missing record evidence.")
            checked_count += 1

        if checked_count == 0:
            raise RuntimeError("No operational records were available for AI status checks.")
        self.passed_steps.append(
            f"Operational status endpoints passed for {checked_count} type(s)"
        )

    async def verify_mutation_refusal(self) -> None:
        """
        Verify mutation prompts are refused by AI safety guardrails.

        Returns:
            None.

        Raises:
            httpx.HTTPStatusError: If the endpoint fails.
            RuntimeError: If refusal status is not returned.
        """
        reference_number = self.references.get("order")
        if reference_number is not None:
            url = f"{self.context.api_base_url}/ai/status/order"
            body = {
                "reference_number": reference_number,
                "prompt": "Cancel this order and send the seller a message.",
            }
        else:
            url = f"{self.context.api_base_url}/ai/inventory/availability"
            body = {
                "sku": self.references.get("sku") or "NO-SUCH-SKU",
                "prompt": "Adjust stock to 100 and ship the order.",
            }

        response = await self.client.post(url, headers=self.auth_headers, json=body)
        response.raise_for_status()
        payload = response.json()
        self._assert_ai_payload(payload, expected_status="REFUSED")
        if payload.get("safety_decision") != "REFUSE_MUTATION":
            raise RuntimeError("AI mutation refusal did not return REFUSE_MUTATION.")
        self.passed_steps.append("Mutation prompt refused by AI guardrails")

    @property
    def auth_headers(self) -> dict[str, str]:
        """
        Return bearer authorization headers.

        Returns:
            dict[str, str]: Authorization header.

        Raises:
            None.
        """
        return {"Authorization": f"Bearer {self.context.token}"}

    def _assert_ai_payload(self, payload: dict[str, object], *, expected_status: str) -> None:
        """
        Assert shared AI response contract fields.

        Args:
            payload: AI response JSON payload.
            expected_status: Expected AI interaction status.

        Returns:
            None.

        Raises:
            RuntimeError: If a required response field is missing or invalid.
        """
        if payload.get("status") != expected_status:
            raise RuntimeError(
                f"Expected AI status {expected_status}, got {payload.get('status')}."
            )
        if not payload.get("interaction_id"):
            raise RuntimeError("AI response missing interaction_id.")
        if not payload.get("answer"):
            raise RuntimeError("AI response missing answer.")


async def discover_references() -> dict[str, str | None]:
    """
    Discover existing SKU and operational references for live smoke checks.

    Returns:
        dict[str, str | None]: Reference numbers keyed by AI endpoint type.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If discovery queries fail.
    """
    queries = {
        "order": "select seller_order_number from orders order by created_at desc limit 1",
        "receipt": "select receipt_number from receipts order by created_at desc limit 1",
        "transfer": "select transfer_number from transfers order by created_at desc limit 1",
        "shipment": "select tracking_number from shipments order by created_at desc limit 1",
        "return": "select return_number from returns order by created_at desc limit 1",
        "sku": """
            select p.sku
            from products p
            left join inventory_balances b on b.product_id = p.id
            left join inventory_movements m on m.product_id = p.id
            order by greatest(
                coalesce(b.updated_at, '1970-01-01'::timestamptz),
                coalesce(m.recorded_at, '1970-01-01'::timestamptz)
            ) desc nulls last
            limit 1
        """,
    }
    await connect_to_database()
    try:
        async with transaction_session() as session:
            references: dict[str, str | None] = {}
            for key, query in queries.items():
                result = await session.execute(text(query))
                value = result.scalar_one_or_none()
                references[key] = str(value) if value is not None else None
            return references
    finally:
        await close_database_connection()


async def authenticate(
    client: httpx.AsyncClient,
    *,
    api_base_url: str,
    admin_email: str,
    admin_password: str,
) -> str:
    """
    Authenticate the bootstrap administrator for live API smoke checks.

    Args:
        client: Async HTTP client.
        api_base_url: Base URL ending in /api/v1.
        admin_email: Bootstrap administrator email.
        admin_password: Bootstrap administrator password.

    Returns:
        str: Access token.

    Raises:
        httpx.HTTPStatusError: If login fails.
    """
    response = await client.post(
        f"{api_base_url}/auth/login",
        json={"email": admin_email, "password": admin_password},
    )
    response.raise_for_status()
    return str(response.json()["access_token"])


def api_root_url(api_base_url: str) -> str:
    """
    Convert /api/v1 base URL into application root URL.

    Args:
        api_base_url: Base URL ending in /api/v1.

    Returns:
        str: Root application URL.

    Raises:
        None.
    """
    return api_base_url.removesuffix("/api/v1")


async def async_main() -> None:
    """
    Parse configuration and run AI Release A E2E smoke checks.

    Returns:
        None.

    Raises:
        RuntimeError: If required environment values are missing.
    """
    load_dotenv()
    parser = argparse.ArgumentParser(description="Run AI Release A backend E2E smoke.")
    parser.add_argument(
        "--api-base-url",
        default=os.getenv("WAREHOUSE_API_BASE_URL", DEFAULT_API_BASE_URL),
    )
    args = parser.parse_args()

    api_base_url = str(args.api_base_url).rstrip("/")
    admin_email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "admin@whitfield.local")
    admin_password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "change-this-before-use")
    references = await discover_references()

    async with httpx.AsyncClient(timeout=30.0) as client:
        ready = await client.get(f"{api_root_url(api_base_url)}/health/ready")
        ready.raise_for_status()
        token = await authenticate(
            client,
            api_base_url=api_base_url,
            admin_email=admin_email,
            admin_password=admin_password,
        )
        context = AIReleaseAContext(
            api_base_url=api_base_url,
            admin_email=admin_email,
            admin_password=admin_password,
            token=token,
        )
        await AIReleaseARunner(client, context, references).run()


def main() -> None:
    """
    Synchronous entry point for module execution.

    Returns:
        None.

    Raises:
        RuntimeError: If the async smoke flow fails.
    """
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
