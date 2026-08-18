# Reconciliation & Inventory Operations Runbook: Whitfield Fulfillment Warehouse

## 1. Overview

Inventory integrity in the Whitfield platform is maintained through an append-only, double-entry inventory ledger (`inventory_movements`) and projected balance state (`inventory_balances`).

---

## 2. Reconciling Opening Inventory Migrations

### CLI Tool Workflow:
1. **Rehearse Batch**:
   ```bash
   python tools/rehearse_migration.py --batch-id <BATCH_UUID>
   ```
2. **Reconcile Rehearsal**:
   ```bash
   python tools/reconcile_migration.py --batch-id <BATCH_UUID>
   ```
3. **Verify Ledger Balances**:
   ```bash
   python tools/reconcile_inventory.py
   ```

### UI Workflow:
1. Navigate to **Admin -> Migration**.
2. Select or upload the target batch.
3. Click **Validate Staged Rows**. Ensure `invalid_rows == 0`.
4. Click **Approve Batch** followed by **Apply to Inventory Ledger**.
5. Inspect the generated **Reconciliation Report** showing 100% matched SKUs and zero discrepancies.

---

## 3. Discrepancy Handling & Variances

### Transfer Variances:
When received quantities differ from dispatched quantities at the destination warehouse:
1. Receiver records physical count (`received_good_quantity`, `received_damaged_quantity`, `missing_quantity`).
2. Transfer status moves to `DISCREPANCY_DETECTED`.
3. Warehouse Manager reviews transfer line notes and triggers `POST /api/v1/transfers/{id}/resolve-discrepancy`.
4. The system writes immutable balancing movements to adjust in-transit and destination balances.

### Return Inspection Variances:
1. Returns arriving at dock are received and placed into `INSPECTION` queue.
2. Receiver inspects items and assigns disposition quantities (`RESTOCK`, `REFURBISH`, `SCRAP`, `RETURN_TO_VENDOR`).
3. Completing the return dispatches inventory ledger movements according to disposition.

---

## 4. Background Jobs & SLA Monitoring

The platform executes autonomous background workers within the FastAPI ASGI lifecycle to maintain ledger integrity and enforce operational SLAs:

| Worker / Job Name | Implementation | Cadence | Purpose & Failure Handling |
|---|---|---|---|
| **Reservation Expiry Worker** | `core/jobs/reservation_expiry_job.py` | 60 seconds | Releases expired customer order inventory reservations (`RESERVED` -> `AVAILABLE`) back to stock. Safe on concurrent orders; skips orders already in physical fulfillment. |
| **Outbox Dispatch Worker** | `core/jobs/outbox_dispatch_job.py` | 10 seconds | Polls `outbox_events` in `PENDING` status, executes downstream event handlers, and marks `DISPATCHED`. Retries failures with exponential backoff; transitions to `DEAD_LETTER` after 5 failed attempts. |
| **Receipt Aging Job** | `core/jobs/receipt_aging_job.py` | 300 seconds | Detects inbound receipts in `DRAFT`/`IN_PROGRESS` exceeding 48h SLA threshold; emits `RECEIPT_AGING_ALERT` outbox events for dock manager escalation. |
| **Transfer Delay Job** | `core/jobs/transfer_delay_job.py` | 300 seconds | Scans in-transit transfers in `DISPATCHED` status exceeding expected transit SLA (default 7 days); emits `TRANSFER_DELAY_ALERT` outbox events. |
| **Return Aging Job** | `core/jobs/return_aging_job.py` | 300 seconds | Monitors customer returns received but uninspected past 24h SLA; emits `RETURN_AGING_ALERT` outbox events for QA lead triage. |

