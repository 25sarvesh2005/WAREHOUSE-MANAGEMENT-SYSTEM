"""
--------------------------------------------------------------------------------
File        : tests/e2e/phase3_e2e_test.py
Purpose     : Run Phase 3 live API smoke verification against a configured backend.

Responsibilities:
    - Verify concurrent order reservation cannot oversell the final available units.
    - Verify seller policy snapshots and strict no-partial reservation outcomes.
    - Verify short-pick exception handling returns shorted units to AVAILABLE.
    - Verify the reservation expiry job releases expired reservations idempotently.
    - Compare Phase 3 smoke-product balances to inventory movement ledger totals.

Flow:
    Operator starts API
        ->
    python -m tests.e2e.phase3_e2e_test
        ->
    Script authenticates and creates unique smoke records
        ->
    Script verifies Phase 3 acceptance behaviors

Used By:
    - Manual Phase 3 acceptance validation.
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
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import httpx
from dotenv import load_dotenv
from sqlalchemy import select

from core.models import audit_model, catalog_model, fulfillment_model, identity_model
from core.models import inventory_model, outbox_model, receiving_model, return_model
from core.models import transfer_model
from core.database.database import (
    close_database_connection,
    connect_to_database,
    transaction_session,
)
from core.jobs.reservation_expiry_job import release_expired_reservations
from core.models.order_model import InventoryReservation

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000/api/v1"
SQLALCHEMY_MODEL_MODULES = (
    audit_model,
    catalog_model,
    fulfillment_model,
    identity_model,
    inventory_model,
    outbox_model,
    receiving_model,
    return_model,
    transfer_model,
)


@dataclass(frozen=True)
class Phase3Context:
    """Runtime IDs and authentication state for one Phase 3 smoke run."""

    api_base_url: str
    admin_email: str
    admin_password: str
    warehouse_id: str
    token: str


@dataclass(frozen=True)
class SellerFixture:
    """Seller and policy identifiers created for isolated Phase 3 checks."""

    seller_id: str
    policy_id: str


class Phase3E2ERunner:
    """HTTP client wrapper for the Phase 3 order and fulfillment smoke test."""

    def __init__(self, client: httpx.AsyncClient, context: Phase3Context) -> None:
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
        self.reconcile_product_ids: list[tuple[str, str]] = []

    async def run(self) -> None:
        """
        Execute all Phase 3 E2E smoke checks in deterministic order.

        Returns:
            None.

        Raises:
            RuntimeError: If a Phase 3 acceptance behavior fails.
            httpx.HTTPStatusError: If an unexpected API response is returned.
        """
        partial_seller = await self.create_seller_with_policy(
            allow_backorder=True,
            allow_partial_fulfillment=True,
            reservation_expiry_minutes=5,
        )
        strict_seller = await self.create_seller_with_policy(
            allow_backorder=True,
            allow_partial_fulfillment=False,
            reservation_expiry_minutes=5,
        )
        concurrency_product = await self.create_smoke_product(
            partial_seller.seller_id,
            "CONCURRENCY",
        )
        await self.receive_available_units(partial_seller.seller_id, concurrency_product["id"], 10)
        await self.verify_concurrent_reservation(partial_seller, concurrency_product["id"])

        strict_product = await self.create_smoke_product(strict_seller.seller_id, "STRICT")
        await self.receive_available_units(strict_seller.seller_id, strict_product["id"], 3)
        await self.verify_strict_partial_policy(strict_seller, strict_product["id"])

        expiry_product = await self.create_smoke_product(partial_seller.seller_id, "EXPIRY")
        await self.receive_available_units(partial_seller.seller_id, expiry_product["id"], 4)
        await self.verify_reservation_expiry_job(partial_seller.seller_id, expiry_product["id"])

        await self.verify_product_ledger_reconciliation()

    async def create_seller_with_policy(
        self,
        allow_backorder: bool,
        allow_partial_fulfillment: bool,
        reservation_expiry_minutes: int,
    ) -> SellerFixture:
        """
        Create an isolated seller and explicit order policy for test determinism.

        Args:
            allow_backorder: Whether the seller policy allows backorders.
            allow_partial_fulfillment: Whether partial reservations are allowed.
            reservation_expiry_minutes: Reservation expiry duration in minutes.

        Returns:
            SellerFixture: Created seller and policy identifiers.

        Raises:
            httpx.HTTPStatusError: If seller or policy creation fails.
        """
        suffix = uuid4().hex[:10].upper()
        seller_response = await self.client.post(
            "/sellers",
            json={
                "code": f"P3{suffix}",
                "name": f"Phase 3 E2E Seller {suffix}",
                "contact_email": f"phase3-{suffix.lower()}@whitfield.local",
                "status": "ACTIVE",
            },
        )
        seller_response.raise_for_status()
        seller = seller_response.json()

        policy_response = await self.client.post(
            "/seller-order-policies",
            json={
                "seller_id": seller["id"],
                "allow_backorder": allow_backorder,
                "allow_partial_fulfillment": allow_partial_fulfillment,
                "reservation_expiry_minutes": reservation_expiry_minutes,
                "allocation_strategy": "FIFO",
                "cancellation_policy": "Phase 3 E2E smoke policy.",
            },
        )
        policy_response.raise_for_status()
        policy = policy_response.json()
        return SellerFixture(seller_id=seller["id"], policy_id=policy["id"])

    async def create_smoke_product(self, seller_id: str, label: str) -> dict:
        """
        Create a unique seller product for isolated order/balance assertions.

        Args:
            seller_id: Seller UUID that owns the product.
            label: Short label included in the SKU and product name.

        Returns:
            dict: Created product response payload.

        Raises:
            httpx.HTTPStatusError: If product creation fails.
        """
        sku = f"PHASE3-{label}-{uuid4().hex[:8].upper()}"
        response = await self.client.post(
            "/products",
            json={
                "seller_id": seller_id,
                "sku": sku,
                "name": f"Phase 3 E2E {label} SKU {sku}",
                "unit_of_measure": "EA",
                "status": "ACTIVE",
            },
        )
        response.raise_for_status()
        product = response.json()
        self.reconcile_product_ids.append((seller_id, product["id"]))
        return product

    async def receive_available_units(
        self,
        seller_id: str,
        product_id: str,
        quantity: int,
    ) -> None:
        """
        Complete a receipt that posts all units to AVAILABLE inventory.

        Args:
            seller_id: Seller UUID that owns the product.
            product_id: Product UUID being received.
            quantity: Available quantity to post.

        Returns:
            None.

        Raises:
            RuntimeError: If the receipt does not complete successfully.
            httpx.HTTPStatusError: If an unexpected API response is returned.
        """
        source_reference = f"PHASE3-RCV-{uuid4().hex[:10].upper()}"
        receipt_response = await self.client.post(
            "/receipts",
            json={
                "seller_id": seller_id,
                "warehouse_id": self.context.warehouse_id,
                "source_type": "CARRIER_TRACKING",
                "source_reference": source_reference,
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
                "notes": "Phase 3 E2E available-stock receipt.",
            },
        )
        line_response.raise_for_status()
        complete_response = await self.client.post(
            f"/receipts/{receipt['id']}/complete",
            json={"notes": "Phase 3 E2E completion."},
        )
        complete_response.raise_for_status()
        completed = complete_response.json()
        if completed["status"] != "COMPLETED":
            raise RuntimeError(f"Expected completed receipt, got {completed['status']}.")

    async def verify_concurrent_reservation(
        self,
        seller: SellerFixture,
        product_id: str,
    ) -> None:
        """
        Verify two competing reservations cannot oversell the final stock.

        Args:
            seller: Seller fixture using partial-fulfillment policy.
            product_id: Product UUID with exactly ten available units.

        Returns:
            None.

        Raises:
            RuntimeError: If reservation status or balance assertions fail.
            httpx.HTTPStatusError: If an unexpected API response is returned.
        """
        order_a = await self.create_order(seller.seller_id, product_id, 7, "A")
        order_b = await self.create_order(seller.seller_id, product_id, 7, "B")

        response_a, response_b = await asyncio.gather(
            self.client.post(f"/orders/{order_a['id']}/reserve", json={}),
            self.client.post(f"/orders/{order_b['id']}/reserve", json={}),
        )
        response_a.raise_for_status()
        response_b.raise_for_status()
        reserved_orders = [response_a.json(), response_b.json()]
        statuses = {order["status"] for order in reserved_orders}
        expected_statuses = {"RESERVED", "PARTIALLY_RESERVED"}
        if statuses != expected_statuses:
            raise RuntimeError(f"Unexpected concurrent reservation statuses: {statuses}.")

        partial_order = next(
            order for order in reserved_orders if order["status"] == "PARTIALLY_RESERVED"
        )
        partial_line = partial_order["lines"][0]
        reserved_quantity = Decimal(str(partial_line["reserved_quantity"]))
        backordered_quantity = Decimal(str(partial_line["backordered_quantity"]))
        if reserved_quantity != Decimal("3.00") or backordered_quantity != Decimal("4.00"):
            raise RuntimeError(
                "Expected partial order to reserve 3.00 and backorder 4.00, "
                f"got reserved={reserved_quantity}, backordered={backordered_quantity}."
            )

        available = await self.get_balance_quantity(seller.seller_id, product_id, "AVAILABLE")
        reserved = await self.get_balance_quantity(seller.seller_id, product_id, "RESERVED")
        if available != Decimal("0.00") or reserved != Decimal("10.00"):
            raise RuntimeError(
                "Expected AVAILABLE=0.00 and RESERVED=10.00 after concurrency check, "
                f"got AVAILABLE={available}, RESERVED={reserved}."
            )

        self.mark_passed("Concurrent reservations avoid oversell and preserve backorders")
        full_order = next(order for order in reserved_orders if order["status"] == "RESERVED")
        await self.verify_short_pick_exception(seller.seller_id, product_id, full_order["id"])

    async def verify_short_pick_exception(
        self,
        seller_id: str,
        product_id: str,
        order_id: str,
    ) -> None:
        """
        Verify a short pick releases the shorted RESERVED quantity to AVAILABLE.

        Args:
            seller_id: Seller UUID owning the order.
            product_id: Product UUID on the order.
            order_id: Fully reserved order UUID selected for picking.

        Returns:
            None.

        Raises:
            RuntimeError: If task status or balance assertions fail.
            httpx.HTTPStatusError: If an unexpected API response is returned.
        """
        task_response = await self.client.post(
            "/pick-tasks",
            json={"order_id": order_id, "priority": 1},
        )
        task_response.raise_for_status()
        task = task_response.json()
        task_line = task["lines"][0]

        complete_response = await self.client.post(
            f"/pick-tasks/{task['id']}/complete",
            json={
                "lines": [
                    {
                        "pick_task_line_id": task_line["id"],
                        "picked_quantity": 5,
                        "short_quantity": 2,
                    }
                ]
            },
        )
        complete_response.raise_for_status()
        completed_task = complete_response.json()
        if completed_task["status"] != "SHORT_PICK_EXCEPTION":
            raise RuntimeError(f"Expected SHORT_PICK_EXCEPTION, got {completed_task['status']}.")

        available = await self.get_balance_quantity(seller_id, product_id, "AVAILABLE")
        if available != Decimal("2.00"):
            raise RuntimeError(f"Expected AVAILABLE=2.00 after short pick, got {available}.")

        self.mark_passed("Short-pick exception releases shorted stock to available")

    async def verify_strict_partial_policy(
        self,
        seller: SellerFixture,
        product_id: str,
    ) -> None:
        """
        Verify allow_partial_fulfillment=False backorders the whole deficient order.

        Args:
            seller: Seller fixture using strict no-partial policy.
            product_id: Product UUID with fewer available units than ordered.

        Returns:
            None.

        Raises:
            RuntimeError: If strict policy reservation outcome is incorrect.
            httpx.HTTPStatusError: If an unexpected API response is returned.
        """
        order = await self.create_order(seller.seller_id, product_id, 5, "STRICT")
        if order["policy_snapshot"]["policy_id"] != seller.policy_id:
            raise RuntimeError("Order did not snapshot the expected seller policy.")

        reserve_response = await self.client.post(f"/orders/{order['id']}/reserve", json={})
        reserve_response.raise_for_status()
        reserved_order = reserve_response.json()
        line = reserved_order["lines"][0]
        if reserved_order["status"] != "BACKORDERED":
            raise RuntimeError(f"Expected BACKORDERED, got {reserved_order['status']}.")
        if Decimal(str(line["reserved_quantity"])) != Decimal("0.00"):
            raise RuntimeError("Strict partial policy unexpectedly reserved inventory.")
        if Decimal(str(line["backordered_quantity"])) != Decimal("5.00"):
            raise RuntimeError("Strict partial policy did not backorder the full line.")

        available = await self.get_balance_quantity(seller.seller_id, product_id, "AVAILABLE")
        if available != Decimal("3.00"):
            raise RuntimeError(f"Expected strict-policy AVAILABLE=3.00, got {available}.")

        self.mark_passed("Strict no-partial seller policy backorders deficient orders")

    async def verify_reservation_expiry_job(self, seller_id: str, product_id: str) -> None:
        """
        Verify expired reservations are released exactly once by the job.

        Args:
            seller_id: Seller UUID owning the product and order.
            product_id: Product UUID with available stock for a full reservation.

        Returns:
            None.

        Raises:
            RuntimeError: If job idempotency or balance assertions fail.
            httpx.HTTPStatusError: If an unexpected API response is returned.
        """
        order = await self.create_order(seller_id, product_id, 4, "EXPIRY")
        reserve_response = await self.client.post(f"/orders/{order['id']}/reserve", json={})
        reserve_response.raise_for_status()
        reserved_order = await self.get_order(order["id"])
        reservations = reserved_order["lines"][0]["reservations"]
        if not reservations:
            raise RuntimeError("Reserved order response did not expose reservation records.")
        reservation_id = reservations[0]["id"]

        await self.force_reservation_expired(reservation_id)
        first_result = await self.run_expiry_job_once()
        second_result = await self.run_expiry_job_once()

        if first_result["released_reservations_count"] < 1:
            raise RuntimeError(f"Expected expiry job to release at least one row: {first_result}.")
        if second_result["released_reservations_count"] != 0:
            raise RuntimeError(f"Expected second expiry job run to be idempotent: {second_result}.")

        available = await self.get_balance_quantity(seller_id, product_id, "AVAILABLE")
        reserved = await self.get_balance_quantity(seller_id, product_id, "RESERVED")
        if available != Decimal("4.00") or reserved != Decimal("0.00"):
            raise RuntimeError(
                "Expected expiry release AVAILABLE=4.00 and RESERVED=0.00, "
                f"got AVAILABLE={available}, RESERVED={reserved}."
            )

        self.mark_passed("Reservation expiry job releases stock idempotently")

    async def create_order(
        self,
        seller_id: str,
        product_id: str,
        ordered_quantity: int,
        label: str,
    ) -> dict:
        """
        Create a customer order for one product line.

        Args:
            seller_id: Seller UUID that owns the order.
            product_id: Product UUID on the order line.
            ordered_quantity: Quantity ordered.
            label: Short label included in the seller order number.

        Returns:
            dict: Created order response payload.

        Raises:
            httpx.HTTPStatusError: If order creation fails.
        """
        response = await self.client.post(
            "/orders",
            json={
                "seller_id": seller_id,
                "warehouse_id": self.context.warehouse_id,
                "seller_order_number": f"P3-{label}-{uuid4().hex[:10].upper()}",
                "channel": "DIRECT",
                "lines": [{"product_id": product_id, "ordered_quantity": ordered_quantity}],
            },
        )
        response.raise_for_status()
        return response.json()

    async def get_order(self, order_id: str) -> dict:
        """
        Retrieve a customer order by ID through the public API.

        Args:
            order_id: Order UUID to retrieve.

        Returns:
            dict: Order response payload.

        Raises:
            httpx.HTTPStatusError: If order retrieval fails.
        """
        response = await self.client.get(f"/orders/{order_id}")
        response.raise_for_status()
        return response.json()

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
            httpx.HTTPStatusError: If the balance query fails.
        """
        response = await self.client.get(
            "/inventory/balances",
            params={
                "seller_id": seller_id,
                "warehouse_id": self.context.warehouse_id,
                "product_id": product_id,
                "inventory_state": inventory_state,
                "limit": 200,
            },
        )
        response.raise_for_status()
        rows = response.json()
        return sum(Decimal(str(row["quantity"])) for row in rows)

    async def verify_product_ledger_reconciliation(self) -> None:
        """
        Compare movement sums and balance projections for all smoke products.

        Returns:
            None.

        Raises:
            RuntimeError: If any smoke product balance differs from movement sums.
            httpx.HTTPStatusError: If balance or movement query fails.
        """
        for seller_id, product_id in self.reconcile_product_ids:
            balances_response = await self.client.get(
                "/inventory/balances",
                params={
                    "seller_id": seller_id,
                    "warehouse_id": self.context.warehouse_id,
                    "product_id": product_id,
                    "limit": 200,
                },
            )
            balances_response.raise_for_status()
            movements_response = await self.client.get(
                "/inventory/movements",
                params={
                    "seller_id": seller_id,
                    "warehouse_id": self.context.warehouse_id,
                    "product_id": product_id,
                    "limit": 200,
                },
            )
            movements_response.raise_for_status()

            balance_totals = self.quantities_by_state(balances_response.json(), "quantity")
            movement_totals = self.quantities_by_state(
                movements_response.json(),
                "quantity_delta",
            )
            if balance_totals != movement_totals:
                raise RuntimeError(
                    "Balance projection differs from movement ledger for product "
                    f"{product_id}: {balance_totals} vs {movement_totals}."
                )

        self.mark_passed("Phase 3 smoke product balances reconcile to movement ledger")

    @staticmethod
    async def force_reservation_expired(reservation_id: str) -> None:
        """
        Move one reservation expiry timestamp into the past for job verification.

        Args:
            reservation_id: Reservation UUID to expire.

        Returns:
            None.

        Raises:
            RuntimeError: If the reservation row cannot be found.
        """
        await connect_to_database()
        try:
            async with transaction_session() as session:
                statement = select(InventoryReservation).where(
                    InventoryReservation.id == UUID(reservation_id)
                )
                result = await session.execute(statement)
                reservation = result.scalar_one_or_none()
                if reservation is None:
                    raise RuntimeError(f"Reservation {reservation_id} not found.")
                reservation.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        finally:
            await close_database_connection()

    @staticmethod
    async def run_expiry_job_once() -> dict:
        """
        Run the reservation expiry job directly against the configured database.

        Returns:
            dict: Job result summary.

        Raises:
            sqlalchemy.exc.SQLAlchemyError: If the job query fails.
        """
        await connect_to_database()
        try:
            async with transaction_session() as session:
                return await release_expired_reservations(session)
        finally:
            await close_database_connection()

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
) -> Phase3Context:
    """
    Authenticate and select the first visible warehouse for E2E records.

    Args:
        client: Async HTTP client configured for the API base URL.
        api_base_url: API base URL used in status output.
        admin_email: Admin email for login.
        admin_password: Admin password for login.

    Returns:
        Phase3Context: Authenticated runtime context.

    Raises:
        RuntimeError: If no warehouse master data is available.
        httpx.HTTPStatusError: If login or master-data loading fails.
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
    if not warehouses:
        raise RuntimeError("No warehouses are available for Phase 3 E2E testing.")

    return Phase3Context(
        api_base_url=api_base_url,
        admin_email=admin_email,
        admin_password=admin_password,
        warehouse_id=warehouses[0]["id"],
        token=token,
    )


def build_parser() -> argparse.ArgumentParser:
    """
    Build the command-line argument parser for Phase 3 E2E execution.

    Returns:
        argparse.ArgumentParser: Configured parser.
    """
    parser = argparse.ArgumentParser(
        description="Run Phase 3 orders and fulfillment E2E smoke test."
    )
    parser.add_argument(
        "--api-base-url",
        default=os.getenv("PHASE3_E2E_API_BASE_URL", DEFAULT_API_BASE_URL),
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
    Load configuration and run the Phase 3 E2E smoke test.

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
        runner = Phase3E2ERunner(client, context)
        await runner.run()
        print(f"\nPhase 3 E2E complete: {len(runner.passed_steps)} / 5 checks passed.")


def main() -> None:
    """
    Run the async Phase 3 E2E entrypoint from a synchronous CLI boundary.

    Returns:
        None.
    """
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
