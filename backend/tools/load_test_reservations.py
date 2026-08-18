"""
Concurrency load test script targeting order reservation paths.

Exercises row-level locking under high contention to verify zero over-allocation
and measure throughput and latency on reservation endpoints.
"""

from __future__ import annotations

import asyncio
import time
from decimal import Decimal
from uuid import UUID, uuid4

from core.constants import BusinessStatus, InventoryMovementType, InventoryState, OrderStatus, UserRole
from core.controllers.order_controller import order_controller
from core.cruds import catalog_crud, identity_crud, inventory_crud
from core.database.database import close_database_connection, connect_to_database, transaction_session
from core.models.catalog_model import Product
from core.models.identity_model import Seller, User, Warehouse
from core.models.inventory_model import InventoryBalance, InventoryMovement


async def run_reservation_load_test(
    concurrency: int = 20,
    total_orders: int = 50,
    initial_stock: int = 30,
) -> dict[str, object]:
    """
    Run concurrent reservation attempts against limited stock.

    Args:
        concurrency: Number of concurrent reservation workers.
        total_orders: Total orders attempting to reserve 1 unit each.
        initial_stock: Initial available inventory units (fewer than total_orders).

    Returns:
        dict[str, object]: Performance and correctness metrics.
    """
    print(f"=== Starting Reservation Concurrency Load Test ===")
    print(f"Concurrency: {concurrency} workers | Total Orders: {total_orders} | Initial Stock: {initial_stock}")

    await connect_to_database()

    # 1. Setup test seller, warehouse, product, and balance
    async with transaction_session() as session:
        user = User(
            email=f"loadtest-{uuid4().hex[:6]}@test.com",
            name="Load Test Admin",
            hashed_password="hash",
            role=UserRole.ADMINISTRATOR.value,
            status=BusinessStatus.ACTIVE.value,
        )
        session.add(user)

        seller = Seller(
            name=f"Load Test Seller {uuid4().hex[:6]}",
            code=f"LT-{uuid4().hex[:4].upper()}",
            status=BusinessStatus.ACTIVE.value,
        )
        session.add(seller)

        wh = Warehouse(
            name=f"Load Test WH {uuid4().hex[:6]}",
            code=f"LT-WH-{uuid4().hex[:4].upper()}",
            timezone="America/Los_Angeles",
            status=BusinessStatus.ACTIVE.value,
        )
        session.add(wh)
        await session.flush()

        product = Product(
            seller_id=seller.id,
            sku=f"SKU-LT-{uuid4().hex[:6]}",
            name="Load Test High Contention Item",
            status=BusinessStatus.ACTIVE.value,
        )
        session.add(product)
        await session.flush()

        # Seed initial stock
        balance = InventoryBalance(
            seller_id=seller.id,
            product_id=product.id,
            warehouse_id=wh.id,
            inventory_state=InventoryState.AVAILABLE.value,
            quantity=Decimal(str(initial_stock)),
        )
        session.add(balance)
        await session.flush()

        user_id = user.id
        seller_id = seller.id
        wh_id = wh.id
        prod_id = product.id

    scope = {
        "user_id": str(user_id),
        "role": UserRole.ADMINISTRATOR.value,
        "seller_ids": [str(seller_id)],
        "warehouse_ids": [str(wh_id)],
    }

    # 2. Create order drafts first
    created_orders = []
    for i in range(total_orders):
        order_data = {
            "seller_id": str(seller_id),
            "warehouse_id": str(wh_id),
            "seller_order_number": f"LT-ORD-{i:03d}-{uuid4().hex[:4]}",
            "customer_name": f"Load Tester {i}",
            "lines": [{"product_id": str(prod_id), "ordered_quantity": 1}],
        }
        order = await order_controller.create_order(order_data, scope)
        created_orders.append(order)

    print(f"Created {len(created_orders)} order drafts. Executing concurrent reservations...")

    # 3. Execute reservations concurrently with semaphore
    semaphore = asyncio.Semaphore(concurrency)
    latencies: list[float] = []
    reserved_count = 0
    backordered_count = 0
    errors_count = 0

    async def reserve_worker(order_id: UUID) -> None:
        nonlocal reserved_count, backordered_count, errors_count
        async with semaphore:
            t0 = time.perf_counter()
            try:
                result = await order_controller.reserve_order(
                    order_id,
                    scope,
                    allow_backorder=True,
                )
                lat = (time.perf_counter() - t0) * 1000
                latencies.append(lat)
                if result.status == OrderStatus.RESERVED.value:
                    reserved_count += 1
                elif result.status == OrderStatus.BACKORDERED.value:
                    backordered_count += 1
            except Exception as e:
                errors_count += 1
                print(f"Worker error on order {order_id}: {e}")

    start_total = time.perf_counter()
    tasks = [asyncio.create_task(reserve_worker(ord_obj.id)) for ord_obj in created_orders]
    await asyncio.gather(*tasks)
    total_duration_sec = time.perf_counter() - start_total

    # 4. Verify ledger and balance state
    async with transaction_session() as session:
        avail_bal = await inventory_crud.get_balance(
            session,
            seller_id=seller_id,
            product_id=prod_id,
            warehouse_id=wh_id,
            inventory_state=InventoryState.AVAILABLE.value,
        )
        res_bal = await inventory_crud.get_balance(
            session,
            seller_id=seller_id,
            product_id=prod_id,
            warehouse_id=wh_id,
            inventory_state=InventoryState.RESERVED.value,
        )

        final_available = avail_bal.quantity if avail_bal else Decimal("0.00")
        final_reserved = res_bal.quantity if res_bal else Decimal("0.00")

    # Invariants verification
    over_allocated = reserved_count > initial_stock
    balance_consistent = (final_reserved == Decimal(str(reserved_count))) and (final_available == Decimal(str(initial_stock - reserved_count)))

    sorted_lats = sorted(latencies) if latencies else [0]
    p50 = sorted_lats[int(len(sorted_lats) * 0.50)]
    p95 = sorted_lats[int(len(sorted_lats) * 0.95)]
    p99 = sorted_lats[min(len(sorted_lats) - 1, int(len(sorted_lats) * 0.99))]
    throughput_rps = round(total_orders / total_duration_sec, 2) if total_duration_sec > 0 else 0

    metrics = {
        "total_orders": total_orders,
        "reserved_count": reserved_count,
        "backordered_count": backordered_count,
        "errors_count": errors_count,
        "final_available_quantity": float(final_available),
        "final_reserved_quantity": float(final_reserved),
        "over_allocation_detected": over_allocated,
        "balance_consistent": balance_consistent,
        "throughput_rps": throughput_rps,
        "latency_ms_p50": round(p50, 2),
        "latency_ms_p95": round(p95, 2),
        "latency_ms_p99": round(p99, 2),
        "duration_sec": round(total_duration_sec, 2),
    }

    print("\n=== Load Test Results ===")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    await close_database_connection()
    return metrics


if __name__ == "__main__":
    asyncio.run(run_reservation_load_test(concurrency=10, total_orders=30, initial_stock=15))
