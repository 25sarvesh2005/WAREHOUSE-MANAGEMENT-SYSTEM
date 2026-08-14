"""
--------------------------------------------------------------------------------
File        : cli/main.py
Purpose     : Provide operational CLI commands for the warehouse platform.

Responsibilities:
    - Expose health and migration-oriented checks.
    - Connect through approved database lifecycle helpers.

Flow:
    Operator runs CLI command
        ->
    Typer command connects to application services
        ->
    Result is printed for operator use

Used By:
    - Warehouse operations and implementation scripts

Returns:
    app -> typer.Typer - CLI application object.

Raises:
    typer.Exit: When a command cannot complete successfully.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

import asyncio

import typer

from common.logger import get_logger
from core.database.database import (
    check_database_ready,
    close_database_connection,
    connect_to_database,
)

logger = get_logger(__name__)
app = typer.Typer(help="Whitfield warehouse operations CLI.")


@app.command("database-health")
def database_health() -> None:
    """
    Check database connectivity from the CLI.

    The command reuses the application database lifecycle helpers and exits with
    a non-zero status when the readiness check fails.

    Returns:
        None.

    Raises:
        typer.Exit: If database connectivity fails.
    """

    async def _run() -> None:
        """
        Execute the async database health check.

        The nested function keeps Typer's synchronous command surface simple
        while using the same async database helper as the API.

        Returns:
            None.

        Raises:
            Exception: If database readiness fails.
        """
        await connect_to_database()
        await check_database_ready()
        await close_database_connection()

    try:
        asyncio.run(_run())
        typer.echo("database: ready")
    except Exception as error:
        logger.error("Database health command failed: %s", error, exc_info=True)
        typer.echo("database: not ready")
        raise typer.Exit(code=1) from error


@app.command("rehearse-migration")
def rehearse_migration(
    notes: str = typer.Option("Migration Rehearsal CLI Run", help="Source notes for batch."),
    apply: bool = typer.Option(
        False,
        "--apply",
        help="Approve and apply the sample row to the live inventory ledger.",
    ),
) -> None:
    """Run an opening inventory migration rehearsal flow."""
    from tools.rehearse_migration import run_rehearsal

    try:
        asyncio.run(run_rehearsal(source_notes=notes, apply_to_ledger=apply))
        typer.echo("migration rehearsal: success")
    except Exception as error:
        logger.error("Migration rehearsal failed: %s", error, exc_info=True)
        typer.echo(f"migration rehearsal failed: {error}")
        raise typer.Exit(code=1) from error


@app.command("reconcile-migration")
def reconcile_migration(
    batch_id: str = typer.Option(..., help="Target migration batch UUID."),
) -> None:
    """Reconcile an opening inventory migration batch."""
    from tools.reconcile_migration import run_migration_reconciliation

    try:
        asyncio.run(run_migration_reconciliation(batch_id))
        typer.echo("migration reconciliation: match")
    except Exception as error:
        logger.error("Migration reconciliation failed: %s", error, exc_info=True)
        typer.echo(f"migration reconciliation failed: {error}")
        raise typer.Exit(code=1) from error


@app.command("import-opening-inventory")
def import_opening_inventory(
    batch_id: str = typer.Option(..., help="Target migration batch UUID."),
    file: str = typer.Option(..., help="CSV/XLSX opening inventory file path."),
) -> None:
    """Stage opening inventory file rows into an import batch."""
    from tools.import_opening_inventory import import_opening_inventory_file

    try:
        asyncio.run(import_opening_inventory_file(batch_id, file))
        typer.echo("opening inventory import: staged")
    except Exception as error:
        logger.error("Opening inventory import failed: %s", error, exc_info=True)
        typer.echo(f"opening inventory import failed: {error}")
        raise typer.Exit(code=1) from error


if __name__ == "__main__":
    app()
