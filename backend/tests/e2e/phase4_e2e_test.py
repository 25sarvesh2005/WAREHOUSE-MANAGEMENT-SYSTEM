"""
--------------------------------------------------------------------------------
File        : tests/e2e/phase4_e2e_test.py
Purpose     : Run Phase 4 live API verification against a configured backend.

Responsibilities:
    - Verify transfer dispatch, variance receipt, and discrepancy resolution.
    - Verify return intake, inspection, and disposition accounting.
    - Verify seller portal endpoints with a real seller-scoped user token.
    - Verify cross-seller seller portal access is blocked.
    - Verify manager dashboard, exception, and reconciliation report endpoints.
    - Keep E2E execution opt-in so normal pytest runs do not mutate live data.

Flow:
    Operator starts API
        ->
    python -m tests.e2e.phase4_e2e_test
        ->
    Script authenticates, creates isolated smoke records, and validates Phase 4

Used By:
    - Manual Phase 4 acceptance validation.
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
class Phase4Context:
    """Runtime authentication and warehouse state for one Phase 4 smoke run."""

    api_base_url: str
    admin_email: str
    admin_password: str
    origin_warehouse_id: str
    destination_warehouse_id: str
    token: str


@dataclass(frozen=True)
class SellerUserFixture:
    """Seller tenant plus a seller-scoped login for portal validation."""

    seller_id: str
    email: str
    password: str


class Phase4E2ERunner:
    """HTTP client wrapper for the Phase 4 transfer, return, and visibility smoke test."""

    def __init__(self, client: httpx.AsyncClient, context: Phase4Context) -> None:
        """
        Initialize the E2E runner with an authenticated administrator client.

        Args:
            client: Async HTTP client configured for the API base URL.
            context: Runtime authentication and warehouse IDs.

        Returns:
            None.
        """
        self.client = client
        self.context = context
        self.passed_steps: list[str] = []

    async def run(self) -> None:
        """
        Execute all Phase 4 E2E smoke checks in deterministic order.

        Returns:
            None.

        Raises:
            RuntimeError: If a Phase 4 acceptance behavior fails.
            httpx.HTTPStatusError: If an unexpected API response is returned.
        """
        seller = await self.create_seller_user_fixture("PRIMARY")
        other_seller = await self.create_seller_user_fixture("OTHER")
        product = await self.create_product(seller.seller_id, "TRANSFER")
        other_product = await self.create_product(other_seller.seller_id, "OTHER")

        await self.receive_available_units(seller.seller_id, product["id"], 10)
        await self.create_order(seller.seller_id, product["id"], 1, "PORTAL")
        await self.create_order(other_seller.seller_id, other_product["id"], 1, "OTHER")

        await self.verify_transfer_workflow(seller.seller_id, product["id"])
        await self.verify_return_workflow(seller.seller_id, product["id"])
        await self.verify_seller_portal_scope(seller, other_seller.seller_id)
        await self.verify_manager_reporting()

    async def create_seller_user_fixture(self, label: str) -> SellerUserFixture:
        """
        Create an isolated seller plus a seller-scoped user assignment.

        Args:
            label: Short fixture label for generated codes and emails.

        Returns:
            SellerUserFixture: Seller tenant and login credentials.

        Raises:
            httpx.HTTPStatusError: If any fixture setup call fails.
        """
        suffix = uuid4().hex[:10].upper()
        seller_response = await self.client.post(
            "/sellers",
            json={
                "code": f"P4{label[:3]}{suffix}",
                "name": f"Phase 4 {label} Seller {suffix}",
                "contact_email": f"phase4-{label.lower()}-{suffix.lower()}@whitfield.local",
                "status": "ACTIVE",
            },
        )
        seller_response.raise_for_status()
        seller = seller_response.json()

        email = f"phase4-{label.lower()}-seller-{suffix.lower()}@whitfield.local"
        password = f"Phase4-{suffix}!"
        user_response = await self.client.post(
            "/users",
            json={
                "email": email,
                "name": f"Phase 4 {label} Seller User",
                "password": password,
                "role": "SELLER",
                "status": "ACTIVE",
            },
        )
        user_response.raise_for_status()
        user = user_response.json()

        assignment_response = await self.client.post(
            "/assignments/sellers",
            json={
                "user_id": user["id"],
                "seller_id": seller["id"],
                "assignment_role": "SELLER",
            },
        )
        assignment_response.raise_for_status()
        return SellerUserFixture(seller_id=seller["id"], email=email, password=password)

    async def create_product(self, seller_id: str, label: str) -> dict:
        """
        Create a unique product owned by the supplied seller.

        Args:
            seller_id: Seller UUID that owns the product.
            label: Short fixture label for generated SKU/name.

        Returns:
            dict: Product response payload.

        Raises:
            httpx.HTTPStatusError: If product creation fails.
        """
        sku = f"PHASE4-{label}-{uuid4().hex[:8].upper()}"
        response = await self.client.post(
            "/products",
            json={
                "seller_id": seller_id,
                "sku": sku,
                "name": f"Phase 4 {label} Product {sku}",
                "unit_of_measure": "EA",
                "status": "ACTIVE",
            },
        )
        response.raise_for_status()
        return response.json()

    async def create_order(
        self,
        seller_id: str,
        product_id: str,
        quantity: int,
        label: str,
    ) -> dict:
        """
        Create a customer order so seller portal order lists are meaningful.

        Args:
            seller_id: Seller UUID that owns the order.
            product_id: Product UUID on the order line.
            quantity: Ordered quantity.
            label: Short fixture label for seller order number.

        Returns:
            dict: Created order response payload.

        Raises:
            httpx.HTTPStatusError: If order creation fails.
        """
        response = await self.client.post(
            "/orders",
            json={
                "seller_id": seller_id,
                "warehouse_id": self.context.origin_warehouse_id,
                "seller_order_number": f"P4-{label}-{uuid4().hex[:10].upper()}",
                "channel": "DIRECT",
                "lines": [{"product_id": product_id, "ordered_quantity": quantity}],
            },
        )
        response.raise_for_status()
        return response.json()

    async def receive_available_units(
        self,
        seller_id: str,
        product_id: str,
        quantity: int,
    ) -> None:
        """
        Complete an inbound receipt posting all units to AVAILABLE inventory.

        Args:
            seller_id: Seller UUID that owns the receipt/product.
            product_id: Product UUID being received.
            quantity: Available units to receive.

        Returns:
            None.

        Raises:
            RuntimeError: If the receipt is not completed.
            httpx.HTTPStatusError: If an unexpected API call fails.
        """
        receipt_response = await self.client.post(
            "/receipts",
            json={
                "seller_id": seller_id,
                "warehouse_id": self.context.origin_warehouse_id,
                "source_type": "CARRIER_TRACKING",
                "source_reference": f"PHASE4-RCV-{uuid4().hex[:10].upper()}",
            },
        )
        receipt_response.raise_for_status()
        receipt = receipt_response.json()

        line_response = await self.client.post(
            f"/receipts/{receipt['id']}/lines",
            json={
                "product_id": product_id,
                "expected_quantity": quantity,
                "sellable_quantity": quantity,
            },
        )
        line_response.raise_for_status()

        complete_response = await self.client.post(
            f"/receipts/{receipt['id']}/complete",
            json={"notes": "Phase 4 E2E receipt completion."},
        )
        complete_response.raise_for_status()
        completed = complete_response.json()
        if completed["status"] != "COMPLETED":
            raise RuntimeError(f"Expected COMPLETED receipt, got {completed['status']}.")

    async def verify_transfer_workflow(self, seller_id: str, product_id: str) -> None:
        """
        Verify transfer approve, dispatch, discrepancy receive, and resolution.

        Args:
            seller_id: Seller UUID owning transferred stock.
            product_id: Product UUID to transfer.

        Returns:
            None.

        Raises:
            RuntimeError: If transfer lifecycle or balance assertions fail.
            httpx.HTTPStatusError: If an unexpected API call fails.
        """
        transfer_response = await self.client.post(
            "/transfers",
            json={
                "seller_id": seller_id,
                "origin_warehouse_id": self.context.origin_warehouse_id,
                "destination_warehouse_id": self.context.destination_warehouse_id,
                "notes": "Phase 4 E2E stock relocation.",
                "lines": [{"product_id": product_id, "requested_quantity": 10}],
            },
        )
        transfer_response.raise_for_status()
        transfer = transfer_response.json()

        approved = await self.post_and_read(f"/transfers/{transfer['id']}/approve", {})
        if approved["status"] != "APPROVED":
            raise RuntimeError(f"Expected APPROVED transfer, got {approved['status']}.")

        dispatched = await self.post_and_read(f"/transfers/{transfer['id']}/dispatch", {})
        if dispatched["status"] != "DISPATCHED":
            raise RuntimeError(f"Expected DISPATCHED transfer, got {dispatched['status']}.")

        in_transit = await self.get_balance_quantity(seller_id, product_id, "IN_TRANSIT")
        if in_transit != Decimal("10.00"):
            raise RuntimeError(f"Expected IN_TRANSIT=10.00 after dispatch, got {in_transit}.")

        line_id = dispatched["lines"][0]["id"]
        received = await self.post_and_read(
            f"/transfers/{transfer['id']}/receive",
            {
                "lines": [
                    {
                        "line_id": line_id,
                        "received_good_quantity": 8,
                        "received_damaged_quantity": 1,
                    }
                ]
            },
        )
        if received["status"] != "DISCREPANCY_REVIEW":
            raise RuntimeError(f"Expected DISCREPANCY_REVIEW, got {received['status']}.")

        resolved = await self.post_and_read(
            f"/transfers/{transfer['id']}/resolve-discrepancy",
            {"notes": "Phase 4 E2E carrier variance reviewed."},
        )
        if resolved["status"] != "RECEIVED":
            raise RuntimeError(f"Expected RECEIVED after resolution, got {resolved['status']}.")

        self.mark_passed("Transfer workflow handles dispatch, variance, and resolution")

    async def verify_return_workflow(self, seller_id: str, product_id: str) -> None:
        """
        Verify return intake, inspection, and disposition accounting workflow.

        Args:
            seller_id: Seller UUID owning the return.
            product_id: Product UUID being returned.

        Returns:
            None.

        Raises:
            RuntimeError: If return lifecycle assertions fail.
            httpx.HTTPStatusError: If an unexpected API call fails.
        """
        return_response = await self.client.post(
            "/returns",
            json={
                "seller_id": seller_id,
                "warehouse_id": self.context.destination_warehouse_id,
                "rma_number": f"RMA-{uuid4().hex[:8].upper()}",
                "inbound_tracking_number": f"TRK-{uuid4().hex[:8].upper()}",
                "notes": "Phase 4 E2E customer return.",
                "lines": [{"product_id": product_id, "expected_quantity": 5}],
            },
        )
        return_response.raise_for_status()
        return_order = return_response.json()
        return_line_id = return_order["lines"][0]["id"]

        received = await self.post_and_read(
            f"/returns/{return_order['id']}/receive",
            {"lines": [{"line_id": return_line_id, "received_quantity": 5}]},
        )
        if received["status"] != "INSPECTION":
            raise RuntimeError(f"Expected INSPECTION return, got {received['status']}.")

        inspected = await self.post_and_read(
            f"/returns/{return_order['id']}/inspect",
            {
                "dispositions": [
                    {
                        "return_line_id": return_line_id,
                        "disposition_state": "RESTOCKED",
                        "quantity": 3,
                        "notes": "Resellable unopened condition.",
                    },
                    {
                        "return_line_id": return_line_id,
                        "disposition_state": "DAMAGED",
                        "quantity": 2,
                        "notes": "Crushed retail packaging.",
                    },
                ]
            },
        )
        if inspected["status"] != "COMPLETED":
            raise RuntimeError(f"Expected COMPLETED return, got {inspected['status']}.")

        self.mark_passed("Return workflow handles intake, inspection, and disposition")

    async def verify_seller_portal_scope(
        self,
        seller: SellerUserFixture,
        other_seller_id: str,
    ) -> None:
        """
        Verify seller portal endpoints with seller token and cross-seller denial.

        Args:
            seller: Seller-scoped login fixture.
            other_seller_id: Seller UUID that the seller token must not access.

        Returns:
            None.

        Raises:
            RuntimeError: If seller endpoints fail or leak another seller.
            httpx.HTTPStatusError: If seller login fails unexpectedly.
        """
        async with httpx.AsyncClient(base_url=self.context.api_base_url, timeout=30.0) as client:
            token_response = await client.post(
                "/auth/login",
                json={"email": seller.email, "password": seller.password},
            )
            token_response.raise_for_status()
            client.headers.update(
                {"Authorization": f"Bearer {token_response.json()['access_token']}"}
            )

            await self.assert_seller_rows(client, "/seller/inventory", seller.seller_id)
            await self.assert_seller_rows(client, "/seller/orders", seller.seller_id)
            await self.assert_seller_rows(client, "/seller/receipts", seller.seller_id)
            await self.assert_seller_rows(client, "/seller/returns", seller.seller_id)
            await self.assert_seller_rows(client, "/seller/transfers", seller.seller_id)

            shipments_response = await client.get("/seller/shipments")
            shipments_response.raise_for_status()

            denied_response = await client.get(
                "/seller/inventory",
                params={"seller_id": other_seller_id},
            )
            if denied_response.status_code != 403:
                raise RuntimeError(
                    "Expected cross-seller seller portal request to return HTTP 403, "
                    f"got {denied_response.status_code}: {denied_response.text}"
                )

        self.mark_passed("Seller portal uses real seller scope and blocks cross-seller access")

    async def assert_seller_rows(
        self,
        client: httpx.AsyncClient,
        path: str,
        seller_id: str,
    ) -> None:
        """
        Assert a seller portal list endpoint succeeds and returns only one seller.

        Args:
            client: Authenticated seller HTTP client.
            path: Seller portal list endpoint path.
            seller_id: Expected seller UUID.

        Returns:
            None.

        Raises:
            RuntimeError: If the endpoint leaks a different seller ID.
            httpx.HTTPStatusError: If the endpoint fails.
        """
        response = await client.get(path)
        response.raise_for_status()
        rows = response.json()
        for row in rows:
            if str(row.get("seller_id")) != seller_id:
                raise RuntimeError(f"{path} leaked seller row: {row}")

    async def verify_manager_reporting(self) -> None:
        """
        Verify manager dashboard, exception queue, and reconciliation report APIs.

        Returns:
            None.

        Raises:
            RuntimeError: If reporting payloads are missing required fields.
            httpx.HTTPStatusError: If an unexpected API call fails.
        """
        dashboard_response = await self.client.get("/manager/dashboard")
        dashboard_response.raise_for_status()
        dashboard = dashboard_response.json()
        required_dashboard_keys = {
            "balances_by_state",
            "open_receipts_count",
            "pending_pick_tasks_count",
            "active_transfers_count",
            "uninspected_returns_count",
        }
        if not required_dashboard_keys.issubset(dashboard):
            raise RuntimeError(f"Manager dashboard payload missing keys: {dashboard}.")

        exceptions_response = await self.client.get("/manager/exceptions")
        exceptions_response.raise_for_status()
        exceptions = exceptions_response.json()
        required_exception_keys = {
            "short_pick_exceptions",
            "transfer_discrepancies",
            "unidentified_returns",
        }
        if not required_exception_keys.issubset(exceptions):
            raise RuntimeError(f"Manager exception payload missing keys: {exceptions}.")

        reconciliation_response = await self.client.get("/reports/inventory-reconciliation")
        reconciliation_response.raise_for_status()
        reconciliation = reconciliation_response.json()
        if reconciliation.get("is_clean") is not True:
            raise RuntimeError(f"Expected clean reconciliation report, got {reconciliation}.")

        self.mark_passed("Manager reporting and reconciliation endpoints return live data")

    async def get_balance_quantity(
        self,
        seller_id: str,
        product_id: str,
        inventory_state: str,
    ) -> Decimal:
        """
        Read one inventory balance quantity for a product/state.

        Args:
            seller_id: Seller UUID filter.
            product_id: Product UUID filter.
            inventory_state: Inventory state to read.

        Returns:
            Decimal: Balance quantity or zero when no projection row exists.

        Raises:
            httpx.HTTPStatusError: If balance query fails.
        """
        response = await self.client.get(
            "/inventory/balances",
            params={
                "seller_id": seller_id,
                "product_id": product_id,
                "inventory_state": inventory_state,
                "limit": 200,
            },
        )
        response.raise_for_status()
        return sum(Decimal(str(row["quantity"])) for row in response.json())

    async def post_and_read(self, path: str, payload: dict) -> dict:
        """
        POST a JSON payload and return the parsed JSON response.

        Args:
            path: API endpoint path relative to the configured base URL.
            payload: JSON payload dictionary.

        Returns:
            dict: Parsed JSON response.

        Raises:
            httpx.HTTPStatusError: If the API call fails.
        """
        response = await self.client.post(path, json=payload)
        response.raise_for_status()
        return response.json()

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
) -> Phase4Context:
    """
    Authenticate and select two warehouses for Phase 4 transfer smoke records.

    Args:
        client: Async HTTP client configured for the API base URL.
        api_base_url: API base URL used for nested seller-token clients.
        admin_email: Admin email for login.
        admin_password: Admin password for login.

    Returns:
        Phase4Context: Authenticated runtime context.

    Raises:
        RuntimeError: If fewer than two warehouses are available.
        httpx.HTTPStatusError: If login or warehouse loading fails.
    """
    token_response = await client.post(
        "/auth/login",
        json={"email": admin_email, "password": admin_password},
    )
    token_response.raise_for_status()
    token = token_response.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})

    warehouses_response = await client.get("/warehouses")
    warehouses_response.raise_for_status()
    warehouses = warehouses_response.json()
    if len(warehouses) < 2:
        raise RuntimeError("Phase 4 E2E requires at least two configured warehouses.")

    return Phase4Context(
        api_base_url=api_base_url,
        admin_email=admin_email,
        admin_password=admin_password,
        origin_warehouse_id=warehouses[0]["id"],
        destination_warehouse_id=warehouses[1]["id"],
        token=token,
    )


def build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line argument parser for Phase 4 E2E execution.

    Returns:
        argparse.ArgumentParser: Configured parser.
    """
    parser = argparse.ArgumentParser(
        description="Run Phase 4 transfers, returns, and visibility E2E smoke test."
    )
    parser.add_argument(
        "--api-base-url",
        default=os.getenv("PHASE4_E2E_API_BASE_URL", DEFAULT_API_BASE_URL),
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
    Load configuration and run the Phase 4 E2E smoke test.

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
        runner = Phase4E2ERunner(client, context)
        await runner.run()
        print(f"\nPhase 4 E2E complete: {len(runner.passed_steps)} / 4 checks passed.")


def main() -> None:
    """
    Run the async Phase 4 E2E entrypoint from a synchronous CLI boundary.

    Returns:
        None.
    """
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
