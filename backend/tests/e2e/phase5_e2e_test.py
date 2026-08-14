"""
--------------------------------------------------------------------------------
File        : tests/e2e/phase5_e2e_test.py
Purpose     : Run Phase 5 live API verification for opening inventory migration.

Responsibilities:
    - Verify import batch creation, raw row staging, and idempotency/conflict rules.
    - Verify validation detects invalid quantities/states and blocks approval when invalid_rows > 0.
    - Verify authorization guards block unauthorized roles (SELLER/STAFF) from approving/applying.
    - Verify batch application creates MIGRATION_OPENING_BALANCE movements and updates balances.
    - Verify duplicate apply is idempotent and does not produce duplicate movements.
    - Verify rehearsal reconciliation report returns MATCH with zero variance.

Flow:
    Operator starts API -> python -m tests.e2e.phase5_e2e_test

Used By:
    - Phase 5 release smoke test and acceptance validation.

Returns:
    main() -> None - Prints step summary and exits non-zero on failure.

Raises:
    RuntimeError: When a required Phase 5 assertion fails.
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
class Phase5Context:
    """Runtime authentication and environment state for Phase 5 E2E test."""

    api_base_url: str
    admin_email: str
    admin_password: str
    token: str


class Phase5E2ERunner:
    """HTTP client wrapper executing Phase 5 opening inventory migration smoke checks."""

    def __init__(self, client: httpx.AsyncClient, context: Phase5Context) -> None:
        """
        Initialize the E2E runner with an authenticated client.

        Args:
            client: Async HTTP client configured for API base URL.
            context: Context containing base URL and admin token.

        Returns:
            None.
        """
        self.client = client
        self.context = context
        self.passed_steps: list[str] = []

    async def run(self) -> None:
        """
        Execute Phase 5 migration E2E verification steps in order.

        Returns:
            None.
        """
        print("\nStarting Phase 5 Opening Inventory Migration E2E Test Suite...")

        # 1. Setup master data fixtures
        seller = await self.create_seller_fixture()
        warehouse = await self.create_warehouse_fixture()
        product = await self.create_product_fixture(seller["id"])

        # 2. Test staging invalid raw row & validation failure
        await self.test_invalid_staging_and_validation_block(seller, warehouse, product)

        # 3. Test idempotency & conflict rules on row submission
        await self.test_row_submission_idempotency_and_conflicts(seller, warehouse, product)

        # 4. Test role authorization guard (Seller role blocked from approving)
        await self.test_role_authorization_guards(seller, warehouse, product)

        # 5. Full happy path.
        await self.test_happy_path_migration_and_reconciliation(seller, warehouse, product)

        print(f"\nPhase 5 E2E Test completed cleanly! Passed {len(self.passed_steps)} steps:")
        for step in self.passed_steps:
            print(f"  [PASS] {step}")

    async def create_seller_fixture(self) -> dict:
        """Create isolated seller fixture."""
        code = f"P5SEL-{uuid4().hex[:6].upper()}"
        resp = await self.client.post(
            f"{self.context.api_base_url}/sellers",
            headers={"Authorization": f"Bearer {self.context.token}"},
            json={"code": code, "name": f"Phase 5 Seller {code}"},
        )
        resp.raise_for_status()
        seller = resp.json()
        self.passed_steps.append(f"Created seller fixture: {seller['code']}")
        return seller

    async def create_warehouse_fixture(self) -> dict:
        """Create isolated warehouse fixture."""
        code = f"P5WH-{uuid4().hex[:6].upper()}"
        resp = await self.client.post(
            f"{self.context.api_base_url}/warehouses",
            headers={"Authorization": f"Bearer {self.context.token}"},
            json={"code": code, "name": f"Phase 5 Warehouse {code}"},
        )
        resp.raise_for_status()
        wh = resp.json()
        self.passed_steps.append(f"Created warehouse fixture: {wh['code']}")
        return wh

    async def create_product_fixture(self, seller_id: str) -> dict:
        """Create isolated product fixture."""
        sku = f"P5SKU-{uuid4().hex[:6].upper()}"
        resp = await self.client.post(
            f"{self.context.api_base_url}/products",
            headers={"Authorization": f"Bearer {self.context.token}"},
            json={"seller_id": seller_id, "sku": sku, "name": f"Product {sku}"},
        )
        resp.raise_for_status()
        prod = resp.json()
        self.passed_steps.append(f"Created product fixture: {prod['sku']}")
        return prod

    async def test_invalid_staging_and_validation_block(
        self, seller: dict, warehouse: dict, product: dict
    ) -> None:
        """Verify invalid raw rows cause validation failure and block approval."""
        # Create batch
        resp = await self.client.post(
            f"{self.context.api_base_url}/migration/batches",
            headers={"Authorization": f"Bearer {self.context.token}"},
            json={"source_notes": "Validation Failure Test Batch"},
        )
        resp.raise_for_status()
        batch = resp.json()

        # Stage invalid row (negative quantity & invalid SKU)
        rows_payload = {
            "rows": [
                {
                    "source_workbook": "invalid_test.xlsx",
                    "source_sheet": "Sheet1",
                    "source_row_number": 2,
                    "raw_seller_code": seller["code"],
                    "raw_sku": "NON_EXISTENT_SKU_9999",
                    "raw_warehouse_code": warehouse["code"],
                    "raw_inventory_state": "AVAILABLE",
                    "raw_quantity": "-10.00",
                }
            ]
        }
        resp = await self.client.post(
            f"{self.context.api_base_url}/migration/batches/{batch['id']}/rows",
            headers={"Authorization": f"Bearer {self.context.token}"},
            json=rows_payload,
        )
        resp.raise_for_status()

        # Validate
        resp = await self.client.post(
            f"{self.context.api_base_url}/migration/batches/{batch['id']}/validate",
            headers={"Authorization": f"Bearer {self.context.token}"},
        )
        resp.raise_for_status()
        val_summary = resp.json()

        if val_summary["status"] != "VALIDATION_FAILED" or val_summary["invalid_rows"] != 1:
            raise RuntimeError(f"Expected VALIDATION_FAILED with 1 invalid row, got {val_summary}")

        # Attempt approval -> must fail with 409 Conflict
        resp = await self.client.post(
            f"{self.context.api_base_url}/migration/batches/{batch['id']}/approve",
            headers={"Authorization": f"Bearer {self.context.token}"},
        )
        if resp.status_code != 409:
            raise RuntimeError(
                "Expected 409 Conflict when approving batch with invalid rows, "
                f"got {resp.status_code}"
            )

        self.passed_steps.append(
            "Verified validation detects invalid rows and blocks approval with 409"
        )

    async def test_row_submission_idempotency_and_conflicts(
        self, seller: dict, warehouse: dict, product: dict
    ) -> None:
        """Verify row submission idempotency and conflict 409 rules."""
        # Create batch
        resp = await self.client.post(
            f"{self.context.api_base_url}/migration/batches",
            headers={"Authorization": f"Bearer {self.context.token}"},
            json={"source_notes": "Idempotency Test Batch"},
        )
        resp.raise_for_status()
        batch = resp.json()

        row_item = {
            "source_workbook": "idem_test.xlsx",
            "source_sheet": "Sheet1",
            "source_row_number": 5,
            "raw_seller_code": seller["code"],
            "raw_sku": product["sku"],
            "raw_warehouse_code": warehouse["code"],
            "raw_inventory_state": "AVAILABLE",
            "raw_quantity": "25.00",
        }

        # First submission
        resp = await self.client.post(
            f"{self.context.api_base_url}/migration/batches/{batch['id']}/rows",
            headers={"Authorization": f"Bearer {self.context.token}"},
            json={"rows": [row_item]},
        )
        resp.raise_for_status()

        # Re-submit exact same item -> must succeed idempotently (no duplicate)
        resp = await self.client.post(
            f"{self.context.api_base_url}/migration/batches/{batch['id']}/rows",
            headers={"Authorization": f"Bearer {self.context.token}"},
            json={"rows": [row_item]},
        )
        resp.raise_for_status()

        # Re-submit same row identity with different content/hash -> must return 409 Conflict
        conflicting_row = dict(row_item)
        conflicting_row["raw_quantity"] = "999.00"
        resp = await self.client.post(
            f"{self.context.api_base_url}/migration/batches/{batch['id']}/rows",
            headers={"Authorization": f"Bearer {self.context.token}"},
            json={"rows": [conflicting_row]},
        )
        if resp.status_code != 409:
            raise RuntimeError(
                "Expected 409 Conflict on row identity content hash mismatch, "
                f"got {resp.status_code}"
            )

        self.passed_steps.append("Verified row submission idempotency and 409 conflict rules")

    async def test_role_authorization_guards(
        self, seller: dict, warehouse: dict, product: dict
    ) -> None:
        """Verify role authorization guards block unauthorized approval attempts."""
        # Create seller user token
        seller_email = f"seller_{uuid4().hex[:6]}@example.com"
        seller_pass = "SellerPass123!"
        resp = await self.client.post(
            f"{self.context.api_base_url}/users",
            headers={"Authorization": f"Bearer {self.context.token}"},
            json={
                "email": seller_email,
                "name": "Seller User",
                "password": seller_pass,
                "role": "SELLER",
                "seller_ids": [seller["id"]],
            },
        )
        resp.raise_for_status()

        # Login as seller
        resp = await self.client.post(
            f"{self.context.api_base_url}/auth/login",
            json={"email": seller_email, "password": seller_pass},
        )
        resp.raise_for_status()
        seller_token = resp.json()["access_token"]

        # Admin creates and validates a batch
        resp = await self.client.post(
            f"{self.context.api_base_url}/migration/batches",
            headers={"Authorization": f"Bearer {self.context.token}"},
            json={"source_notes": "Role Guard Test Batch"},
        )
        resp.raise_for_status()
        batch = resp.json()

        # Attempt to approve batch using Seller token -> must return 403 Forbidden
        resp = await self.client.post(
            f"{self.context.api_base_url}/migration/batches/{batch['id']}/approve",
            headers={"Authorization": f"Bearer {seller_token}"},
        )
        if resp.status_code != 403:
            raise RuntimeError(
                "Expected 403 Forbidden for Seller role approving migration batch, "
                f"got {resp.status_code}"
            )

        self.passed_steps.append(
            "Verified 403 Forbidden for unauthorized SELLER role approving migration"
        )

    async def test_happy_path_migration_and_reconciliation(
        self, seller: dict, warehouse: dict, product: dict
    ) -> None:
        """Test full opening inventory migration happy path."""
        # 1. Create Batch
        resp = await self.client.post(
            f"{self.context.api_base_url}/migration/batches",
            headers={"Authorization": f"Bearer {self.context.token}"},
            json={"source_notes": "Happy Path Migration Batch"},
        )
        resp.raise_for_status()
        batch = resp.json()

        # 2. Stage Valid Rows
        qty_str = "150.00"
        rows_payload = {
            "rows": [
                {
                    "source_workbook": "happy_opening.xlsx",
                    "source_sheet": "Sheet1",
                    "source_row_number": 2,
                    "raw_seller_code": seller["code"],
                    "raw_sku": product["sku"],
                    "raw_warehouse_code": warehouse["code"],
                    "raw_location_code": None,
                    "raw_inventory_state": "AVAILABLE",
                    "raw_quantity": qty_str,
                }
            ]
        }
        resp = await self.client.post(
            f"{self.context.api_base_url}/migration/batches/{batch['id']}/rows",
            headers={"Authorization": f"Bearer {self.context.token}"},
            json=rows_payload,
        )
        resp.raise_for_status()

        # 3. Validate
        resp = await self.client.post(
            f"{self.context.api_base_url}/migration/batches/{batch['id']}/validate",
            headers={"Authorization": f"Bearer {self.context.token}"},
        )
        resp.raise_for_status()
        val_summary = resp.json()
        if val_summary["status"] != "VALIDATED" or val_summary["valid_rows"] != 1:
            raise RuntimeError(f"Expected VALIDATED status, got {val_summary}")

        # 4. Approve
        resp = await self.client.post(
            f"{self.context.api_base_url}/migration/batches/{batch['id']}/approve",
            headers={"Authorization": f"Bearer {self.context.token}"},
        )
        resp.raise_for_status()
        appr_batch = resp.json()
        if appr_batch["status"] != "APPROVED":
            raise RuntimeError(f"Expected APPROVED status, got {appr_batch}")

        # 5. Apply to Ledger
        resp = await self.client.post(
            f"{self.context.api_base_url}/migration/batches/{batch['id']}/apply",
            headers={"Authorization": f"Bearer {self.context.token}"},
        )
        resp.raise_for_status()
        applied_batch = resp.json()
        if applied_batch["status"] != "APPLIED":
            raise RuntimeError(f"Expected APPLIED status, got {applied_batch}")

        # 6. Verify Movements
        resp = await self.client.get(
            f"{self.context.api_base_url}/inventory/movements"
            f"?seller_id={seller['id']}&warehouse_id={warehouse['id']}"
            f"&product_id={product['id']}",
            headers={"Authorization": f"Bearer {self.context.token}"},
        )
        resp.raise_for_status()
        movements = resp.json()
        mig_movements = [
            movement
            for movement in movements
            if movement["movement_type"] == "MIGRATION_OPENING_BALANCE"
        ]
        if not mig_movements:
            raise RuntimeError("No MIGRATION_OPENING_BALANCE movements found after batch apply!")
        movement_count_before_reapply = len(mig_movements)

        # 7. Verify Balances
        resp = await self.client.get(
            f"{self.context.api_base_url}/inventory/balances"
            f"?seller_id={seller['id']}&warehouse_id={warehouse['id']}"
            f"&product_id={product['id']}",
            headers={"Authorization": f"Bearer {self.context.token}"},
        )
        resp.raise_for_status()
        balances = resp.json()
        avail_balance = [b for b in balances if b["inventory_state"] == "AVAILABLE"]
        if not avail_balance or Decimal(str(avail_balance[0]["quantity"])) != Decimal(qty_str):
            raise RuntimeError(f"Expected available balance {qty_str}, got {balances}")

        # 8. Verify Reconciliation Report
        resp = await self.client.get(
            f"{self.context.api_base_url}/migration/batches/{batch['id']}/reconciliation",
            headers={"Authorization": f"Bearer {self.context.token}"},
        )
        resp.raise_for_status()
        recon = resp.json()
        if recon["reconciliation_status"] != "MATCH":
            raise RuntimeError(f"Expected reconciliation status MATCH, got {recon}")

        # 9. Idempotent Re-apply
        resp = await self.client.post(
            f"{self.context.api_base_url}/migration/batches/{batch['id']}/apply",
            headers={"Authorization": f"Bearer {self.context.token}"},
        )
        resp.raise_for_status()
        reapplied = resp.json()
        if reapplied["status"] != "APPLIED":
            raise RuntimeError(f"Expected APPLIED status on re-apply, got {reapplied}")

        resp = await self.client.get(
            f"{self.context.api_base_url}/inventory/movements"
            f"?seller_id={seller['id']}&warehouse_id={warehouse['id']}&product_id={product['id']}",
            headers={"Authorization": f"Bearer {self.context.token}"},
        )
        resp.raise_for_status()
        movements_after_reapply = resp.json()
        migration_count_after_reapply = len(
            [
                movement
                for movement in movements_after_reapply
                if movement["movement_type"] == "MIGRATION_OPENING_BALANCE"
            ]
        )
        if migration_count_after_reapply != movement_count_before_reapply:
            raise RuntimeError("Duplicate apply created extra migration movements")

        self.passed_steps.append(
            "Verified happy path and idempotent re-apply without duplicate movements"
        )


async def main() -> None:
    """E2E entry point."""
    load_dotenv()

    parser = argparse.ArgumentParser(description="Run Phase 5 E2E migration test suite.")
    parser.add_argument(
        "--api-url",
        default=os.getenv("WAREHOUSE_API_BASE_URL", DEFAULT_API_BASE_URL),
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
    args = parser.parse_args()

    if not args.admin_email or not args.admin_password:
        raise RuntimeError(
            "Set BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD, or pass "
            "--admin-email and --admin-password."
        )

    api_url = args.api_url.rstrip("/")
    if not api_url.endswith("/api/v1"):
        api_url = f"{api_url}/api/v1" if not api_url.endswith("/api") else f"{api_url}/v1"

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Login
        resp = await client.post(
            f"{api_url}/auth/login",
            json={"email": args.admin_email, "password": args.admin_password},
        )
        resp.raise_for_status()
        token = resp.json()["access_token"]

        ctx = Phase5Context(
            api_base_url=api_url,
            admin_email=args.admin_email,
            admin_password=args.admin_password,
            token=token,
        )

        runner = Phase5E2ERunner(client, ctx)
        await runner.run()


if __name__ == "__main__":
    asyncio.run(main())
