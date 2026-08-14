"""
--------------------------------------------------------------------------------
Opening Inventory Migration Rehearsal CLI Tool
--------------------------------------------------------------------------------
Purpose:
    Executes a rehearsal of opening inventory migration workflow:
    Creates batch -> stages rows -> validates -> approves -> applies -> reconciles.

Usage:
    python -m tools.rehearse_migration [--notes NOTES]

Outputs:
    Migration rehearsal summary and reconciliation results.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import argparse
import asyncio

from common.logger import get_logger
from core.constants import UserRole
from core.controllers.migration_controller import migration_controller
from core.database.database import (
    close_database_connection,
    connect_to_database,
    transaction_session,
)
from core.models.catalog_model import Product
from core.models.identity_model import Seller, User, Warehouse
from sqlalchemy import select

logger = get_logger(__name__)


async def run_rehearsal(
    source_notes: str = "Migration Rehearsal Tool Run",
    *,
    apply_to_ledger: bool = False,
) -> None:
    """
    Execute an opening inventory migration rehearsal.

    Args:
        source_notes: Optional description for the rehearsal batch.
        apply_to_ledger: When True, approve and apply the sample batch.

    Returns:
        None.

    Raises:
        RuntimeError: If required master data is missing or validation fails.
    """
    print("=========================================================")
    print("OPENING INVENTORY MIGRATION REHEARSAL")
    print("=========================================================")

    await connect_to_database()

    try:
        async with transaction_session() as session:
            # Find an admin user or fallback
            admin_user = (
                await session.execute(
                    select(User).where(User.role == UserRole.ADMINISTRATOR.value).limit(1)
                )
            ).scalar_one_or_none()

            seller = (
                await session.execute(select(Seller).where(Seller.status == "ACTIVE").limit(1))
            ).scalar_one_or_none()
            warehouse = (
                await session.execute(
                    select(Warehouse).where(Warehouse.status == "ACTIVE").limit(1)
                )
            ).scalar_one_or_none()
            product = (
                await session.execute(select(Product).where(Product.status == "ACTIVE").limit(1))
            ).scalar_one_or_none()

            if not admin_user or not seller or not warehouse or not product:
                raise RuntimeError(
                    "Required master data missing: admin user, seller, warehouse, and "
                    "product are required for rehearsal."
                )

            scope = {
                "user_id": str(admin_user.id),
                "role": admin_user.role,
                "seller_ids": [str(seller.id)],
                "warehouse_ids": [str(warehouse.id)],
            }

            # Step 1: Create batch
            batch = await migration_controller.create_batch(scope, source_notes=source_notes)
            print(f"[1/5] Created Import Batch: {batch.batch_number} (ID: {batch.id})")

            # Step 2: Stage sample rows
            rows_data = [
                {
                    "source_workbook": "rehearsal_opening_stock.xlsx",
                    "source_sheet": "Sheet1",
                    "source_row_number": 2,
                    "raw_seller_code": seller.code,
                    "raw_sku": product.sku,
                    "raw_warehouse_code": warehouse.code,
                    "raw_location_code": None,
                    "raw_inventory_state": "AVAILABLE",
                    "raw_quantity": "100.00",
                }
            ]
            staged = await migration_controller.submit_staged_rows(scope, batch.id, rows_data)
            print(f"[2/5] Staged {len(staged)} raw rows into batch.")

            # Step 3: Validate
            validated_batch = await migration_controller.validate_batch(scope, batch.id)
            print(
                f"[3/5] Validated Batch: Status={validated_batch.status}, "
                f"Valid={validated_batch.valid_rows}, Invalid={validated_batch.invalid_rows}"
            )

            if validated_batch.invalid_rows > 0:
                raise RuntimeError("Validation failed with invalid rows. Rehearsal stopped.")

            if not apply_to_ledger:
                print("[4/5] Skipped approval/apply. Pass --apply to mutate the ledger.")
                print("[5/5] Rehearsal complete without operational inventory changes.")
                return

            # Step 4: Approve
            approved_batch = await migration_controller.approve_batch(scope, batch.id)
            print(
                f"[4/5] Approved Batch: Status={approved_batch.status}, "
                f"ApprovedBy={approved_batch.approved_by_user_id}"
            )

            # Step 5: Apply
            applied_batch = await migration_controller.apply_batch(scope, batch.id)
            print(
                f"[5/5] Applied Batch: Status={applied_batch.status}, "
                f"AppliedAt={applied_batch.applied_at}"
            )

            # Step 6: Reconciliation
            report = await migration_controller.get_reconciliation_report(scope, batch.id)
            print("\nReconciliation Report:")
            print(f"  Batch Number: {report['batch_number']}")
            print(f"  Reconciliation Status: {report['reconciliation_status']}")
            print(f"  Movements Applied: {report['applied_movements_count']}")
            for detail in report["details"]:
                print(
                    f"  - SKU={detail['sku']} State={detail['inventory_state']} "
                    f"Staged={detail['staged_approved_quantity']} "
                    f"Ledger={detail['ledger_movement_quantity']} Status={detail['status']}"
                )

            print("\nRehearsal complete cleanly.")
    finally:
        await close_database_connection()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rehearse opening inventory migration.")
    parser.add_argument(
        "--notes",
        default="Migration Rehearsal Run",
        help="Source notes for batch.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Approve and apply the staged sample row to the live inventory ledger.",
    )
    args = parser.parse_args()
    asyncio.run(run_rehearsal(source_notes=args.notes, apply_to_ledger=args.apply))
