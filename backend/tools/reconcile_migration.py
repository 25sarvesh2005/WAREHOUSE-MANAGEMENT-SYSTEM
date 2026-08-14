"""
--------------------------------------------------------------------------------
Opening Inventory Migration Reconciliation CLI Tool
--------------------------------------------------------------------------------
Purpose:
    Generates and displays the migration rehearsal reconciliation report for a batch.

Usage:
    python -m tools.reconcile_migration --batch-id UUID

Outputs:
    Detailed line-by-line reconciliation audit comparing staged vs ledger position.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from uuid import UUID

from common.logger import get_logger
from core.constants import UserRole
from core.controllers.migration_controller import migration_controller
from core.database.database import (
    close_database_connection,
    connect_to_database,
    transaction_session,
)
from core.models.identity_model import User
from sqlalchemy import select

logger = get_logger(__name__)


async def run_migration_reconciliation(batch_id_str: str) -> None:
    """
    Generate and print migration reconciliation report for a batch.

    Args:
        batch_id_str: Batch UUID string.

    Returns:
        None.
    """
    print("=========================================================")
    print("MIGRATION REHEARSAL RECONCILIATION AUDIT")
    print("=========================================================")

    await connect_to_database()

    try:
        batch_id = UUID(batch_id_str)
        async with transaction_session() as session:
            admin_user = (
                await session.execute(
                    select(User).where(User.role == UserRole.ADMINISTRATOR.value).limit(1)
                )
            ).scalar_one_or_none()

            if not admin_user:
                print("Error: Administrator user not found.")
                sys.exit(1)

            scope = {
                "user_id": str(admin_user.id),
                "role": admin_user.role,
            }

            report = await migration_controller.get_reconciliation_report(scope, batch_id)

            print(f"Batch ID:              {report['batch_id']}")
            print(f"Batch Number:          {report['batch_number']}")
            print(f"Batch Status:          {report['batch_status']}")
            print(f"Total Staged Rows:     {report['total_staged_rows']}")
            print(f"Movements Applied:     {report['applied_movements_count']}")
            print(f"Reconciliation Status: {report['reconciliation_status']}")
            print("---------------------------------------------------------")

            for idx, detail in enumerate(report["details"], 1):
                print(
                    f"Line {idx}: Seller={detail['seller_code']} SKU={detail['sku']} "
                    f"Warehouse={detail['warehouse_code']} Location={detail['location_code']} "
                    f"State={detail['inventory_state']} | "
                    f"Staged={detail['staged_approved_quantity']} "
                    f"Ledger={detail['ledger_movement_quantity']} "
                    f"Variance={detail['variance_quantity']} "
                    f"Status={detail['status']}"
                )

            if report["reconciliation_status"] != "MATCH":
                print("\nWARNING: Reconciliation contains mismatches!")
                sys.exit(1)
            else:
                print("\nSUCCESS: All staged quantities match ledger movements cleanly.")
    finally:
        await close_database_connection()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reconcile an opening inventory batch.")
    parser.add_argument("--batch-id", required=True, help="Migration batch UUID.")
    args = parser.parse_args()
    asyncio.run(run_migration_reconciliation(args.batch_id))
