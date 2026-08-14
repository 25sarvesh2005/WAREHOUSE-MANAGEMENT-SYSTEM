# Whitfield Fulfillment Warehouse Operations Platform

## Complete Implementation Specification

**Document type:** Engineering implementation authority  
**Audience:** Founders, warehouse operators, product owners, solution architects, backend/frontend engineers, QA, DevOps, and implementation partners  
**System:** Multi-warehouse warehouse management and seller visibility platform  
**Locations:** Reno, Nevada and Columbus, Ohio  
**Primary outcome:** Replace spreadsheet-based operations with accurate, transactional, auditable inventory and fulfillment workflows  
**Architecture authority:** This document, followed by the approved source requirements and repository engineering standards  

---

## 1. Purpose and Implementation Authority

This document is the implementation authority for the Whitfield Fulfillment warehouse operations platform. It translates the case study and approved client implementation plan into a buildable software design while applying the CityCare-style project architecture and Eigi backend/frontend engineering standards.

The platform becomes the operational source of truth for inventory. Excel is used only for controlled migration, pilot reconciliation, and historical reference after cutover. Inventory is never represented as an unaudited editable number. Every stock change is explained by an immutable inventory movement created by a permitted workflow.

### 1.1 Precedence rules

When requirements conflict, apply them in this order:

1. Explicit user decisions in the current project.
2. Warehouse case-study facts and approved operational behavior.
3. The existing Warehouse Operations Application Implementation Plan.
4. CityCare architecture conventions, adapted to PostgreSQL.
5. Eigi backend and frontend standards.
6. The closest established convention in the implemented repository.

### 1.2 Resolved source conflicts

| Topic | Decision | Reason |
|---|---|---|
| Database | PostgreSQL 16+ | Explicit project decision; relational integrity, transaction isolation, reporting, and workflow complexity favor PostgreSQL. |
| ORM | SQLAlchemy 2.x async with `asyncpg` | Replaces ODMantic/Motor while preserving the model -> CRUD -> controller layering. |
| Database access | CRUD functions receive `AsyncSession` as the first argument | Adapts the CityCare engine-first rule to safe unit-of-work transaction handling. Routes never access sessions directly except through controller-owned transaction dependencies. |
| Logger import | `from common.logger import get_logger` | Project-specific CityCare convention takes precedence over the generic Eigi logger example. |
| Authentication in routes | FastAPI dependencies (`get_current_user`, `get_warehouse_scope`) | Project-specific rule takes precedence over token decoding inside route bodies. |
| Frontend routing | Vite + React + TypeScript + TanStack Router | Defined by the project codex. |
| Hardware | Deferred adapters with manual browser fallbacks | Hardware is not a prerequisite for the core release. |
| AI | Read-only assistance first; no autonomous inventory mutation | Core operational accuracy must exist before AI features are enabled. |

### 1.3 Non-negotiable outcomes

- A completed receipt cannot be applied twice without a manager-approved, audited exception.
- Concurrent orders cannot reserve the same last available units.
- Every stock change has an actor, timestamp, reason, source workflow, and source record.
- Damaged, quarantined, returned-uninspected, and in-transit units are not sellable.
- Inventory is isolated by seller, SKU, warehouse, location, lot when applicable, and inventory state.
- Sellers can access only their own records.
- Warehouse workers can access only assigned warehouses and permitted actions.
- Excel becomes read-only when a warehouse completes cutover.
- Offline receiving creates drafts only; central stock changes only after the server accepts synchronization.
- AI cannot directly mutate inventory, orders, transfers, shipments, returns, or seller communications.

---

## 2. Scope

### 2.1 Core release scope

The core release includes:

- Secure authentication and role-based access.
- Seller, user, warehouse, location, product, SKU, UPC, and seller-policy master data.
- Immutable inventory movement ledger and query-optimized inventory balances.
- Carrier-tracking and seller-ticket receiving.
- Receipt drafts, completion, cancellation, shortages, overages, damage, and quarantine.
- Order creation/import, transactional inventory reservation, picking, packing, shipping, and exceptions.
- Seller-specific backorder, partial-fulfillment, and reservation-expiry behavior.
- Reno-to-Columbus and Columbus-to-Reno transfers.
- Expected and unidentified return intake, inspection, disposition, and closure.
- Seller portal for inventory, receipts, orders, shipments, returns, and transfers relevant to that seller.
- Manager operational dashboard and exception queues.
- Audit history for business, permission, policy, and administrative actions.
- Offline-safe receipt drafting and duplicate-safe synchronization.
- Migration tooling, reconciliation reports, controlled pilot, and cutover controls.
- Monitoring, backups, restore validation, error alerts, rollback procedures, and runbooks.

### 2.2 Deferred integrations

- Barcode-scanner model-specific adapters.
- Carrier APIs and native label printing.
- Scales and dimensioners.
- Marketplace and external order-source webhooks/APIs.
- Voice-assisted receiving.
- Autonomous or mutation-capable AI.

The core application must expose stable integration boundaries so these additions do not require redesigning inventory or fulfillment domain models.

### 2.3 Explicitly out of scope for the first production release

- Fully disconnected inventory reservation or shipment confirmation.
- AI-generated stock adjustments.
- AI-confirmed orders, transfers, returns, or shipments.
- Direct seller access to another seller's records.
- Silent inventory edits, hard deletion of ledger rows, or retroactive mutation of completed operational records.
- Hardware procurement or warehouse-network installation.

---

## 3. Technology Stack

| Layer | Technology |
|---|---|
| Backend API | Python 3.11+, FastAPI, Uvicorn |
| Persistence | PostgreSQL 16+ |
| ORM and migrations | SQLAlchemy 2.x async, Alembic |
| Async PostgreSQL driver | `asyncpg` |
| Validation | Pydantic v2 |
| Authentication | `python-jose`, bcrypt through `passlib`/`bcrypt` |
| HTTP client | `httpx.AsyncClient` |
| Background work | PostgreSQL-backed job/outbox worker initially; optional Celery/Redis only when scale requires it |
| Frontend | Vite, React, TypeScript, TanStack Router |
| Frontend state/data | TanStack Query; local feature state; Zustand only for justified cross-route client state |
| Offline receipt drafts | IndexedDB with a versioned local schema and sync queue |
| Testing | pytest, pytest-asyncio, HTTPX ASGITransport, Testcontainers/PostgreSQL, Vitest, React Testing Library, Playwright |
| PDF/report generation | ReportLab when server-generated documents are required |
| File storage | Cloudinary or an approved object-store adapter; no provider logic in controllers |
| AI/LLM | `google-genai` behind a provider service |
| RAG | ChromaDB and approved LangChain integrations, isolated from transactional data |
| MCP server | FastMCP with streamable HTTP |
| CLI | Typer or argparse; Typer is preferred |
| Environment loading | `python-dotenv` for local development; secret manager/environment injection in deployed environments |
| Observability | Structured application logs, metrics, traces, health checks, and alerting |

### 3.1 PostgreSQL extensions

Enable only where used:

- `pgcrypto` for `gen_random_uuid()`.
- `citext` for case-insensitive email and selected business identifiers.
- `btree_gist` if exclusion constraints are introduced.
- `pg_trgm` for operator search when normal indexed prefix search is insufficient.

---

## 4. System Context and Request Flow

```mermaid
flowchart LR
    U["Warehouse staff / managers / sellers"] --> FE["React web application"]
    FE --> API["FastAPI routes"]
    CLI["Operational CLI"] --> C["Controllers"]
    MCP["FastMCP server"] --> API
    API --> C
    C --> S["Domain and integration services"]
    C --> CRUD["CRUD / repositories"]
    S --> CRUD
    CRUD --> PG[("PostgreSQL")]
    C --> OUTBOX["Transactional outbox"]
    OUTBOX --> WORKER["Background worker"]
    WORKER --> EXT["Carrier / storage / notification providers"]
    AI["Read-only AI assistant"] --> TOOLS["Permission-aware application tools"]
    TOOLS --> API
```

Mandatory HTTP request flow:

```text
HTTP request
  -> route handler
     - validates request schema
     - authenticates through Depends(...)
     - obtains seller/warehouse permission scope
     - calls controller
     - re-raises HTTPException
     - converts unknown errors to a generic 500
  -> controller
     - opens or joins the transaction unit of work
     - applies authorization and business rules
     - calls CRUD and services
     - returns response-ready domain data
  -> CRUD/repository
     - performs SQLAlchemy/PostgreSQL operations only
     - applies row locks when requested by the controller workflow
     - never raises HTTPException
  -> PostgreSQL
```

Dependency direction is strict:

```text
routes -> controllers -> CRUD/models
                     -> services -> provider clients
```

Routes do not query the database. CRUD modules do not contain business policy. Services do not parse FastAPI requests or raise `HTTPException`.

---

## 5. Repository Structure

```text
warehouse-operations/
|-- main.py
|-- requirements.txt
|-- pyproject.toml
|-- alembic.ini
|-- .env.example
|-- .gitignore
|-- README.md
|-- IMPLEMENTATION.md
|-- common/
|   |-- __init__.py
|   |-- auth.py
|   |-- logger.py
|   |-- warehouse_scope.py
|   |-- idempotency.py
|   `-- pagination.py
|-- core/
|   |-- __init__.py
|   |-- constants.py
|   |-- config/
|   |   `-- settings.py
|   |-- database/
|   |   |-- database.py
|   |   |-- base.py
|   |   |-- migrations/
|   |   `-- seed.py
|   |-- models/
|   |   |-- identity_model.py
|   |   |-- catalog_model.py
|   |   |-- inventory_model.py
|   |   |-- receiving_model.py
|   |   |-- order_model.py
|   |   |-- shipment_model.py
|   |   |-- transfer_model.py
|   |   |-- return_model.py
|   |   |-- audit_model.py
|   |   `-- outbox_model.py
|   |-- cruds/
|   |   |-- identity_crud.py
|   |   |-- catalog_crud.py
|   |   |-- inventory_crud.py
|   |   |-- receipt_crud.py
|   |   |-- order_crud.py
|   |   |-- shipment_crud.py
|   |   |-- transfer_crud.py
|   |   |-- return_crud.py
|   |   `-- audit_crud.py
|   |-- controllers/
|   |   |-- identity_controller.py
|   |   |-- catalog_controller.py
|   |   |-- receipt_controller.py
|   |   |-- inventory_controller.py
|   |   |-- order_controller.py
|   |   |-- fulfillment_controller.py
|   |   |-- transfer_controller.py
|   |   |-- return_controller.py
|   |   |-- seller_portal_controller.py
|   |   `-- reporting_controller.py
|   |-- services/
|   |   |-- inventory/
|   |   |   |-- ledger_service.py
|   |   |   |-- allocation_service.py
|   |   |   `-- reconciliation_service.py
|   |   |-- carrier/
|   |   |   |-- service.py
|   |   |   |-- client.py
|   |   |   `-- providers/
|   |   |-- storage/
|   |   |-- notification/
|   |   |-- import_export/
|   |   `-- jobs/
|   |-- jobs/
|   |   |-- worker.py
|   |   |-- reservation_expiry_job.py
|   |   |-- outbox_dispatch_job.py
|   |   `-- exception_detection_job.py
|   |-- apis/
|   |   |-- api.py
|   |   |-- routes/
|   |   `-- schemas/
|   |       |-- requests/
|   |       `-- responses/
|   `-- utils/
|-- chatbot/
|   |-- gemini_client.py
|   |-- rag_service.py
|   |-- tools.py
|   |-- warehouse_assistant.py
|   |-- models/
|   |-- schemas/
|   |-- controllers/
|   |-- cruds/
|   `-- routes/
|-- mcp_server/
|   |-- server.py
|   `-- tools/
|       |-- auth.py
|       |-- inventory_tools.py
|       |-- order_tools.py
|       `-- exception_tools.py
|-- cli/
|   |-- main.py
|   `-- commands/
|-- scripts/
|   |-- migrate_db.py
|   |-- import_opening_inventory.py
|   |-- reconcile_inventory.py
|   `-- ingest_docs.py
|-- tests/
|   |-- conftest.py
|   |-- unit/
|   |-- integration/
|   `-- e2e/
|-- data/
|-- logs/
|-- tmp/
`-- warehouse-web/
    |-- package.json
    |-- vite.config.ts
    |-- .env.example
    |-- src/
    |   |-- routes/
    |   |-- features/
    |   |-- components/
    |   |   |-- ui/
    |   |   |-- layout/
    |   |   `-- forms/
    |   |-- lib/api/
    |   |-- hooks/
    |   |-- stores/
    |   |-- styles/
    |   |-- types/
    |   |-- utils/
    |   `-- assets/
    `-- tests/
```

### 5.1 Backend file rules

- Every Python file begins with the project banner docstring containing file path, purpose, responsibilities, flow, used-by modules, returns, and raises.
- Every function and method has a complete docstring with a two-line purpose/behavior introduction and applicable `Args`, `Returns`, and `Raises` sections.
- Every function and method has complete type annotations.
- Use section-divider comments consistently.
- Never use `print()` in backend application code.
- Never log secrets, raw tokens, passwords, private prompts, full sensitive request bodies, or provider credentials.
- Models own persistence shape; Pydantic schemas own transport shape.
- New routers are registered in `core/apis/api.py`.

### 5.2 Required `.gitignore` baseline

```gitignore
.git/
.env
.env.*
!.env.example
venv/
.venv/
__pycache__/
*.py[cod]
.pytest_cache/
.mypy_cache/
.ruff_cache/
htmlcov/
.coverage
coverage/
dist/
build/
*.egg-info/
node_modules/
.vite/
playwright-report/
test-results/
logs/
*.log
tmp/
*.sqlite*
.DS_Store
.idea/
.vscode/
.vercel/
.netlify/
```

---

## 6. Identity, Tenancy, Roles, and Authorization

### 6.1 Tenancy model

The seller is the primary data tenant. Warehouses are shared operational facilities. A user's effective permission is the intersection of:

- Role capability.
- Assigned seller scope, if any.
- Assigned warehouse scope, if any.
- Record-specific ownership and workflow state.

Tenant and warehouse identifiers are derived from authenticated assignments, never trusted from a request body.

### 6.2 Roles

| Role | Primary permissions | Restrictions |
|---|---|---|
| Receiver | Create/edit receipt drafts, record counts/condition, complete normal receipts | Cannot approve major adjustments, duplicate overrides, or transfer discrepancies |
| Picker/Packer | View assigned work, pick, short-pick, pack, enter dimensions/weight, record shipment progress | Cannot edit inventory totals, policies, or other sellers' work |
| Warehouse Manager | Approve adjustments, resolve exceptions, manage returns/transfers, view assigned warehouse reporting | Limited to assigned warehouses unless explicitly granted broader access |
| Seller | Read own inventory, receipts, orders, shipments, returns; create expected returns when enabled | Cannot view another seller or mutate warehouse inventory directly |
| Administrator | Manage users, sellers, products, warehouse configuration, assignments, policies | All administrative actions remain audited; operational overrides still require reasons |
| Service Account | Execute explicitly granted API/MCP/CLI scopes | No interactive privileges; least privilege; secret rotation required |

### 6.3 Permission strategy

- Backend authorization is authoritative; frontend visibility is convenience only.
- Every seller-scoped query includes `seller_id` from the permission context.
- Every warehouse-scoped operation checks an active assignment.
- Administrators are not implicitly exempt from audit, idempotency, or state-transition rules.
- PostgreSQL row-level security may be added as defense in depth, but application-level scoped queries remain mandatory.
- Permission denials return `403`; unauthenticated/invalid sessions return `401`; concealed cross-tenant records may return `404` where existence must not be disclosed.

### 6.4 JWT contract

JWT payload contains:

```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "name": "User Name",
  "role": "WAREHOUSE_MANAGER",
  "seller_ids": ["uuid"],
  "warehouse_ids": ["uuid"],
  "token_version": 3,
  "exp": 0
}
```

Use short-lived access tokens and an approved refresh-token/session strategy. Store refresh-token hashes, not raw values. `token_version` permits immediate revocation after password or permission changes.

---

## 7. Domain Model and PostgreSQL Schema

### 7.1 Database conventions

- Primary keys are UUIDs generated by PostgreSQL.
- All timestamps are `timestamptz` stored in UTC.
- Business timestamps are named explicitly: `received_at`, `reserved_at`, `dispatched_at`, etc.
- Monetary amounts use `numeric`, never floating point.
- Quantities use `numeric(18,4)` to support future non-integer units; current product policy may enforce whole units.
- Status/type columns use PostgreSQL enums only when operational migration cost is acceptable; otherwise use constrained strings with application enums.
- Completed transactional records are soft-closed, never hard-deleted.
- Mutable master data uses `is_active` or `archived_at`.
- Every externally retryable command has an idempotency key.
- Optimistic concurrency uses a `version` integer on mutable aggregate roots.
- Foreign keys are explicit and indexed according to access patterns.

### 7.2 Identity and access tables

#### `users`

- `id`, `email` (`citext`, unique), `name`, `hashed_password`, `role`, `status`.
- `token_version`, `last_login_at`, `created_at`, `updated_at`.
- Never returned with `hashed_password`.

#### `sellers`

- `id`, `code`, `name`, contact fields, `status`, `created_at`, `updated_at`.
- Unique active seller code.

#### `warehouses`

- `id`, `code`, `name`, address fields, timezone, `status`.
- Seed Reno and Columbus as separate records.

#### `user_seller_assignments`

- `user_id`, `seller_id`, assignment role/scope, `created_at`, `revoked_at`.
- Unique active assignment per user/seller/scope.

#### `user_warehouse_assignments`

- `user_id`, `warehouse_id`, assignment role/scope, `created_at`, `revoked_at`.
- Unique active assignment per user/warehouse/scope.

#### `service_accounts` and `service_account_scopes`

- Store client identifiers, hashed credentials, status, expiry, and narrow scopes.

### 7.3 Catalog and policy tables

#### `products`

- `id`, `seller_id`, `sku`, `name`, description, unit-of-measure, dimensional defaults, status.
- Unique `(seller_id, sku)`.

#### `product_identifiers`

- `id`, `product_id`, `identifier_type` (`UPC`, `EAN`, `SELLER_CODE`, etc.), `identifier_value`, `is_primary`.
- Unique normalized `(identifier_type, identifier_value)` where business rules require global uniqueness.

#### `warehouse_locations`

- `id`, `warehouse_id`, location code, type, status.
- Unique `(warehouse_id, code)`.
- Types include receiving, storage, picking, packing, quarantine, damage, return inspection, and transfer staging.

#### `seller_order_policies`

- `seller_id`, `allow_backorder`, `allow_partial_fulfillment`, `reservation_expiry_minutes`, allocation strategy, cancellation policy, effective dates, version.
- Policy changes are audited and never silently rewrite existing confirmed order behavior.

#### `approval_policies`

- Per seller/warehouse thresholds for adjustment quantities, transfer variances, duplicate receipt overrides, and return exceptions.

### 7.4 Inventory ledger tables

#### `inventory_movements`

This table is append-only and authoritative.

Key columns:

- `id` UUID.
- `seller_id`, `product_id`, `warehouse_id`.
- `location_id` nullable where movement is warehouse-level.
- `inventory_state`: `AVAILABLE`, `RESERVED`, `DAMAGED`, `QUARANTINED`, `RETURN_INSPECTION`, `IN_TRANSIT`, `SHIPPED`, or other approved state.
- `quantity_delta` signed numeric.
- `movement_type`: receipt, reservation, reservation release, pick, short-pick correction, shipment, return disposition, transfer dispatch, transfer receipt, adjustment, migration opening balance.
- `source_type`, `source_id`, `source_line_id`.
- `idempotency_key`.
- `reason_code`, `reason_text`.
- `actor_user_id` or `actor_service_account_id`.
- `correlation_id`, `occurred_at`, `recorded_at`.
- `reversal_of_movement_id` nullable.

Constraints:

- `quantity_delta <> 0`.
- Exactly one actor identity is present for interactive/system events as applicable.
- Unique `(source_type, source_line_id, movement_type, idempotency_key)` for retry safety.
- Ledger rows cannot be updated or deleted by the application role; corrections create compensating movements.

#### `inventory_balances`

This is the fast operational projection, updated in the same database transaction as ledger insertion.

- Composite unique key: `(seller_id, product_id, warehouse_id, location_id, inventory_state)`.
- `quantity`, `version`, `updated_at`.
- `quantity >= 0` for controlled states unless an explicitly approved migration/reconciliation procedure is active.
- Queries for reservation acquire `SELECT ... FOR UPDATE` on the relevant balance rows.

#### `inventory_adjustments`

- Adjustment request, reason, requested quantities, approval state, requester, approver, timestamps, and linked movement IDs.
- No adjustment is applied before required approval.

#### `inventory_reconciliations`

- Warehouse/seller scope, snapshot time, counted quantity, ledger quantity, variance, status, investigator, resolution, linked adjustments.

### 7.5 Receiving tables

#### `receipts`

- `id`, human-readable receipt number, seller, warehouse.
- `source_type`: carrier tracking or seller drop-off ticket.
- Normalized `source_reference`.
- `client_draft_id` for offline synchronization.
- Status: `DRAFT`, `IN_PROGRESS`, `PENDING_REVIEW`, `COMPLETED`, `CANCELLED`.
- Expected/actual arrival timestamps, started/completed users, version, timestamps.

Duplicate protection:

- A partial unique index prevents more than one completed receipt for `(warehouse_id, normalized source_type, normalized source_reference)` under the normal path.
- A duplicate override requires manager permission, a reason, and a reference to the original receipt.
- `client_draft_id` is unique per originating client/device identity.

#### `receipt_lines`

- Product/SKU/UPC reference, expected quantity if known.
- Sellable, damaged, quarantined, shortage, and overage quantities.
- Lot/expiry/serial fields when enabled.
- Condition notes and evidence attachment references.
- Completion creates separate movements by inventory state.

#### `receipt_events`

- Append-only workflow event stream for start, line updates, review, override, complete, cancel, sync conflict, and correction.

### 7.6 Order and reservation tables

#### `orders`

- `id`, seller, seller order number, warehouse assignment, channel/source.
- Status: `DRAFT`, `PENDING_RESERVATION`, `PARTIALLY_RESERVED`, `RESERVED`, `BACKORDERED`, `PICKING`, `PACKED`, `SHIPPED`, `PARTIALLY_SHIPPED`, `CANCELLED`, `CLOSED`.
- Policy snapshot columns or `policy_snapshot` JSONB capturing the exact policy applied at confirmation.
- Idempotency/source import identifiers.
- Unique `(seller_id, seller_order_number)` unless a defined version/replacement workflow exists.

#### `order_lines`

- Product, ordered quantity, reserved quantity, picked quantity, shipped quantity, backordered quantity, cancelled quantity.
- Quantity conservation constraint enforced by controller plus database checks where feasible.

#### `inventory_reservations`

- Order line, warehouse/product, quantity, status, reserved/expiry/released timestamps.
- Active reservations are backed by matching available-to-reserved ledger movements.
- Expiry/release uses idempotent compensating movements.

### 7.7 Fulfillment and shipment tables

#### `pick_tasks` and `pick_task_lines`

- Warehouse assignment, worker assignment, priority, status.
- Source and destination locations, requested/picked/short quantities.
- Short pick always creates an exception and triggers reservation/order re-evaluation.

#### `packages`

- Shipment association, weight, dimensions, packaging type.
- Manual measurements supported initially.

#### `shipments`

- Order, warehouse, carrier, service, tracking number, label mode, status, shipped/picked-up timestamps.
- Manual tracking is supported before carrier integration.
- Shipment completion moves inventory out of reserved/fulfillment state and retains full history.

#### `shipment_events`

- Append-only label, pack, handoff, pickup, tracking, failure, and cancellation events.

### 7.8 Transfer tables

#### `transfers`

- Origin and destination warehouse, status, creator, approver, dispatched/received timestamps.
- Status: `DRAFT`, `PENDING_APPROVAL`, `APPROVED`, `DISPATCHED`, `PARTIALLY_RECEIVED`, `RECEIVED`, `DISCREPANCY_REVIEW`, `CANCELLED`.
- Origin and destination must differ.

#### `transfer_lines`

- Product, requested, approved, dispatched, received-good, received-damaged, missing, and overage quantities.

Behavior:

- Dispatch moves stock from origin available/staged state to `IN_TRANSIT`.
- In-transit stock is not sellable at either warehouse.
- Receipt removes `IN_TRANSIT` and adds destination state-specific quantities.
- Variances remain open until an approved resolution produces explicit movements.

### 7.9 Return tables

#### `returns`

- Seller, warehouse, optional original order/shipment, return authorization number, inbound tracking.
- Status: `EXPECTED`, `RECEIVED`, `INSPECTION`, `PARTIALLY_DISPOSED`, `COMPLETED`, `REJECTED`, `UNIDENTIFIED`.

#### `return_lines`

- Product if identified, expected quantity, received quantity, disposition quantities, reason, inspection notes.

Behavior:

- Receipt of a return never automatically adds available stock.
- Unidentified or uninspected inventory enters `RETURN_INSPECTION` or `QUARANTINED`.
- Inspection creates explicit movements into available, damaged, quarantined, rejected, or other approved disposition states.

### 7.10 Audit and asynchronous processing tables

#### `audit_events`

- Actor, action, aggregate type/id, seller/warehouse scope, request/correlation ID, timestamp.
- Sanitized before/after metadata or change summary.
- Permission changes, policy changes, approvals, exceptions, imports, and AI operations are included.

#### `idempotency_records`

- Scope, key, request hash, response status/body reference, state, expiry.
- Reusing a key with a different request hash returns `409`.

#### `outbox_events`

- Event type, aggregate type/id, payload, creation/publish timestamps, attempt count, next attempt, last error.
- Inserted in the same transaction as business state.
- Worker delivery is at least once; consumers must be idempotent.

#### `background_jobs`

- Job type, payload, status, schedule, lease owner/expiry, attempts, errors.
- Worker claims jobs with `FOR UPDATE SKIP LOCKED`.

---

## 8. Inventory Accounting and Transaction Rules

### 8.1 Quantity invariants

For a product/seller/warehouse scope:

```text
physical accountable quantity
  = available
  + reserved
  + damaged
  + quarantined
  + return inspection
  + transfer staging

network accountable quantity
  = sum(warehouse physical accountable quantity)
  + in transit
```

`SHIPPED` is historical and not on-hand. Orders do not reduce stock at creation; reservation moves available to reserved. Shipment removes reserved stock from on-hand accountability.

### 8.2 Ledger write algorithm

Every inventory-changing workflow must:

1. Begin a PostgreSQL transaction.
2. Validate actor permission and aggregate state.
3. Acquire balance row locks in deterministic order to avoid deadlocks.
4. Verify quantity/state invariants.
5. Insert immutable movement rows.
6. Upsert/update corresponding balance rows.
7. Update the workflow aggregate and version.
8. Insert audit and outbox events.
9. Commit once.

If any step fails, the entire transaction rolls back.

### 8.3 Concurrent last-unit reservation

For each order line:

```sql
SELECT quantity
FROM inventory_balances
WHERE seller_id = :seller_id
  AND product_id = :product_id
  AND warehouse_id = :warehouse_id
  AND inventory_state = 'AVAILABLE'
FOR UPDATE;
```

The controller then applies the seller's snapshotted policy:

- Enough stock: reserve requested quantity.
- Insufficient stock + partial allowed: reserve available portion and backorder/cancel remainder per policy.
- Insufficient stock + backorder allowed: create backorder without over-reserving.
- Neither allowed: reject confirmation with an operational `409` response and permitted next actions.

The balance update and available-to-reserved ledger movements occur in the same transaction. No cache or application mutex is accepted as the inventory correctness mechanism.

### 8.4 Corrections and reversals

- Ledger rows are never edited.
- An erroneous movement is corrected by an authorized compensating movement linked through `reversal_of_movement_id`.
- Completed receipts/orders/transfers/returns are not reopened casually. Corrections use dedicated workflows with reasons and approvals.
- Database roles deny `UPDATE`/`DELETE` on `inventory_movements` to normal application identities.

### 8.5 Reconciliation

- Rebuild balances from the ledger in a read-only verification job.
- Compare rebuilt balances with `inventory_balances`.
- Any mismatch opens a critical exception; it is never silently repaired.
- Approved repair updates the projection from the ledger or creates an adjustment if the real-world count differs.

---

## 9. Workflow Specifications

### 9.1 Receiving

1. Start a receipt with carrier tracking number or seller drop-off ticket.
2. Normalize and check the source reference against completed receipts.
3. Search/scan UPC or enter seller SKU manually.
4. Record sellable, damaged, quarantined, shortage, and overage quantities separately.
5. Save as a draft repeatedly using optimistic concurrency.
6. On completion, validate lines, permissions, duplicate state, and required exception reasons.
7. Create inventory movements per line and state.
8. Update inventory balances and mark the receipt completed atomically.
9. Publish receipt-completed events for seller visibility and downstream notifications.

Cancellation of a draft creates no stock movement. A completed receipt requires a correction workflow, not cancellation.

### 9.2 Offline receipt drafting

- The web app generates a UUID `client_draft_id` before first save.
- Draft data is stored in IndexedDB with schema version, user ID, seller/warehouse scope, timestamps, and sync state.
- The UI clearly displays offline, pending sync, syncing, conflict, and synchronized states.
- Offline mode may create/edit receipt drafts only.
- Reservation, stock confirmation, shipment confirmation, manager approvals, and live lookup requiring current data remain blocked offline.
- On reconnect, the client submits the draft with the same `client_draft_id` and an idempotency key.
- The server returns the existing receipt for a repeated successful submission.
- A conflict does not silently merge operational quantities. The user receives a field/line-level conflict view and must resolve it.
- Central inventory changes only during server-confirmed receipt completion.
- Logout removes or encrypts local drafts according to approved device policy; drafts must not leak across users.

### 9.3 Orders and fulfillment

1. Create/import an order idempotently.
2. Validate seller, product identifiers, requested quantities, and order uniqueness.
3. Snapshot the applicable seller policy.
4. Reserve inventory transactionally.
5. Generate pick work for reserved quantities.
6. Record picks and short-pick exceptions.
7. Pack using manual weight/dimensions initially.
8. Record manual tracking or create a carrier label through an adapter later.
9. Confirm shipment and create shipment inventory movements atomically.
10. Expose updated order/shipment state to the seller portal.

### 9.4 Transfers

1. Manager creates a transfer and requested lines.
2. Required approval is captured.
3. Origin staff pick/stage inventory.
4. Dispatch atomically moves quantities to `IN_TRANSIT`.
5. Destination staff records good, damaged, missing, and overage quantities.
6. Receipt moves quantities out of `IN_TRANSIT` into destination states.
7. Variances open discrepancy-review tasks.
8. A manager resolves discrepancies with explicit reasons and movements.

### 9.5 Returns

1. Seller or manager creates an expected return where possible.
2. Warehouse matches the inbound package to return/order/shipment.
3. Unmatched packages become unidentified returns.
4. Received units enter inspection/quarantine, never available stock.
5. Inspector records condition and disposition per line.
6. Approved completion creates inventory movements into the final state.
7. Seller sees status and final outcome.

### 9.6 Adjustments

1. Authorized user requests an adjustment with reason and evidence.
2. System determines approval requirement from policy thresholds.
3. Requester cannot approve their own adjustment when segregation of duties applies.
4. Approval creates explicit ledger movements and an audit event.
5. Rejection closes the request without inventory change.

---

## 10. API Design

### 10.1 API conventions

- Base prefix: `/api/v1`.
- JSON uses `snake_case` unless a frontend-wide alternative is explicitly adopted.
- Every endpoint declares `response_model`, `status_code`, and `summary`.
- Mutating endpoints accept `Idempotency-Key` where retries are possible.
- List endpoints use cursor pagination for high-volume operational records.
- Filters are typed and bounded.
- Timestamps use ISO 8601 UTC.
- Validation errors use `422`; business conflicts use `409`; invalid state transitions use `409`; missing records use `404`.
- Unknown failures return a generic `500` and a request/correlation ID, never raw exception text.

Standard error response:

```json
{
  "error": {
    "code": "INSUFFICIENT_AVAILABLE_INVENTORY",
    "message": "The requested quantity is no longer available.",
    "details": {
      "available_quantity": "4",
      "allowed_actions": ["PARTIAL_FULFILLMENT", "BACKORDER", "CANCEL"]
    },
    "request_id": "uuid"
  }
}
```

### 10.2 Endpoint inventory

#### Authentication and identity

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/users/me`
- CRUD endpoints for users, assignments, sellers, warehouses, and policies restricted to administrators/managers as appropriate.

#### Catalog

- `GET|POST /api/v1/products`
- `GET|PATCH /api/v1/products/{product_id}`
- `POST /api/v1/products/{product_id}/identifiers`
- `GET|POST /api/v1/warehouses/{warehouse_id}/locations`

#### Inventory

- `GET /api/v1/inventory/balances`
- `GET /api/v1/inventory/movements`
- `GET /api/v1/inventory/products/{product_id}/explanation`
- `POST /api/v1/inventory/adjustments`
- `POST /api/v1/inventory/adjustments/{adjustment_id}/approve`
- `POST /api/v1/inventory/adjustments/{adjustment_id}/reject`
- `POST /api/v1/inventory/reconciliations`

#### Receipts

- `POST /api/v1/receipts`
- `GET /api/v1/receipts`
- `GET|PATCH /api/v1/receipts/{receipt_id}`
- `POST /api/v1/receipts/{receipt_id}/lines`
- `PATCH /api/v1/receipts/{receipt_id}/lines/{line_id}`
- `POST /api/v1/receipts/{receipt_id}/complete`
- `POST /api/v1/receipts/{receipt_id}/cancel`
- `POST /api/v1/receipts/{receipt_id}/duplicate-override`
- `POST /api/v1/receipt-drafts/sync`

#### Orders and fulfillment

- `POST /api/v1/orders`
- `POST /api/v1/orders/import`
- `GET|PATCH /api/v1/orders/{order_id}`
- `POST /api/v1/orders/{order_id}/confirm`
- `POST /api/v1/orders/{order_id}/cancel`
- `GET /api/v1/pick-tasks`
- `POST /api/v1/pick-tasks/{task_id}/start`
- `POST /api/v1/pick-tasks/{task_id}/record-pick`
- `POST /api/v1/pick-tasks/{task_id}/short-pick`
- `POST /api/v1/orders/{order_id}/packages`
- `POST /api/v1/orders/{order_id}/shipments`
- `POST /api/v1/shipments/{shipment_id}/confirm`

#### Transfers

- `POST|GET /api/v1/transfers`
- `GET|PATCH /api/v1/transfers/{transfer_id}`
- `POST /api/v1/transfers/{transfer_id}/approve`
- `POST /api/v1/transfers/{transfer_id}/dispatch`
- `POST /api/v1/transfers/{transfer_id}/receive`
- `POST /api/v1/transfers/{transfer_id}/resolve-discrepancy`

#### Returns

- `POST|GET /api/v1/returns`
- `GET|PATCH /api/v1/returns/{return_id}`
- `POST /api/v1/returns/{return_id}/receive`
- `POST /api/v1/returns/{return_id}/inspect`
- `POST /api/v1/returns/{return_id}/complete`
- `POST /api/v1/returns/unidentified`

#### Seller portal and reports

- `GET /api/v1/seller/inventory`
- `GET /api/v1/seller/orders`
- `GET /api/v1/seller/receipts`
- `GET /api/v1/seller/shipments`
- `GET /api/v1/seller/returns`
- `GET /api/v1/seller/transfers`
- `GET /api/v1/manager/dashboard`
- `GET /api/v1/manager/exceptions`
- `GET /api/v1/reports/inventory-reconciliation`

---

## 11. Backend Implementation Standards

### 11.1 Database lifecycle

`core/database/database.py` owns:

- One module-level `AsyncEngine`.
- One module-level `async_sessionmaker[AsyncSession]`.
- `async connect_to_database()` for connectivity validation and startup checks.
- `async close_database_connection()` for engine disposal and singleton reset.
- `get_session_factory()` which raises `RuntimeError` before initialization.
- `async session_scope()` context manager for transaction/unit-of-work ownership.

FastAPI lifespan initializes configuration, logging, database connectivity, seed validation, workers/dispatchers, and shutdown cleanup.

### 11.2 CRUD rules

- CRUD functions receive `session: AsyncSession` as their first argument.
- CRUD modules contain SQLAlchemy persistence operations only.
- CRUD functions never raise `HTTPException`.
- CRUD functions do not authenticate, authorize, or choose business policy.
- Locking methods state their locking behavior in names/docstrings, for example `get_balance_for_update`.
- Reads/writes log at debug level with stable identifiers.
- Database exceptions are logged and re-raised unless a safe persistence result is explicitly part of the contract.

### 11.3 Controller rules

- Controllers are classes with backward-compatible module singleton instances where the project convention requires them.
- Controllers own domain validation, permissions, transactions, orchestration, state transitions, and response assembly.
- Controllers obtain the session/unit of work at method start.
- Expected business rejection uses warning logs and meaningful `HTTPException` status codes.
- Unknown failures use error logs and retain the original exception chain internally.
- Controllers never call SQLAlchemy queries directly.

### 11.4 Route rules

- Routes are thin wrappers.
- Authentication and scope come from `Depends(...)`.
- Routes call one controller entry point.
- Routes re-raise `HTTPException` unchanged.
- Unknown errors are logged with `exc_info=True` and converted to a generic 500.
- No session, SQLAlchemy model, or provider client is imported into route modules.

### 11.5 Service rules

- Services own external clients, reusable complex workflows, retries, timeouts, and cleanup.
- Services raise plain/domain exceptions, not FastAPI exceptions.
- Provider implementations live behind interfaces/adapters.
- HTTP clients have explicit connect/read/write/pool timeouts.
- Retries are limited to safe/idempotent operations and use bounded exponential backoff with jitter.

### 11.6 Logging standard

```python
from common.logger import get_logger

logger = get_logger(__name__)
```

- Route entry: `Calling METHOD /path endpoint`.
- Controller/CRUD/service entry: `Executing ClassName.method_name`.
- `INFO`: successful business operations and lifecycle transitions.
- `WARNING`: expected denial, duplicate, missing record, invalid transition, shortage, or conflict.
- `ERROR`: unexpected exceptions, with `exc_info=True` at the boundary that records the stack trace.
- `DEBUG`: identifiers, counts, query intent, and provider metadata without secrets.
- Logs are structured and include timestamp, severity, module, request ID, correlation ID, actor ID, seller ID, warehouse ID, aggregate type/id, and event name when applicable.
- `common/logger.py` configures INFO+ console output and DEBUG+ rotating file output (5 MB, three backups) in UTC for local deployments; centralized production logging is preferred.

---

## 12. Frontend Application

### 12.1 Route map

```text
/login
/app
  /dashboard
  /receiving
  /receiving/new
  /receiving/:receiptId
  /inventory
  /inventory/:productId
  /orders
  /orders/:orderId
  /picking
  /shipments
  /returns
  /returns/:returnId
  /transfers
  /transfers/:transferId
  /exceptions
  /reports
  /admin/users
  /admin/sellers
  /admin/products
  /admin/warehouses
  /admin/policies
/seller
  /dashboard
  /inventory
  /orders
  /receipts
  /shipments
  /returns
```

### 12.2 Frontend rules

- Route files handle layouts, metadata, permission redirects, route params, and feature composition only.
- Workflow UI lives under `src/features`.
- Raw `fetch`/Axios calls never appear in components; typed calls live under `src/lib/api` or feature API modules using the shared client.
- API errors are normalized into safe domain messages.
- Every data workflow has loading, empty, error, success, disabled, permission-denied, and retry states where applicable.
- Forms use accessible labels, keyboard-safe controls, visible focus states, and field-level errors.
- Operational screens prioritize scanability and speed over decorative layouts.
- Responsive layouts support warehouse workstations/tablets and seller mobile/desktop views.
- Do not rely on color alone for state or exceptions.
- Current seller and warehouse context is visible on every operational screen.
- Destructive/irreversible actions use explicit confirmation and explain their operational effect.

### 12.3 Receiving UX

- Fast item lookup by scanner keyboard input, UPC, SKU, or name.
- Separate quantity inputs for sellable, damaged, and quarantine states.
- Persistent source reference and seller/warehouse context.
- Autosave indicator and offline sync badge.
- Completion summary showing exactly which inventory states will change.
- Duplicate-receipt conflict page showing the existing receipt and manager override path.

### 12.4 Order and picking UX

- Availability is labeled as a time-sensitive server-confirmed value.
- Confirmation shows the policy outcome before mutation.
- Pick screens minimize typing and show location, SKU, identifier, requested/picked quantities, and exception action.
- Short-pick is a first-class workflow, not a free-text workaround.

### 12.5 Seller portal UX

- Read-only operational status by default.
- Clear warehouse-separated inventory.
- Order, shipment, receipt, and return timelines.
- Expected-return creation when enabled.
- No internal notes, other sellers, staff-only evidence, or sensitive audit metadata.

---

## 13. Background Work, Events, and Integrations

### 13.1 Transactional outbox

Any business event that must trigger external or asynchronous work is written to `outbox_events` in the same transaction as the business change. A worker claims and publishes events using leases/`SKIP LOCKED`.

Initial events include:

- `receipt.completed`
- `order.reserved`
- `order.backordered`
- `pick.short`
- `shipment.confirmed`
- `transfer.dispatched`
- `transfer.received`
- `transfer.discrepancy_detected`
- `return.received`
- `return.completed`
- `inventory.adjusted`
- `exception.created`

### 13.2 Scheduled jobs

- Reservation expiry/release.
- Aging open receipt detection.
- Delayed transfer detection.
- Uninspected return detection.
- Negative/mismatched balance detection.
- Outbox dispatch/retry.
- Audit retention/archive according to policy.
- Backup/restore verification signaling.

### 13.3 Provider adapters

Carrier, storage, notification, marketplace, scanner, printer, scale, and AI providers are accessed through explicit interfaces. Domain controllers do not know provider SDK details.

Manual workflows remain supported when integrations are absent or temporarily unavailable.

---

## 14. AI, RAG, MCP, and CLI Roadmap

### 14.1 AI safety authority

AI may answer, summarize, identify rule-based exceptions, and create drafts. A permitted human must approve every action that changes inventory, orders, transfers, returns, seller communications, or shipments.

All AI interactions record actor, question category, retrieved references, tool calls, response, draft actions, approval/rejection, timestamps, and correlation IDs. Private prompts, secrets, and unnecessary sensitive payloads are not logged.

### 14.2 AI Release A: read-only operations assistant

- Answer available quantity by warehouse.
- Explain why stock changed using ledger references.
- Answer order, receipt, transfer, shipment, and return status.
- Use permission-aware application tools; never query PostgreSQL directly.
- Include related business references in answers.
- Apply seller and warehouse scope to every tool call.
- Use medical-style safety guard concepts only as a structural pattern; warehouse-specific guards cover destructive requests, secret disclosure, cross-tenant access, and unsupported operational advice.

### 14.3 AI Release B: exception summaries and drafts

- Summarize negative/mismatched balances, old receipts, aging reservations, delayed transfers, uninspected returns, and unusual adjustments.
- Create manager-review tasks or seller-message drafts.
- Never perform the final mutation or send the final communication without human approval.

### 14.4 AI Release C: voice-assisted receiving

- Voice captures structured draft quantities, condition, and notes.
- Barcode/UPC remains the identity authority.
- The user visually confirms the structured draft before receipt completion.
- Manual entry is always available.

### 14.5 MCP server

- Use `FastMCP` with streamable HTTP at `/mcp`.
- Database lifecycle is wired through an async lifespan.
- Tool arguments use `Annotated[type, Field(description=...)]`.
- `RequesterContext` contains user ID, email, role, seller scope, warehouse scope, and raw token only for forwarding where required.
- Authorization occurs inside tool functions.
- Tools call existing APIs or controller-approved read services and never duplicate business rules.
- HTTP/provider errors are wrapped in safe domain-specific `RuntimeError` subclasses.
- Initial tools are read-only: inventory lookup, ledger explanation, order status, receipt status, transfer status, return status, and exception listing.

### 14.6 CLI

- CLI entry point is `cli/main.py`.
- Commands live in `cli/commands`.
- Commands connect through approved controller/service boundaries.
- Initial commands: database health, migration status, import validation, reconciliation, exception report, and read-only routine checks.
- CLI commands use service-account or operator identity and produce audit events.

---

## 15. Security and Privacy

### 15.1 Required controls

- TLS in transit; encrypted managed disks/backups at rest.
- Password hashing with bcrypt and strong parameters.
- Secrets injected from environment/secret manager; no committed credentials.
- Least-privilege database roles for application, migrations, read-only reporting, and operations.
- CSRF-safe token/cookie design when cookies are used.
- Strict CORS allowlist by environment.
- Rate limits for login, refresh, imports, AI, and externally exposed integration endpoints.
- File upload content-type/size limits, malware scanning where applicable, and object access controls.
- SQLAlchemy parameterization only; no interpolated SQL from user input.
- Output encoding and safe rich-text policy in the frontend.
- Dependency and container vulnerability scanning in CI.
- Audit of permission and policy changes.
- Configurable retention for business records, logs, AI transcripts, and attachments.

### 15.2 Sensitive logging exclusions

Never log:

- Passwords or password hashes.
- JWTs, refresh tokens, API keys, or connection strings.
- Private prompt bodies when not required for audited AI behavior.
- Full seller payloads, attachment contents, or personal contact data.
- Provider credentials or signed object URLs.

### 15.3 Database protections

- Normal application role cannot mutate or delete inventory ledger rows.
- Alembic migration role is separate and not used by the runtime.
- Production schema changes are forward-compatible and deployed with expand/migrate/contract discipline.
- Backups use point-in-time recovery when supported.
- Restore tests occur on a defined schedule and are recorded.

---

## 16. Observability and Operations

### 16.1 Health endpoints

- `/health/live`: process is running; no external dependency check.
- `/health/ready`: database connectivity, required migration version, and essential worker/provider readiness.
- `/health/startup`: startup initialization status when the hosting platform uses it.

### 16.2 Metrics

Track at minimum:

- Request rate, error rate, and latency by endpoint.
- PostgreSQL pool usage, transaction time, lock wait, deadlock, slow query, and replication/backup health.
- Receipt completion and duplicate-block counts.
- Reservation success/conflict/partial/backorder counts.
- Pick/pack/shipment cycle time and short-pick rate.
- Transfer age and discrepancy rate.
- Return inspection age.
- Inventory reconciliation mismatches.
- Outbox/job lag, failure, and retry counts.
- Offline draft sync success/conflict/age.
- AI tool error and permission-denial rate.

### 16.3 Alerts

Critical alerts include:

- Ledger/balance mismatch.
- Negative controlled-state balance.
- Repeated reservation deadlocks or transaction failures.
- Database unavailable or storage near capacity.
- Backup/restore validation failure.
- Outbox lag above threshold.
- Elevated authentication failures or cross-tenant authorization denials.
- Error-rate or latency SLO breach.

### 16.4 Operational runbooks

Maintain runbooks for:

- Database outage and recovery.
- Failed migration and application rollback.
- Inventory mismatch investigation.
- Duplicate receipt investigation.
- Stuck reservation/outbox/job.
- Offline draft conflict.
- Carrier/storage provider outage.
- Compromised credential/session revocation.
- Warehouse cutover and rollback.

---

## 17. Testing Strategy

### 17.1 Backend test rules

- Tests use PostgreSQL, not SQLite, for transaction, lock, constraint, JSONB, enum, and migration behavior.
- Testcontainers or an isolated PostgreSQL test database is required.
- Database fixtures set the test database before importing the app.
- Each test runs in an isolated database/schema/transaction strategy that cannot leak state.
- Seed only required default identities, roles, warehouses, and policies.
- `AsyncClient` uses `ASGITransport(app=app)` for API tests.
- Every changed behavior includes happy-path and relevant `401`, `403`, `404`, `409`, and `422` cases.

### 17.2 Unit tests

- Policy decisions: backorder, partial fulfillment, expiry, approvals.
- State-transition guards.
- Quantity conservation.
- Ledger movement construction.
- Permission-scope decisions.
- Identifier normalization.
- Error normalization and safe messages.

### 17.3 Integration tests

- Alembic upgrade from an empty database and from the prior supported version.
- Receipt duplicate constraint and override.
- Receipt completion ledger/balance atomicity.
- Concurrent final-unit reservation using two real transactions.
- Deadlock-resistant deterministic lock ordering.
- Reservation expiry/release idempotency.
- Shipment and cancellation movement correctness.
- Transfer dispatch/receipt/discrepancy accounting.
- Return inspection and disposition accounting.
- Cross-seller and cross-warehouse access denial.
- Outbox insertion in the business transaction and idempotent retry.
- Import rollback and reconciliation.

### 17.4 End-to-end tests

- Receive normal stock.
- Detect repeated offline receipt sync.
- Block duplicate completed receipt and complete manager override.
- Race two orders for the final nine units and confirm only one permitted reservation outcome.
- Pick, pack, manually track, and ship an order.
- Short-pick and follow seller policy.
- Dispatch Reno-to-Columbus transfer and receive with/without variance.
- Expected return, unidentified return, inspection, quarantine, restock, and damage.
- Seller sees only own data.
- Manager sees only assigned warehouse(s).
- Excel migration rehearsal and report sign-off.
- Offline draft creation, reconnect, synchronization, and conflict handling.

### 17.5 Frontend tests

- Component state rendering and accessibility.
- Form validation, disabled/loading states, and server error mapping.
- Permission and route guards.
- Offline draft persistence and sync queue.
- Duplicate/conflict workflows.
- Responsive behavior for supported screen sizes.
- Critical workflows in Playwright.

### 17.6 Non-functional tests

- Reservation concurrency/load test.
- Receipt-import and seller-query performance test at projected volumes plus safety margin.
- Backup restoration drill.
- Authorization matrix test.
- Dependency/security scan.
- Accessibility test against WCAG 2.1 AA targets.
- Failure injection for database/provider/network interruptions.

---

## 18. Migration and Cutover

### 18.1 Data preparation

1. Inventory every source workbook, tab, column, formula, owner, and update process.
2. Freeze identifier conventions for sellers, products, UPCs, warehouses, and locations.
3. Normalize duplicate/ambiguous SKUs and UPCs with business-owner approval.
4. Reconcile sellable, damaged, held, and unknown quantities separately.
5. Define the opening-balance timestamp and sign-off owners.

### 18.2 Import design

- Imports run through a staging schema/table set.
- Every row retains source workbook, sheet, row, source hash, import batch, and validation status.
- Validation reports missing sellers/products, duplicate identifiers, invalid quantities, ambiguous warehouse/state, and cross-sheet mismatches.
- No staged row reaches operational tables until the batch passes validation and receives approval.
- Opening inventory produces `MIGRATION_OPENING_BALANCE` ledger movements, never direct balance-only writes.
- Import is idempotent by batch and source-row identity.

### 18.3 Controlled launch

1. Rehearse migration with a copy of spreadsheet data.
2. Reconcile the database-generated opening position with the approved stock baseline.
3. Select pilot warehouse, seller group, and workflow scope.
4. Make Excel read-only for the pilot operational scope while retaining comparison access.
5. Run a 10-business-day reconciliation window.
6. Log and resolve every variance and workflow exception.
7. Obtain operational sign-off.
8. Cut over the second warehouse using the proven runbook.

### 18.4 Rollback boundary

After the platform accepts live inventory movements, rollback cannot mean silently returning to editable spreadsheets. A rollback pauses new platform transactions, exports a ledger-derived operational snapshot, reconciles in-flight work, and follows an approved continuity runbook. The ledger remains the audit authority for all accepted events.

---

## 19. Delivery Plan

Phases overlap. Foundation, frontend scaffolding, automated testing, CI/CD, security, observability, and release infrastructure progress alongside workflow development.

### Phase 0: discovery and decisions

- Confirm seller policies, opening inventory baseline, pilot scope, approval thresholds, record-retention rules, expected volumes, supported devices/browsers, and integration priorities.
- Map current workbooks and warehouse procedures.
- Produce event/state-transition and authorization matrices.
- Establish SLOs and recovery targets.

**Exit:** all decisions in Section 21 have accountable owners and approved values.

### Phase 1: foundation, access, and master data

- Application/repository scaffolding.
- PostgreSQL, SQLAlchemy async, Alembic, database roles.
- Authentication, users, roles, seller/warehouse assignments.
- Sellers, warehouses, locations, products, identifiers, policies.
- Audit, idempotency, outbox, logging, health, metrics, CI/CD.
- React shell, typed API client, authentication, permission routing.

**Exit:** permission matrix and master-data flows pass automated tests.

### Phase 2: inventory ledger and receiving

- Ledger and balance projection.
- Receipt draft/completion/cancellation/duplicate override.
- Damage, quarantine, shortage, and overage handling.
- Offline receipt drafting/sync.
- Inventory views and ledger explanation.
- Reconciliation tooling.

**Exit:** duplicate prevention, atomic completion, ledger invariants, and offline sync pass integration/E2E tests.

### Phase 3: orders and fulfillment

- Order creation/import.
- Transactional reservation and seller policy outcomes.
- Pick, short-pick, pack, package, manual shipment/tracking.
- Seller order/shipment visibility.

**Exit:** concurrency test proves no oversell; fulfillment lifecycle passes E2E validation.

### Phase 4: transfers, returns, and operational visibility

- Transfer approval/dispatch/receipt/discrepancy.
- Expected/unidentified returns, inspection, disposition.
- Manager dashboards and exception queues.
- Complete seller portal.

**Exit:** state-specific inventory isolation and cross-tenant/warehouse permissions pass testing.

### Phase 5: migration, validation, and controlled launch

- Import tooling and rehearsal.
- Load/security/accessibility validation.
- Operational training and runbooks.
- Pilot, 10-business-day reconciliation, second-warehouse cutover.

**Exit:** signed acceptance criteria and operational handover.

### Later releases

- Scanner, printer, carrier, scale, marketplace/order-source adapters.
- AI Release A, then B, then voice-assisted C after data quality gates.
- Additional automation only after explicit risk and permission review.

---

## 20. CI/CD and Deployment

### 20.1 Pull-request gates

- Formatting and linting.
- Static typing.
- Unit and integration tests.
- Frontend lint/typecheck/unit tests.
- Migration upgrade test.
- Dependency, secret, and vulnerability scans.
- Build backend/frontend artifacts.
- Playwright smoke test in an ephemeral environment for material workflow changes.

### 20.2 Deployment strategy

- Immutable container images pinned by digest.
- Separate development, staging, and production environments.
- Environment-specific secrets and allowlists.
- Expand/migrate/contract database changes.
- Backward-compatible API/database deployment order.
- Pre-deployment backup/restore readiness check for risky migrations.
- Smoke tests after deployment.
- Application rollback does not reverse already-accepted business transactions.

### 20.3 Environment variables

```env
APP_ENV=development
APP_HOST=127.0.0.1
APP_PORT=8000
DATABASE_URL=postgresql+asyncpg://warehouse_app:change-me@localhost:5432/warehouse_ops
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
JWT_SECRET=replace-with-long-random-secret
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
LOG_LEVEL=INFO
FRONTEND_ORIGINS=http://localhost:5173
GOOGLE_API_KEY=
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=
MCP_HOST=127.0.0.1
MCP_PORT=8001
MCP_TRANSPORT=streamable-http
WAREHOUSE_API_BASE_URL=http://127.0.0.1:8000
```

`.env.example` contains names and safe placeholders only. Production values come from the deployment secret mechanism.

---

## 21. Decisions Required Before Development Completion

| Decision | Required owner | Effect |
|---|---|---|
| Seller backorder, partial-fulfillment, reservation-expiry policies | Business owner per seller | Reservation and order state behavior |
| Opening inventory baseline and cutoff | Dan/warehouse managers + implementation lead | Migration ledger authority |
| Pilot warehouse, sellers, and workflows | Dan + implementation lead | Launch sequence and risk scope |
| Adjustment approval thresholds | Operations leadership | Segregation of duties and exception workflow |
| Transfer variance thresholds | Warehouse managers | Automatic vs manager-reviewed discrepancies |
| Return disposition categories and seller visibility | Operations + sellers | Return data and inventory-state model |
| SKU/UPC ownership and duplicate handling | Operations/data owner | Catalog uniqueness and receiving lookup |
| Reservation allocation strategy | Operations | Warehouse/location allocation behavior |
| Retention requirements | Business/security | Audit, operational records, logs, AI data |
| RPO/RTO and hosting region | Business + infrastructure | Backup, deployment, and recovery design |
| Supported browsers/devices | Warehouse operations | Offline storage and UI validation matrix |
| First hardware/provider integration | Business + implementation lead | Post-core adapter priority |

Unresolved decisions must be represented as configuration or a blocked acceptance item. Engineers must not silently invent business policy.

---

## 22. Acceptance Criteria

### 22.1 Inventory integrity

- [ ] No stock total changes without an auditable movement or approved adjustment.
- [ ] Ledger rows cannot be edited or deleted by the normal application role.
- [ ] Balance projection equals a rebuild from the ledger.
- [ ] Damaged, quarantined, return-inspection, and in-transit units are excluded from available stock.
- [ ] Reno and Columbus balances are independently visible.

### 22.2 Receiving

- [ ] Carrier tracking and seller ticket receipt sources are supported.
- [ ] Duplicate completed receipts are blocked by normal workflow and database protection.
- [ ] Manager override requires permission, reference to the original, and a reason.
- [ ] Damage, quarantine, shortage, and overage are captured separately.
- [ ] Offline drafts synchronize idempotently and do not alter stock before server completion.

### 22.3 Orders and fulfillment

- [ ] Concurrent orders cannot reserve the same final units.
- [ ] Backorder and partial outcomes follow the snapshotted seller policy.
- [ ] Short picks create an exception and correct downstream quantities.
- [ ] Manual pack measurements and tracking support the core launch.
- [ ] Shipment history and inventory effects remain auditable.

### 22.4 Transfers and returns

- [ ] Transfer stock remains in transit until destination receipt.
- [ ] Transfer variances remain visible until approved resolution.
- [ ] Returns never automatically become available stock.
- [ ] Expected, unidentified, damaged, quarantined, rejected, and restocked outcomes are traceable.

### 22.5 Access and seller visibility

- [ ] Users are restricted by role and assigned warehouse/seller scope.
- [ ] Sellers can view their own inventory, receipts, orders, shipments, and returns.
- [ ] Cross-seller access tests pass for every seller endpoint.
- [ ] New staff cannot access manager/admin capabilities without explicit assignment.

### 22.6 Reliability and launch

- [ ] Core workflows pass unit, PostgreSQL integration, concurrency, E2E, security, and migration tests.
- [ ] Monitoring, backups, restoration checks, alerts, rollback, and runbooks are operational.
- [ ] Migration rehearsal reconciles to the approved opening baseline.
- [ ] Excel is read-only for a warehouse once it becomes the operational source of truth.
- [ ] Pilot completes a 10-business-day reconciliation window before second-warehouse cutover.

### 22.7 AI and automation

- [ ] AI uses permission-aware application tools, not direct database access.
- [ ] Every answer references the relevant application record where applicable.
- [ ] AI cannot finalize a mutation or seller communication.
- [ ] AI/tool/draft/approval activity is audited.
- [ ] MCP and CLI identities are least-privilege and audited.

---

## 23. Definition of Done

A feature is done only when:

- Approved business behavior and state transitions are implemented.
- Authorization is enforced in the backend and represented correctly in the frontend.
- Database constraints, transactions, idempotency, and audit behavior are implemented where required.
- Every new/modified Python function and method has type annotations and the required docstring.
- Routes, controllers, CRUD modules, models, schemas, and services respect their layer boundaries.
- Loading, empty, error, disabled, success, permission, and responsive UI states are complete.
- Unit/integration/E2E tests cover the change and relevant error cases.
- Logging, metrics, alerts, and runbooks are updated.
- Migration and rollback implications are documented.
- Security and sensitive-data handling have been reviewed.
- User-facing and operator documentation is updated where the project requires it.
- Acceptance evidence is linked to the applicable criterion.

---

## 24. Recommended Immediate Next Step

Approve this implementation authority and run a focused workflow/data discovery session with Dan, one trusted manager from each warehouse, a receiver, a picker/packer, and representative sellers. The session must close the policy decisions in Section 21, inventory every spreadsheet source, validate state transitions and permissions, and produce the signed opening-data and pilot scope required to begin Phase 1 without inventing business rules.
