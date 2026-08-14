"""
--------------------------------------------------------------------------------
File        : tests/unit/test_migration_flows.py
Purpose     : Unit and schema tests for opening inventory migration flows.

Responsibilities:
    - Validate migration request and response schema definitions.
    - Test MigrationBatchStatus, StagedRowValidationStatus, and InventoryMovementType enums.
    - Test hash computation and raw payload serialization.

Flow:
    pytest -> Migration schemas & constants -> Assertions

Used By:
    - pytest

Returns:
    test_*() -> None - Pytest assertion handlers.

Raises:
    AssertionError: If validation fails.
--------------------------------------------------------------------------------
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from core.apis.schemas.requests.migration_request import (
    CreateImportBatchRequest,
    StagedRowSubmitItem,
    SubmitStagedRowsRequest,
)
from core.apis.schemas.responses.migration_response import (
    ImportBatchResponse,
    MigrationReconciliationReportResponse,
    ReconciliationRowDetail,
    StagedRowResponse,
    ValidationSummaryResponse,
)
from core.constants import (
    AuditActionType,
    InventoryMovementType,
    MigrationBatchStatus,
    StagedRowValidationStatus,
)
from core.controllers.migration_controller import _compute_row_hash


def test_migration_enums() -> None:
    """Verify migration movement type, audit actions, and status enums."""
    assert InventoryMovementType.MIGRATION_OPENING_BALANCE.value == "MIGRATION_OPENING_BALANCE"
    assert MigrationBatchStatus.STAGED.value == "STAGED"
    assert MigrationBatchStatus.VALIDATED.value == "VALIDATED"
    assert MigrationBatchStatus.VALIDATION_FAILED.value == "VALIDATION_FAILED"
    assert MigrationBatchStatus.APPROVED.value == "APPROVED"
    assert MigrationBatchStatus.APPLIED.value == "APPLIED"
    assert StagedRowValidationStatus.PENDING.value == "PENDING"
    assert StagedRowValidationStatus.VALID.value == "VALID"
    assert StagedRowValidationStatus.INVALID.value == "INVALID"
    assert AuditActionType.MIGRATION_BATCH_CREATED.value == "MIGRATION_BATCH_CREATED"
    assert AuditActionType.MIGRATION_BATCH_APPLIED.value == "MIGRATION_BATCH_APPLIED"


def test_create_import_batch_request_schema() -> None:
    """Verify CreateImportBatchRequest validation."""
    req = CreateImportBatchRequest(source_notes="Baseline 2026 Reno")
    assert req.source_notes == "Baseline 2026 Reno"


def test_staged_row_submit_item_schema() -> None:
    """Verify StagedRowSubmitItem payload validation."""
    item = StagedRowSubmitItem(
        source_workbook="stock.xlsx",
        source_sheet="Sheet1",
        source_row_number=10,
        raw_seller_code="WHITFIELD",
        raw_sku="SKU-999",
        raw_warehouse_code="RENO",
        raw_inventory_state="AVAILABLE",
        raw_quantity="50.00",
    )
    assert item.source_workbook == "stock.xlsx"
    assert item.source_row_number == 10
    assert item.raw_quantity == "50.00"


def test_compute_row_hash_deterministic() -> None:
    """Verify SHA-256 hash computation is deterministic for raw item dicts."""
    item1 = {
        "source_workbook": "wb.xlsx",
        "source_sheet": "S1",
        "source_row_number": 5,
        "raw_seller_code": "WHITFIELD",
        "raw_sku": "SKU-1",
        "raw_warehouse_code": "RENO",
        "raw_inventory_state": "AVAILABLE",
        "raw_quantity": "10.00",
    }
    item2 = dict(item1)
    hash1 = _compute_row_hash(item1)
    hash2 = _compute_row_hash(item2)
    assert hash1 == hash2
    assert len(hash1) == 64


def test_migration_reconciliation_report_schema() -> None:
    """Verify MigrationReconciliationReportResponse serialization."""
    batch_id = uuid4()
    detail = ReconciliationRowDetail(
        seller_code="WHITFIELD",
        sku="SKU-1",
        warehouse_code="RENO",
        location_code=None,
        inventory_state="AVAILABLE",
        staged_approved_quantity=Decimal("100.00"),
        ledger_movement_quantity=Decimal("100.00"),
        balance_projection_quantity=Decimal("100.00"),
        variance_quantity=Decimal("0.00"),
        status="MATCH",
    )
    report = MigrationReconciliationReportResponse(
        batch_id=batch_id,
        batch_number="BATCH-20260813-001",
        batch_status="APPLIED",
        total_staged_rows=1,
        applied_movements_count=1,
        reconciliation_status="MATCH",
        details=[detail],
    )
    assert report.batch_id == batch_id
    assert report.reconciliation_status == "MATCH"
    assert report.details[0].variance_quantity == Decimal("0.00")
