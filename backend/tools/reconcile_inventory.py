"""
--------------------------------------------------------------------------------
Inventory Ledger Reconciliation CLI Tool
--------------------------------------------------------------------------------
Purpose:
    Compares projected operational balances (inventory_balances) against the
    authoritative append-only movement ledger (inventory_movements) rebuild.

Usage:
    python -m tools.reconcile_inventory [--warehouse-id UUID] [--seller-id UUID]

Outputs:
    Detailed audit report detailing matched balances, variance discrepancies,
    and integrity reconciliation status.
--------------------------------------------------------------------------------
"""

import argparse
import asyncio
import sys
from decimal import Decimal
from uuid import UUID

from core.cruds import inventory_crud
from core.database.database import (
    close_database_connection,
    connect_to_database,
    transaction_session,
)

async def run_reconciliation(warehouse_id: str | None = None, seller_id: str | None = None) -> None:
    """
    Compare projected inventory balances against ledger-rebuilt quantities.

    Args:
        warehouse_id: Optional warehouse UUID string used to narrow the audit.
        seller_id: Optional seller UUID string used to narrow the audit.

    Returns:
        None.

    Raises:
        SystemExit: Exits with status 1 when reconciliation variances are found.
        ValueError: If supplied UUID filters are malformed.
    """
    print("=========================================================")
    print("INVENTORY LEDGER & BALANCE RECONCILIATION AUDIT")
    print("=========================================================")

    await connect_to_database()

    wh_uuid = UUID(warehouse_id) if warehouse_id else None
    seller_uuid = UUID(seller_id) if seller_id else None

    try:
        async with transaction_session() as session:
            # 1. Fetch live projection balances
            projections = await inventory_crud.list_balances(
                session,
                warehouse_id=wh_uuid,
                seller_id=seller_uuid,
                limit=1000,
            )

            # Map projection key -> quantity
            proj_map = {}
            for p in projections:
                key = (
                    str(p.seller_id),
                    str(p.warehouse_id),
                    str(p.product_id),
                    str(p.location_id) if p.location_id else "NONE",
                    str(p.inventory_state),
                )
                proj_map[key] = p.quantity

            # 2. Fetch rebuilt ledger balances
            rebuild_rows = await inventory_crud.rebuild_ledger_balances(
                session,
                warehouse_id=wh_uuid,
                seller_id=seller_uuid,
            )

            rebuild_map = {}
            for r in rebuild_rows:
                key = (
                    r["seller_id"],
                    r["warehouse_id"],
                    r["product_id"],
                    r["location_id"] if r["location_id"] else "NONE",
                    r["inventory_state"],
                )
                rebuild_map[key] = r["rebuilt_quantity"]

            # 3. Compare all keys
            all_keys = set(proj_map.keys()).union(set(rebuild_map.keys()))

            matches = 0
            variances = []

            for key in all_keys:
                proj_qty = proj_map.get(key, Decimal("0.00"))
                rebuild_qty = rebuild_map.get(key, Decimal("0.00"))

                diff = proj_qty - rebuild_qty
                if diff == Decimal("0.00"):
                    matches += 1
                else:
                    variances.append(
                        {
                            "seller_id": key[0],
                            "warehouse_id": key[1],
                            "product_id": key[2],
                            "location_id": key[3],
                            "inventory_state": key[4],
                            "projected_quantity": proj_qty,
                            "rebuilt_quantity": rebuild_qty,
                            "variance": diff,
                        }
                    )

            print("\nAudit Summary:")
            print(f" -> Total Composite Balance Keys Evaluated: {len(all_keys)}")
            print(f" -> Exact Ledger Matches: {matches}")
            print(f" -> Variance Discrepancies: {len(variances)}")

            if variances:
                print("\n[!] DISCREPANCY DETECTED:")
                for v in variances:
                    print(
                        f"    Seller={v['seller_id'][:8]}.. WH={v['warehouse_id'][:8]}.. "
                        f"Prod={v['product_id'][:8]}.. State={v['inventory_state']} | "
                        f"Projection={v['projected_quantity']} vs Rebuild={v['rebuilt_quantity']} (Variance={v['variance']})"
                    )
                print("\nResult: RECONCILIATION FAILED - Discrepancy present.")
                sys.exit(1)
            else:
                print("\nResult: RECONCILIATION PASSED - 100% Mathematical Precision!")
    finally:
        await close_database_connection()


def main() -> None:
    """
    Parse CLI arguments and execute the inventory reconciliation audit.

    Returns:
        None.

    Raises:
        SystemExit: Propagates reconciliation failure or argument parsing errors.
    """
    parser = argparse.ArgumentParser(
        description="Reconcile Inventory Balances against Movement Ledger"
    )
    parser.add_argument("--warehouse-id", type=str, help="Optional Warehouse UUID filter")
    parser.add_argument("--seller-id", type=str, help="Optional Seller UUID filter")
    args = parser.parse_args()

    asyncio.run(run_reconciliation(args.warehouse_id, args.seller_id))


if __name__ == "__main__":
    main()
