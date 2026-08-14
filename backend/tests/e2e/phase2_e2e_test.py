"""
--------------------------------------------------------------------------------
File        : tests/e2e/phase2_e2e_test.py
Purpose     : Run Phase 2 live API smoke verification against a configured backend.

Responsibilities:
    - Verify receiving governance against a running FastAPI server.
    - Exercise duplicate receipt blocking and offline client_draft_id replay.
    - Confirm damaged, quarantined, and available receipt quantities reconcile.
    - Keep E2E execution opt-in so normal pytest runs do not mutate live data.

Flow:
    Operator starts API
        ->
    python -m tests.e2e.phase2_e2e_test
        ->
    Script authenticates and creates unique smoke records
        ->
    Script verifies Phase 2 acceptance behaviors

Used By:
    - Manual Phase 2 acceptance validation.
    - Release smoke-test runbooks.

Returns:
    main() -> None - Prints a pass/fail summary and exits non-zero on failure.

Raises:
    RuntimeError: When a required E2E assertion fails.
    httpx.HTTPStatusError: When an unexpected API status is returned.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import argparse
import asyncio
import os
from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4

import httpx
from dotenv import load_dotenv

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000/api/v1"


@dataclass(frozen=True)
class Phase2Context:
    """Runtime IDs and authentication state for one Phase 2 smoke run."""

    api_base_url: str
    admin_email: str
    admin_password: str
    seller_id: str
    warehouse_id: str
    token: str


class Phase2E2ERunner:
    """HTTP client wrapper for the Phase 2 receiving-governance smoke test."""

    def __init__(self, client: httpx.AsyncClient, context: Phase2Context) -> None:
        """
        Initialize the E2E runner with an authenticated HTTP client.

        Args:
            client: Async HTTP client configured for the API base URL.
            context: Runtime authentication and master-data IDs.

        Returns:
            None.
        """
        self.client = client
        self.context = context
        self.passed_steps: list[str] = []

    async def run(self) -> None:
        """
        Execute all Phase 2 E2E smoke checks in deterministic order.

        Returns:
            None.

        Raises:
            RuntimeError: If a Phase 2 acceptance behavior fails.
            httpx.HTTPStatusError: If an unexpected API response is returned.
        """
        product = await self.create_smoke_product()
        receipt = await self.verify_mixed_receipt_completion(product["id"])
        await self.verify_duplicate_receipt_block(receipt["source_reference"])
        await self.verify_offline_draft_replay()
        await self.verify_receipt_cancellation_rules(receipt["id"])
        await self.verify_product_ledger_reconciliation(product["id"])

    async def create_smoke_product(self) -> dict:
        """
        Create a unique seller product for isolated receipt/balance assertions.

        Returns:
            dict: Created product response payload.

        Raises:
            httpx.HTTPStatusError: If product creation fails.
        """
        sku = f"PHASE2-SKU-{uuid4().hex[:8].upper()}"
        response = await self.client.post(
            "/products",
            json={
                "seller_id": self.context.seller_id,
                "sku": sku,
                "name": f"Phase 2 E2E Smoke SKU {sku}",
                "unit_of_measure": "EA",
                "status": "ACTIVE",
            },
        )
        response.raise_for_status()
        product = response.json()
        self.mark_passed(f"Created isolated smoke product {sku}")
        return product

    async def verify_mixed_receipt_completion(self, product_id: str) -> dict:
        """
        Complete a receipt with sellable, damaged, and quarantined quantities.

        Args:
            product_id: Product UUID to receive.

        Returns:
            dict: Completed receipt response payload.

        Raises:
            RuntimeError: If completion status is not COMPLETED.
            httpx.HTTPStatusError: If an unexpected API call fails.
        """
        source_reference = f"PHASE2-RCV-{uuid4().hex[:10].upper()}"
        receipt = await self.create_receipt(source_reference)
        line_response = await self.client.post(
            f"/receipts/{receipt['id']}/lines",
            json={
                "product_id": product_id,
                "expected_quantity": 10,
                "sellable_quantity": 6,
                "damaged_quantity": 2,
                "quarantined_quantity": 2,
                "notes": "Phase 2 E2E mixed condition receipt.",
            },
        )
        line_response.raise_for_status()

        complete_response = await self.client.post(
            f"/receipts/{receipt['id']}/complete",
            json={"notes": "Phase 2 E2E completion."},
        )
        complete_response.raise_for_status()
        completed = complete_response.json()
        if completed["status"] != "COMPLETED":
            raise RuntimeError(f"Expected completed receipt, got {completed['status']}.")

        completed["source_reference"] = source_reference
        self.mark_passed("Completed receipt posts available/damaged/quarantined quantities")
        return completed

    async def verify_duplicate_receipt_block(self, source_reference: str) -> None:
        """
        Verify completed receipt source references cannot be reused normally.

        Args:
            source_reference: Source reference from an already completed receipt.

        Returns:
            None.

        Raises:
            RuntimeError: If duplicate creation does not return HTTP 409.
        """
        duplicate_response = await self.client.post(
            "/receipts",
            json={
                "seller_id": self.context.seller_id,
                "warehouse_id": self.context.warehouse_id,
                "source_type": "CARRIER_TRACKING",
                "source_reference": source_reference,
            },
        )
        if duplicate_response.status_code != 409:
            raise RuntimeError(
                "Expected duplicate completed receipt to return HTTP 409, "
                f"got {duplicate_response.status_code}: {duplicate_response.text}"
            )
        self.mark_passed("Duplicate completed receipt is blocked with HTTP 409")

    async def verify_offline_draft_replay(self) -> None:
        """
        Verify client_draft_id replay returns the existing receipt draft.

        Returns:
            None.

        Raises:
            RuntimeError: If replay creates a different receipt ID.
            httpx.HTTPStatusError: If an unexpected API call fails.
        """
        client_draft_id = f"phase2-e2e-{uuid4()}"
        source_reference = f"PHASE2-OFFLINE-{uuid4().hex[:10].upper()}"
        payload = {
            "seller_id": self.context.seller_id,
            "warehouse_id": self.context.warehouse_id,
            "source_type": "DROP_OFF_TICKET",
            "source_reference": source_reference,
            "client_draft_id": client_draft_id,
        }

        first_response = await self.client.post("/receipts", json=payload)
        first_response.raise_for_status()
        second_response = await self.client.post("/receipts", json=payload)
        second_response.raise_for_status()

        first_receipt = first_response.json()
        second_receipt = second_response.json()
        if first_receipt["id"] != second_receipt["id"]:
            raise RuntimeError("client_draft_id replay created a new receipt instead of reusing.")

        cancel_response = await self.client.post(f"/receipts/{first_receipt['id']}/cancel")
        cancel_response.raise_for_status()
        self.mark_passed("Offline client_draft_id replay is idempotent")

    async def verify_receipt_cancellation_rules(self, completed_receipt_id: str) -> None:
        """
        Verify completed receipts cannot be cancelled.

        Args:
            completed_receipt_id: Completed receipt UUID.

        Returns:
            None.

        Raises:
            RuntimeError: If cancelling a completed receipt does not fail.
        """
        cancel_response = await self.client.post(f"/receipts/{completed_receipt_id}/cancel")
        if cancel_response.status_code not in {400, 409}:
            raise RuntimeError(
                "Expected completed receipt cancellation to fail, "
                f"got {cancel_response.status_code}: {cancel_response.text}"
            )
        self.mark_passed("Completed receipt cancellation is blocked")

    async def verify_product_ledger_reconciliation(self, product_id: str) -> None:
        """
        Compare movement sums and balance projections for the smoke product.

        Args:
            product_id: Product UUID used for the completed smoke receipt.

        Returns:
            None.

        Raises:
            RuntimeError: If balance projection differs from movement sums.
            httpx.HTTPStatusError: If balance or movement query fails.
        """
        balances_response = await self.client.get(
            "/inventory/balances",
            params={
                "seller_id": self.context.seller_id,
                "warehouse_id": self.context.warehouse_id,
                "product_id": product_id,
                "limit": 200,
            },
        )
        balances_response.raise_for_status()
        movements_response = await self.client.get(
            "/inventory/movements",
            params={
                "seller_id": self.context.seller_id,
                "warehouse_id": self.context.warehouse_id,
                "product_id": product_id,
                "limit": 200,
            },
        )
        movements_response.raise_for_status()

        balance_totals = self.quantities_by_state(balances_response.json(), "quantity")
        movement_totals = self.quantities_by_state(movements_response.json(), "quantity_delta")
        expected = {
            "AVAILABLE": Decimal("6.00"),
            "DAMAGED": Decimal("2.00"),
            "QUARANTINED": Decimal("2.00"),
        }

        for state, expected_quantity in expected.items():
            if balance_totals.get(state, Decimal("0.00")) != expected_quantity:
                raise RuntimeError(f"Balance for {state} did not equal {expected_quantity}.")
            if movement_totals.get(state, Decimal("0.00")) != expected_quantity:
                raise RuntimeError(f"Movement sum for {state} did not equal {expected_quantity}.")

        if balance_totals != movement_totals:
            raise RuntimeError(
                f"Balance projection differs from movement ledger: {balance_totals} vs {movement_totals}"
            )

        self.mark_passed("Smoke product balances reconcile exactly to movement ledger")

    async def create_receipt(self, source_reference: str) -> dict:
        """
        Create a receipt draft for the configured seller and warehouse.

        Args:
            source_reference: Unique source reference for the receipt.

        Returns:
            dict: Created receipt response payload.

        Raises:
            httpx.HTTPStatusError: If receipt creation fails.
        """
        response = await self.client.post(
            "/receipts",
            json={
                "seller_id": self.context.seller_id,
                "warehouse_id": self.context.warehouse_id,
                "source_type": "CARRIER_TRACKING",
                "source_reference": source_reference,
            },
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def quantities_by_state(rows: list[dict], quantity_key: str) -> dict[str, Decimal]:
        """
        Aggregate API rows by inventory_state using Decimal math.

        Args:
            rows: Balance or movement response rows.
            quantity_key: Numeric quantity key to sum.

        Returns:
            dict[str, Decimal]: Quantity totals keyed by inventory state.
        """
        totals: dict[str, Decimal] = {}
        for row in rows:
            state = str(row["inventory_state"])
            quantity = Decimal(str(row[quantity_key]))
            totals[state] = totals.get(state, Decimal("0.00")) + quantity
        return totals

    def mark_passed(self, message: str) -> None:
        """
        Record and print a passed E2E step.

        Args:
            message: Human-readable step description.

        Returns:
            None.
        """
        self.passed_steps.append(message)
        print(f"PASSED {len(self.passed_steps)}: {message}")


async def authenticate_and_build_context(
    client: httpx.AsyncClient,
    api_base_url: str,
    admin_email: str,
    admin_password: str,
) -> Phase2Context:
    """
    Authenticate and select the first visible seller and warehouse for E2E records.

    Args:
        client: Async HTTP client configured for the API base URL.
        api_base_url: API base URL used in status output.
        admin_email: Admin email for login.
        admin_password: Admin password for login.

    Returns:
        Phase2Context: Authenticated runtime context.

    Raises:
        RuntimeError: If no seller or warehouse master data is available.
        httpx.HTTPStatusError: If login or master-data loading fails.
    """
    token_response = await client.post(
        "/auth/login",
        json={"email": admin_email, "password": admin_password},
    )
    token_response.raise_for_status()
    token = token_response.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})

    sellers_response = await client.get("/sellers")
    sellers_response.raise_for_status()
    warehouses_response = await client.get("/warehouses")
    warehouses_response.raise_for_status()
    sellers = sellers_response.json()
    warehouses = warehouses_response.json()
    if not sellers:
        raise RuntimeError("No sellers are available for Phase 2 E2E testing.")
    if not warehouses:
        raise RuntimeError("No warehouses are available for Phase 2 E2E testing.")

    return Phase2Context(
        api_base_url=api_base_url,
        admin_email=admin_email,
        admin_password=admin_password,
        seller_id=sellers[0]["id"],
        warehouse_id=warehouses[0]["id"],
        token=token,
    )


def build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line argument parser for Phase 2 E2E execution.

    Returns:
        argparse.ArgumentParser: Configured parser.
    """
    parser = argparse.ArgumentParser(description="Run Phase 2 receiving-governance E2E smoke test.")
    parser.add_argument(
        "--api-base-url",
        default=os.getenv("PHASE2_E2E_API_BASE_URL", DEFAULT_API_BASE_URL),
        help="Versioned API base URL, for example http://127.0.0.1:8000/api/v1.",
    )
    parser.add_argument(
        "--admin-email",
        default=os.getenv("BOOTSTRAP_ADMIN_EMAIL"),
        help="Admin login email. Defaults to BOOTSTRAP_ADMIN_EMAIL.",
    )
    parser.add_argument(
        "--admin-password",
        default=os.getenv("BOOTSTRAP_ADMIN_PASSWORD"),
        help="Admin login password. Defaults to BOOTSTRAP_ADMIN_PASSWORD.",
    )
    return parser


async def async_main() -> None:
    """
    Load configuration and run the Phase 2 E2E smoke test.

    Returns:
        None.

    Raises:
        RuntimeError: If required credentials are missing or any E2E assertion fails.
    """
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args()
    if not args.admin_email or not args.admin_password:
        raise RuntimeError(
            "Set BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD, or pass "
            "--admin-email and --admin-password."
        )

    async with httpx.AsyncClient(base_url=args.api_base_url, timeout=30.0) as client:
        context = await authenticate_and_build_context(
            client,
            args.api_base_url,
            args.admin_email,
            args.admin_password,
        )
        runner = Phase2E2ERunner(client, context)
        await runner.run()
        print(f"\nPhase 2 E2E complete: {len(runner.passed_steps)} / 6 checks passed.")


def main() -> None:
    """
    Run the async Phase 2 E2E entrypoint from a synchronous CLI boundary.

    Returns:
        None.
    """
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
