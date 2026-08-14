"""
--------------------------------------------------------------------------------
Opening Inventory File Import CLI Tool
--------------------------------------------------------------------------------
Purpose:
    Parse a CSV/XLSX opening inventory file and stage rows into an import batch.

Usage:
    python -m tools.import_opening_inventory --batch-id UUID --file path/to/file.csv

Outputs:
    Staged row summary. This command never validates, approves, applies, or
    mutates inventory balances.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from common.logger import get_logger
from core.constants import UserRole
from core.controllers.migration_controller import migration_controller
from core.database.database import (
    close_database_connection,
    connect_to_database,
    transaction_session,
)
from core.models.identity_model import User

logger = get_logger(__name__)


async def import_opening_inventory_file(batch_id_str: str, file_path_str: str) -> None:
    """
    Parse and stage an opening inventory source file into an existing batch.

    Args:
        batch_id_str: Target import batch UUID string.
        file_path_str: Local CSV/XLSX file path.

    Returns:
        None.

    Raises:
        RuntimeError: If the file or administrator scope is unavailable.
    """
    batch_id = UUID(batch_id_str)
    file_path = Path(file_path_str)
    if not file_path.is_file():
        raise RuntimeError(f"Opening inventory file not found: {file_path}")

    await connect_to_database()
    try:
        async with transaction_session() as session:
            admin_user = (
                await session.execute(
                    select(User).where(User.role == UserRole.ADMINISTRATOR.value).limit(1)
                )
            ).scalar_one_or_none()
            if admin_user is None:
                raise RuntimeError("Administrator user not found for import staging.")

            scope = {
                "user_id": str(admin_user.id),
                "role": admin_user.role,
                "seller_ids": [],
                "warehouse_ids": [],
            }

        file_bytes = file_path.read_bytes()
        response = await migration_controller.upload_staged_rows_file(
            scope,
            batch_id,
            file_path.name,
            file_bytes,
        )

        print("=========================================================")
        print("OPENING INVENTORY FILE STAGED")
        print("=========================================================")
        print(f"Batch ID:    {response['batch_id']}")
        print(f"File:        {response['file_name']}")
        print(f"Parsed Rows: {response['parsed_rows']}")
        print(f"Staged Rows: {response['staged_rows']}")
        print("\nNo inventory movements or balance updates were created.")
    finally:
        await close_database_connection()


def main() -> None:
    """
    Parse CLI arguments and execute the opening inventory import command.

    Returns:
        None.
    """
    parser = argparse.ArgumentParser(description="Stage opening inventory file rows.")
    parser.add_argument("--batch-id", required=True, help="Target import batch UUID.")
    parser.add_argument("--file", required=True, help="CSV/XLSX opening inventory file.")
    args = parser.parse_args()
    asyncio.run(import_opening_inventory_file(args.batch_id, args.file))


if __name__ == "__main__":
    main()
