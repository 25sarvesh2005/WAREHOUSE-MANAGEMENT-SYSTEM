# Phase 5 Opening Inventory Migration, Reconciliation & Cutover Runbook

## System Authority & Purpose
This runbook governs the opening inventory migration, rehearsal validation, reconciliation sign-off, rollback boundary, and controlled pilot cutover for the Whitfield Fulfillment Warehouse Operations Platform.

As specified in **IMPLEMENTATION.md Section 18**, the transactional database and append-only inventory movement ledger (`inventory_movements`) constitute the operational source of truth upon cutover. Spreadsheet workbooks are used solely for controlled migration staging and historical comparison.

---

## 1. Opening Inventory Migration Rehearsal Procedure

### 1.1 Prerequisites
1. Seller master data, product SKUs, warehouse locations, and operational policies are fully loaded and validated in the target environment.
2. The operator holds `ADMINISTRATOR` or `WAREHOUSE_MANAGER` role privileges.
3. Source spreadsheet workbooks are normalized and catalog identifiers (SKU, UPC, Seller Code, Warehouse Code) match master data exactly.

### 1.2 Step-by-Step Rehearsal Workflow
1. **Create Import Batch Header**
   ```http
   POST /api/v1/migration/batches
   Body: { "source_notes": "Rehearsal Batch 2026-08-13 Reno Baseline" }
   ```
2. **Submit Staged Rows**
   Operators may stage rows from a controlled CSV/XLSX source file:
   ```http
   POST /api/v1/migration/batches/{batch_id}/upload
   Form field: file=<opening_inventory.csv|opening_inventory.xlsx>
   ```
   Or submit JSON rows directly:
   ```http
   POST /api/v1/migration/batches/{batch_id}/rows
   Body: { "rows": [ { "source_workbook": "reno_opening.xlsx", "source_sheet": "Sheet1", "source_row_number": 2, "raw_seller_code": "WHITFIELD", "raw_sku": "SKU-100", "raw_warehouse_code": "RENO", "raw_inventory_state": "AVAILABLE", "raw_quantity": "150.00" } ] }
   ```
   - Upload/stage does **not** validate, approve, apply, create movements, or update balances.
   - Upload/stage only creates staged evidence rows for later validation.
3. **Execute Batch Validation**
   ```http
   POST /api/v1/migration/batches/{batch_id}/validate
   ```
   - Inspect summary: Ensure `invalid_rows == 0` and `status == "VALIDATED"`.
   - If `invalid_rows > 0`, resolve missing catalog records or correct raw spreadsheet data and re-submit/re-validate.
4. **Approve Batch**
   ```http
   POST /api/v1/migration/batches/{batch_id}/approve
   ```
   - Approver must hold `WAREHOUSE_MANAGER` (assigned to target warehouse) or `ADMINISTRATOR` role.
5. **Apply Opening Inventory to Ledger**
   ```http
   POST /api/v1/migration/batches/{batch_id}/apply
   ```
   - Creates append-only `InventoryMovement` entries with `movement_type = "MIGRATION_OPENING_BALANCE"`.
   - Atomically updates operational `InventoryBalance` projections.
6. **Generate Rehearsal Reconciliation Report**
   ```http
   GET /api/v1/migration/batches/{batch_id}/reconciliation
   ```
   - Confirm `reconciliation_status == "MATCH"` and zero variance across all staged vs ledger line items.

---

## 2. Source File Template

### 2.1 Supported formats
- `.csv`
- `.xlsx`

Unsupported file types are rejected before staging.

### 2.2 Required columns
The first row of every CSV sheet or XLSX worksheet must include:

| Column | Required | Notes |
|---|---:|---|
| `seller_code` | Yes | Must match active seller master data during validation. |
| `sku` | Yes | Must match active product master data during validation. |
| `warehouse_code` | Yes | Must match active warehouse master data during validation. |
| `inventory_state` | Yes | Must match allowed platform inventory states. |
| `quantity` | Yes | Must be greater than zero during validation. |
| `upc` | No | Preserved as raw evidence when present. |
| `location_code` | No | Validated when present. |

Header names are matched by lowercasing and replacing spaces/hyphens with underscores.
Do not use ambiguous duplicate header names.

### 2.3 Source evidence preservation
For every staged source row, the platform preserves:
- source workbook/file name
- source sheet name
- original source row number
- source content hash
- raw seller, SKU, UPC, warehouse, location, state, and quantity values

Fully empty rows are skipped. Invalid business values are still staged when the file
shape is usable, so validation reports can identify and explain bad rows.

### 2.4 CLI file import
Operators may stage a local file into an existing batch:

```bash
python -m tools.import_opening_inventory --batch-id <BATCH_UUID> --file opening.csv
```

This command never approves, applies, creates inventory movements, or updates balances.

---

## 3. Failed Migration Rollback Boundary

### 3.1 Pre-Apply Rollback (Uncommitted Staging)
- Prior to batch application (`status` in `STAGED`, `VALIDATED`, or `VALIDATION_FAILED`), no operational inventory movements or balance projections have been created.
- To abort a batch, mark the batch status as `REJECTED` or delete/discard the staged batch.
- **Rollback Cost:** Zero operational risk. Spreadsheets may be edited and re-submitted.

### 3.2 Post-Apply Rollback Boundary (Strict Rule)
> [!CAUTION]
> **CRITICAL ROLLBACK BOUNDARY POLICY:**
> - Once an opening inventory batch is applied (`status == "APPLIED"`) and live operational transactions (receipts, reservations, picks, shipments) begin, **rollback CANNOT mean silently returning to editable spreadsheets.**
> - Spreadsheet workbooks become strictly **read-only** for the pilot operational scope.
> - The append-only `inventory_movements` ledger remains the sole audit authority for all accepted events.
> - If an applied migration batch contains errors discovered after live transactions commence:
>   1. **Do not modify past ledger rows.**
>   2. Export a ledger-derived operational snapshot.
>   3. Execute audited manager compensating adjustments (`POST /api/v1/inventory/adjustments`) with explicit reason codes and approval.

---

## 4. Reconciliation Sign-Off Procedure

Before granting pilot cutover approval:
1. Run the reconciliation report tool:
   ```bash
   python -m tools.reconcile_migration --batch-id <BATCH_UUID>
   ```
2. Verify:
   - 100% of staged rows have `validation_status == "VALID"`.
   - `reconciliation_status == "MATCH"`.
   - Sum of staged quantities matches total `MIGRATION_OPENING_BALANCE` movement deltas.
   - Projection balances equal ledger-rebuilt totals.
3. Both the Implementation Lead and Warehouse Manager must sign off on the reconciliation report artifacts before cutover.

---

## 5. Pilot Cutover Checklist

- [ ] Master Data Verification: All sellers, SKUs, warehouses, locations, and policies verified.
- [ ] Source Spreadsheet Freeze: Opening inventory workbooks locked and SHA-256 hashed.
- [ ] Migration Rehearsal: Successful rehearsal run performed in staging environment.
- [ ] Staging & Validation: Import batch created, staged rows submitted, and 0 invalid rows confirmed.
- [ ] Manager Approval: Authorized `WAREHOUSE_MANAGER` or `ADMINISTRATOR` approved batch.
- [ ] Ledger Application: Opening inventory applied atomically with `MIGRATION_OPENING_BALANCE` movements.
- [ ] Post-Apply Reconciliation: Report generated with status `MATCH` and signed off.
- [ ] Spreadsheet Read-Only Transition: Access rights updated; Excel marked read-only for pilot warehouse scope.
- [ ] Live Transaction Authorization: Operational workflows (receiving, order reservation, picking) enabled in platform.
