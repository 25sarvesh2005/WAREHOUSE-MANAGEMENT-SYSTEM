"""
--------------------------------------------------------------------------------
File        : tests/e2e/phase5_file_import_e2e_test.py
Purpose     : Run Phase 5 file-upload migration verification against live API.

Responsibilities:
    - Verify CSV upload stages opening inventory rows without mutating inventory.
    - Verify duplicate upload idempotency and changed-row conflict.
    - Verify staged rows can follow existing validate/approve/apply/reconcile flow.

Flow:
    Operator starts API -> python -m tests.e2e.phase5_file_import_e2e_test

Used By:
    - Phase 5 Slice 2 release smoke test.

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
from decimal import Decimal
from uuid import uuid4

import httpx
from dotenv import load_dotenv

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000/api/v1"


@dataclass(frozen=True)
class Phase5FileImportContext:
    """Runtime state for Phase 5 file import E2E verification."""

    api_base_url: str
    admin_email: str
    admin_password: str
    token: str


class Phase5FileImportRunner:
    """HTTP client wrapper for Phase 5 file import smoke checks."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        context: Phase5FileImportContext,
    ) -> None:
        """
        Initialize the E2E runner.

        Args:
            client: Async HTTP client.
            context: Authenticated runtime context.

        Returns:
            None.
        """
        self.client = client
        self.context = context
        self.passed_steps: list[str] = []

    async def run(self) -> None:
        """
        Execute the Phase 5 file import verification flow.

        Returns:
            None.
        """
        seller = await self.create_seller_fixture()
        warehouse = await self.create_warehouse_fixture()
        product = await self.create_product_fixture(seller["id"])
        batch = await self.create_batch()

        await self.upload_csv_and_verify_staging_only(batch, seller, warehouse, product)
        await self.verify_duplicate_upload_rules(batch, seller, warehouse, product)
        await self.validate_approve_apply_reconcile(batch, seller, warehouse, product)

        print(f"\nPhase 5 file import E2E complete: {len(self.passed_steps)} checks passed.")
        for step in self.passed_steps:
            print(f"  [PASS] {step}")

    async def create_seller_fixture(self) -> dict:
        """Create an isolated seller fixture."""
        code = f"P5FILE-SEL-{uuid4().hex[:6].upper()}"
        response = await self.client.post(
            f"{self.context.api_base_url}/sellers",
            headers=self.auth_headers(),
            json={"code": code, "name": f"Phase 5 File Seller {code}"},
        )
        response.raise_for_status()
        return response.json()

    async def create_warehouse_fixture(self) -> dict:
        """Create an isolated warehouse fixture."""
        code = f"P5FILE-WH-{uuid4().hex[:6].upper()}"
        response = await self.client.post(
            f"{self.context.api_base_url}/warehouses",
            headers=self.auth_headers(),
            json={"code": code, "name": f"Phase 5 File Warehouse {code}"},
        )
        response.raise_for_status()
        return response.json()

    async def create_product_fixture(self, seller_id: str) -> dict:
        """Create an isolated product fixture."""
        sku = f"P5FILE-SKU-{uuid4().hex[:6].upper()}"
        response = await self.client.post(
            f"{self.context.api_base_url}/products",
            headers=self.auth_headers(),
            json={"seller_id": seller_id, "sku": sku, "name": f"Product {sku}"},
        )
        response.raise_for_status()
        return response.json()

    async def create_batch(self) -> dict:
        """Create an isolated migration batch."""
        response = await self.client.post(
            f"{self.context.api_base_url}/migration/batches",
            headers=self.auth_headers(),
            json={"source_notes": "Phase 5 file import E2E"},
        )
        response.raise_for_status()
        return response.json()

    async def upload_csv_and_verify_staging_only(
        self,
        batch: dict,
        seller: dict,
        warehouse: dict,
        product: dict,
    ) -> None:
        """Upload a CSV file and verify it does not mutate inventory."""
        csv_bytes = self.build_csv_bytes(seller, warehouse, product, "75.00")
        response = await self.upload_csv(batch["id"], "opening_file_import.csv", csv_bytes)
        response.raise_for_status()
        summary = response.json()
        if summary["parsed_rows"] != 1:
            raise RuntimeError(f"Expected one parsed row, got {summary}")

        movements = await self.list_movements(seller, warehouse, product)
        balances = await self.list_balances(seller, warehouse, product)
        if movements:
            raise RuntimeError("Upload created inventory movements before apply.")
        if balances:
            raise RuntimeError("Upload updated inventory balances before apply.")

        self.passed_steps.append("CSV upload staged rows without mutating inventory")

    async def verify_duplicate_upload_rules(
        self,
        batch: dict,
        seller: dict,
        warehouse: dict,
        product: dict,
    ) -> None:
        """Verify exact duplicate upload is idempotent and modified row conflicts."""
        exact_csv = self.build_csv_bytes(seller, warehouse, product, "75.00")
        duplicate_response = await self.upload_csv(batch["id"], "opening_file_import.csv", exact_csv)
        duplicate_response.raise_for_status()

        changed_csv = self.build_csv_bytes(seller, warehouse, product, "76.00")
        conflict_response = await self.upload_csv(
            batch["id"],
            "opening_file_import.csv",
            changed_csv,
        )
        if conflict_response.status_code != 409:
            raise RuntimeError(
                "Expected changed same source row upload to return 409, got "
                f"{conflict_response.status_code}: {conflict_response.text}"
            )

        self.passed_steps.append("Duplicate upload idempotency and conflict rules verified")

    async def validate_approve_apply_reconcile(
        self,
        batch: dict,
        seller: dict,
        warehouse: dict,
        product: dict,
    ) -> None:
        """Run existing migration lifecycle after file staging."""
        validate_response = await self.client.post(
            f"{self.context.api_base_url}/migration/batches/{batch['id']}/validate",
            headers=self.auth_headers(),
        )
        validate_response.raise_for_status()
        validation = validate_response.json()
        if validation["status"] != "VALIDATED":
            raise RuntimeError(f"Expected VALIDATED after file upload, got {validation}")

        approve_response = await self.client.post(
            f"{self.context.api_base_url}/migration/batches/{batch['id']}/approve",
            headers=self.auth_headers(),
        )
        approve_response.raise_for_status()

        apply_response = await self.client.post(
            f"{self.context.api_base_url}/migration/batches/{batch['id']}/apply",
            headers=self.auth_headers(),
        )
        apply_response.raise_for_status()

        movements = await self.list_movements(seller, warehouse, product)
        migration_movements = [
            movement
            for movement in movements
            if movement["movement_type"] == "MIGRATION_OPENING_BALANCE"
        ]
        if len(migration_movements) != 1:
            raise RuntimeError(f"Expected one migration movement, got {movements}")

        balances = await self.list_balances(seller, warehouse, product)
        available = [
            balance
            for balance in balances
            if balance["inventory_state"] == "AVAILABLE"
        ]
        if not available or Decimal(str(available[0]["quantity"])) != Decimal("75.00"):
            raise RuntimeError(f"Expected available balance 75.00, got {balances}")

        reconcile_response = await self.client.get(
            f"{self.context.api_base_url}/migration/batches/{batch['id']}/reconciliation",
            headers=self.auth_headers(),
        )
        reconcile_response.raise_for_status()
        reconciliation = reconcile_response.json()
        if reconciliation["reconciliation_status"] != "MATCH":
            raise RuntimeError(f"Expected reconciliation MATCH, got {reconciliation}")

        self.passed_steps.append("File-staged batch validated, applied, and reconciled")

    async def upload_csv(
        self,
        batch_id: str,
        file_name: str,
        file_bytes: bytes,
    ) -> httpx.Response:
        """Upload CSV bytes to the migration upload endpoint."""
        return await self.client.post(
            f"{self.context.api_base_url}/migration/batches/{batch_id}/upload",
            headers=self.auth_headers(),
            files={"file": (file_name, file_bytes, "text/csv")},
        )

    async def list_movements(self, seller: dict, warehouse: dict, product: dict) -> list[dict]:
        """List movements for the isolated product scope."""
        response = await self.client.get(
            f"{self.context.api_base_url}/inventory/movements"
            f"?seller_id={seller['id']}&warehouse_id={warehouse['id']}"
            f"&product_id={product['id']}",
            headers=self.auth_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def list_balances(self, seller: dict, warehouse: dict, product: dict) -> list[dict]:
        """List balances for the isolated product scope."""
        response = await self.client.get(
            f"{self.context.api_base_url}/inventory/balances"
            f"?seller_id={seller['id']}&warehouse_id={warehouse['id']}"
            f"&product_id={product['id']}",
            headers=self.auth_headers(),
        )
        response.raise_for_status()
        return response.json()

    def build_csv_bytes(
        self,
        seller: dict,
        warehouse: dict,
        product: dict,
        quantity: str,
    ) -> bytes:
        """Build CSV bytes for the isolated fixture row."""
        csv_text = (
            "seller_code,sku,warehouse_code,inventory_state,quantity\n"
            f"{seller['code']},{product['sku']},{warehouse['code']},AVAILABLE,{quantity}\n"
        )
        return csv_text.encode("utf-8")

    def auth_headers(self) -> dict[str, str]:
        """Return bearer-token authorization headers."""
        return {"Authorization": f"Bearer {self.context.token}"}


async def build_context(args: argparse.Namespace) -> Phase5FileImportContext:
    """
    Build authenticated E2E context from CLI/environment arguments.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Phase5FileImportContext: Authenticated context.
    """
    api_url = str(args.api_url).rstrip("/")
    if not api_url.endswith("/api/v1"):
        api_url = f"{api_url}/api/v1" if not api_url.endswith("/api") else f"{api_url}/v1"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{api_url}/auth/login",
            json={"email": args.admin_email, "password": args.admin_password},
        )
        response.raise_for_status()
        token = response.json()["access_token"]

    return Phase5FileImportContext(
        api_base_url=api_url,
        admin_email=args.admin_email,
        admin_password=args.admin_password,
        token=token,
    )


def build_parser() -> argparse.ArgumentParser:
    """
    Build the E2E CLI argument parser.

    Returns:
        argparse.ArgumentParser: Configured parser.
    """
    parser = argparse.ArgumentParser(description="Run Phase 5 file import E2E test.")
    parser.add_argument(
        "--api-url",
        default=os.getenv("WAREHOUSE_API_BASE_URL", DEFAULT_API_BASE_URL),
    )
    parser.add_argument(
        "--admin-email",
        default=os.getenv("BOOTSTRAP_ADMIN_EMAIL"),
    )
    parser.add_argument(
        "--admin-password",
        default=os.getenv("BOOTSTRAP_ADMIN_PASSWORD"),
    )
    return parser


async def async_main() -> None:
    """
    Execute the async E2E entry point.

    Returns:
        None.
    """
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args()
    if not args.admin_email or not args.admin_password:
        raise RuntimeError(
            "Set BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD, or pass "
            "--admin-email and --admin-password."
        )

    context = await build_context(args)
    async with httpx.AsyncClient(timeout=30.0) as client:
        await Phase5FileImportRunner(client, context).run()


def main() -> None:
    """
    Run the E2E script.

    Returns:
        None.
    """
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
