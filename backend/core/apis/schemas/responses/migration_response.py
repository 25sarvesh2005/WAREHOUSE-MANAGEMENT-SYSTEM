"""
--------------------------------------------------------------------------------
File        : core/apis/schemas/responses/migration_response.py
Purpose     : Define opening inventory migration response schemas.

Responsibilities:
    - Serialize import batch headers and validation summary.
    - Serialize staged rows with raw values, resolved IDs, and validation errors.
    - Serialize migration rehearsal reconciliation reports.

Flow:
    Controller domain data -> Pydantic response schema -> FastAPI JSON

Used By:
    - core/apis/routes/migration_routes.py

Returns:
    BaseModel instances - Serialized migration API responses.

Raises:
    pydantic.ValidationError: When response schema mapping fails.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ImportBatchResponse(BaseModel):
    """Serialized import batch response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="Batch UUID primary key.")
    batch_number: str = Field(description="Unique human-readable batch identifier.")
    status: str = Field(description="Current batch status.")
    source_notes: str | None = Field(default=None, description="Optional batch description.")
    created_by_user_id: UUID = Field(description="User UUID who created the batch.")
    approved_by_user_id: UUID | None = Field(
        default=None,
        description="User UUID who approved the batch.",
    )
    approved_at: datetime | None = Field(default=None, description="UTC timestamp of approval.")
    applied_at: datetime | None = Field(
        default=None,
        description="UTC timestamp of application to ledger.",
    )
    total_rows: int = Field(description="Total count of staged rows in batch.")
    valid_rows: int = Field(description="Count of valid staged rows in batch.")
    invalid_rows: int = Field(description="Count of invalid staged rows in batch.")
    created_at: datetime = Field(description="UTC creation timestamp.")
    updated_at: datetime = Field(description="UTC last updated timestamp.")


class StagedRowResponse(BaseModel):
    """Serialized staged row response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="Row UUID primary key.")
    import_batch_id: UUID = Field(description="Parent batch UUID.")
    source_workbook: str = Field(description="Source workbook filename.")
    source_sheet: str = Field(description="Source worksheet name.")
    source_row_number: int = Field(description="Source row number.")
    source_hash: str = Field(description="SHA-256 source content hash.")
    raw_seller_code: str | None = Field(default=None, description="Raw seller code.")
    raw_sku: str | None = Field(default=None, description="Raw SKU.")
    raw_upc: str | None = Field(default=None, description="Raw UPC/barcode.")
    raw_warehouse_code: str | None = Field(default=None, description="Raw warehouse code.")
    raw_location_code: str | None = Field(default=None, description="Raw location code.")
    raw_inventory_state: str | None = Field(default=None, description="Raw inventory state.")
    raw_quantity: str | None = Field(default=None, description="Raw quantity text.")
    seller_id: UUID | None = Field(default=None, description="Resolved seller UUID.")
    product_id: UUID | None = Field(default=None, description="Resolved product UUID.")
    warehouse_id: UUID | None = Field(default=None, description="Resolved warehouse UUID.")
    location_id: UUID | None = Field(default=None, description="Resolved location UUID.")
    inventory_state: str | None = Field(default=None, description="Resolved inventory state.")
    quantity: Decimal | None = Field(default=None, description="Resolved numeric quantity.")
    validation_status: str = Field(description="Validation status (PENDING, VALID, INVALID).")
    validation_errors: list[dict[str, object]] = Field(
        default_factory=list, description="List of validation errors."
    )
    applied_movement_id: UUID | None = Field(
        default=None, description="Linked movement UUID if applied."
    )
    created_at: datetime = Field(description="UTC creation timestamp.")
    updated_at: datetime = Field(description="UTC last updated timestamp.")


class ValidationSummaryResponse(BaseModel):
    """Validation summary result for a migration batch."""

    batch_id: UUID = Field(description="Batch UUID.")
    batch_number: str = Field(description="Batch identifier.")
    status: str = Field(description="Updated batch status.")
    total_rows: int = Field(description="Total staged rows.")
    valid_rows: int = Field(description="Valid staged rows.")
    invalid_rows: int = Field(description="Invalid staged rows.")


class MigrationUploadResponse(BaseModel):
    """Summary response for a staged opening inventory file upload."""

    batch_id: UUID = Field(description="Target migration batch UUID.")
    file_name: str = Field(description="Uploaded source file name.")
    parsed_rows: int = Field(description="Count of parsed non-empty source rows.")
    staged_rows: int = Field(description="Total staged rows currently in the batch.")


class ReconciliationRowDetail(BaseModel):
    """Detailed reconciliation row comparison for migration rehearsal."""

    seller_code: str | None = Field(default=None, description="Seller code.")
    sku: str | None = Field(default=None, description="Product SKU.")
    warehouse_code: str | None = Field(default=None, description="Warehouse code.")
    location_code: str | None = Field(default=None, description="Location code.")
    inventory_state: str = Field(description="Inventory state.")
    staged_approved_quantity: Decimal = Field(description="Staged approved quantity sum.")
    ledger_movement_quantity: Decimal = Field(description="Ledger movement quantity sum for batch.")
    balance_projection_quantity: Decimal = Field(description="Current balance projection quantity.")
    variance_quantity: Decimal = Field(description="Variance (staged vs ledger).")
    status: str = Field(description="Row reconciliation status (MATCH or MISMATCH).")


class MigrationReconciliationReportResponse(BaseModel):
    """Migration rehearsal reconciliation report."""

    batch_id: UUID = Field(description="Target migration batch UUID.")
    batch_number: str = Field(description="Target migration batch number.")
    batch_status: str = Field(description="Target migration batch status.")
    total_staged_rows: int = Field(description="Total staged rows in batch.")
    applied_movements_count: int = Field(
        description="Count of MIGRATION_OPENING_BALANCE movements."
    )
    reconciliation_status: str = Field(description="Overall status (MATCH or MISMATCH).")
    details: list[ReconciliationRowDetail] = Field(
        default_factory=list, description="Line item reconciliation details."
    )
