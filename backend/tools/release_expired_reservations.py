"""
--------------------------------------------------------------------------------
File        : tools/release_expired_reservations.py
Purpose     : Execute the reservation-expiry release job from the CLI.

Responsibilities:
    - Connect to the configured PostgreSQL database.
    - Run the idempotent expired-reservation release job in one transaction.
    - Print an operator-readable summary.

Flow:
    CLI invocation
        ->
    connect_to_database()
        ->
    release_expired_reservations()
        ->
    close_database_connection()

Used By:
    - Manual operations.
    - Scheduled reservation-expiry runbooks.

Returns:
    main() -> None - Runs the CLI command.

Raises:
    sqlalchemy.exc.SQLAlchemyError: If database operations fail.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import asyncio

from core.database.database import (
    close_database_connection,
    connect_to_database,
    transaction_session,
)
from core.jobs.reservation_expiry_job import release_expired_reservations


async def run() -> None:
    """
    Run expired reservation release and print the result summary.

    Returns:
        None.

    Raises:
        sqlalchemy.exc.SQLAlchemyError: If database connection or release fails.
    """
    print("=========================================================")
    print("RESERVATION EXPIRY RELEASE RUNNER")
    print("=========================================================")

    await connect_to_database()
    try:
        async with transaction_session() as session:
            result = await release_expired_reservations(session)
            print(f" -> Released Count: {result['released_reservations_count']}")
            print(f" -> Released Quantity Total: {result['released_quantity_total']}")
            print("\nResult: RESERVATION EXPIRY RUN COMPLETE - SUCCESS")
    finally:
        await close_database_connection()


def main() -> None:
    """
    Execute the async reservation release runner from a synchronous CLI boundary.

    Returns:
        None.
    """
    asyncio.run(run())


if __name__ == "__main__":
    main()
