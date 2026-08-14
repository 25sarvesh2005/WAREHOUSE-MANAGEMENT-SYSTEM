"""
--------------------------------------------------------------------------------
File        : core/apis/schemas/requests/migration_request.py
Purpose     : Define opening inventory migration request schemas.

Responsibilities:
    - Validate import batch creation request payloads.
    - Validate staged row submission payloads with raw evidence.

Flow:
    HTTP request body -> Pydantic request schema -> MigrationController

Used By:
    - core/apis/routes/migration_routes.py

Returns:
    BaseModel instances - Validated migration request payloads.

Raises:
    pydantic.ValidationError: When request shape validation fails.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreateImportBatchRequest(BaseModel):
    """Request body to create a new opening inventory import batch."""

    source_notes: str | None = Field(
        default=None,
        max_length=500,
        description="Optional notes or source document description.",
    )


class StagedRowSubmitItem(BaseModel):
    """Single raw opening inventory row submitted for staging."""

    source_workbook: str = Field(
        min_length=1,
        max_length=255,
        description="Source spreadsheet filename or workbook identifier.",
    )
    source_sheet: str = Field(
        min_length=1,
        max_length=255,
        description="Worksheet name within source workbook.",
    )
    source_row_number: int = Field(
        ge=1,
        description="1-indexed row number in the source worksheet.",
    )
    source_hash: str | None = Field(
        default=None,
        max_length=64,
        description="SHA-256 hash of raw row content for duplicate content detection.",
    )
    raw_seller_code: str | None = Field(
        default=None,
        max_length=100,
        description="Raw seller code value from spreadsheet.",
    )
    raw_sku: str | None = Field(
        default=None,
        max_length=100,
        description="Raw SKU value from spreadsheet.",
    )
    raw_upc: str | None = Field(
        default=None,
        max_length=100,
        description="Raw UPC/barcode value from spreadsheet.",
    )
    raw_warehouse_code: str | None = Field(
        default=None,
        max_length=100,
        description="Raw warehouse code value from spreadsheet.",
    )
    raw_location_code: str | None = Field(
        default=None,
        max_length=100,
        description="Raw location code value from spreadsheet.",
    )
    raw_inventory_state: str | None = Field(
        default=None,
        max_length=50,
        description="Raw inventory state value from spreadsheet.",
    )
    raw_quantity: str | None = Field(
        default=None,
        max_length=100,
        description="Raw quantity string value from spreadsheet.",
    )


class SubmitStagedRowsRequest(BaseModel):
    """Request body containing list of staged rows to submit to an import batch."""

    rows: list[StagedRowSubmitItem] = Field(
        min_length=1,
        description="List of raw staged rows to insert into batch.",
    )
