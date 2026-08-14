# Phase 5 Controlled Launch Checklist: Whitfield Operations Platform

This checklist is the formal launch gate for the Whitfield Fulfillment Warehouse Operations Platform.

---

## 1. Required Sign-offs

1. **Product Owner**: Confirms pilot sellers (Alpha, Beta), active warehouses (RENO, DAL), and migration source workbooks.
2. **Operations Lead**: Confirms all staged opening-inventory rows are validated with 0 errors.
3. **Warehouse Manager / Administrator**: Formally approves the clean migration batch.
4. **Engineering**: Verifies append-only `MIGRATION_OPENING_BALANCE` movements and confirms zero reconciliation variance.
5. **Security**: Verifies frontend secret audit passes, rate limiters are active, and no sensitive credentials exist in client bundles.

---

## 2. Technical Validation Gates

Run these commands from `C:\Partition\major_project`:

```powershell
# 1. Backend imports, compileall, and unit test suite
.\.venv\Scripts\python -c "import main; print('main import ok')"
.\.venv\Scripts\python -m compileall main.py common core cli tools tests
.\.venv\Scripts\python -m pytest

# 2. Frontend secret audit
.\.venv\Scripts\python tools/audit_frontend_secrets.py

# 3. Database migrations (Head: c1f2e3d4a5b6)
.\.venv\Scripts\alembic upgrade head
```

Then validate the frontend from `C:\Partition\major_project\frontend`:

```powershell
npm run typecheck
npm run build
```

---

## 3. Runtime Health Verification

Verify runtime operational status via HTTP:
```bash
# 1. Liveness check
GET /health/live -> 200 {"status": "live"}

# 2. Readiness check (DB connectivity)
GET /health/ready -> 200 {"status": "ready"}

# 3. Diagnostic health & Alembic revision
GET /health/status -> 200 {
  "status": "HEALTHY",
  "database": {"status": "connected"},
  "alembic_head": "c1f2e3d4a5b6",
  "ai": {"status": "HEALTHY" / "DISABLED"}
}

# 4. AI Provider Health
GET /api/v1/ai/admin/provider-health -> 200 {"status": "HEALTHY", "configured": true}
```

---

## 4. Controlled Launch Execution Sequence

1. **Apply Alembic Migrations**: Ensure database is at revision `c1f2e3d4a5b6`.
2. **Start Backend API Service**: Ensure environment validation passes with zero critical warnings.
3. **Verify Master Data**: Confirm Warehouses, Sellers, Products, and Locations are registered.
4. **Stage Opening Inventory**: Upload source workbook via UI (**Admin -> Migration**) or CLI.
5. **Validate Staged Rows**: Confirm `valid_rows == total_rows` and `invalid_rows == 0`.
6. **Approve & Apply**: As Warehouse Manager or Administrator, approve and apply the batch once.
7. **Reconcile Rehearsal**: Confirm 100% matched SKUs and zero discrepancies in the reconciliation report.
8. **Export Evidence**: From **Admin -> Controlled Launch & Health**, export and archive the signed launch evidence JSON bundle.

---

## 5. Rollback & Immutability Boundary

Opening inventory application is strictly append-only:
- Never edit or delete rows in `inventory_movements`.
- Any physical count adjustments post-launch must occur through approved, audited adjusting movements (`INVENTORY_ADJUSTMENT`) rather than mutating historical records.
