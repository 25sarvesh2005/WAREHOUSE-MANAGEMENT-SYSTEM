# Whitfield Fulfillment WMS — Architecture Reference

**Version:** 0.1.0  
**Stack:** Python 3.11+ · FastAPI · PostgreSQL 16 · React 19 · TanStack Router · Vite

---

## 1. System Overview

Whitfield WMS is a multi-tenant, bicoastal fulfillment and warehouse operations platform. It replaces spreadsheet-based operations with a fully transactional, auditable inventory system spanning two fulfillment hubs: **Reno, NV (RNO)** and **Columbus, OH (CMH)**.

### Core Design Principles

| Principle | Implementation |
|---|---|
| Immutable ledger | Inventory movements are append-only; balances are derived projections |
| Concurrency safety | `SELECT FOR UPDATE` row-level locks prevent over-allocation |
| Tenant isolation | All queries are scoped by `seller_id` and `warehouse_id` via JWT claims |
| Transactional consistency | Domain events are written atomically via the Outbox pattern |
| Read-only AI | The Gemini copilot and MCP tools can never mutate inventory state |
| Layered architecture | Routes → Controllers → CRUDs → PostgreSQL; no layer skipping permitted |

---

## 2. Repository Structure

```
WAREHOUSE-MANAGEMENT-SYSTEM/
├── backend/                        # Python FastAPI application
│   ├── main.py                     # ASGI entrypoint, lifespan, middleware registration
│   ├── requirements.txt            # Pinned Python dependencies
│   ├── pyproject.toml              # Build metadata, pytest config, ruff lint rules
│   ├── alembic.ini                 # Alembic migration tool configuration
│   ├── .env.example                # All supported environment variables with examples
│   ├── postman_collection.json     # Importable Postman collection (manual API testing)
│   ├── postman_environment.json    # Postman environment variable template
│   ├── common/                     # Shared infrastructure (no domain logic)
│   │   ├── auth.py                 # JWT decode, get_current_user, get_warehouse_scope
│   │   ├── idempotency.py          # Request idempotency key helpers
│   │   ├── logger.py               # Structured JSON logger (get_logger factory)
│   │   ├── pagination.py           # Shared cursor/offset pagination models
│   │   ├── rate_limit.py           # Token-bucket rate limiting middleware
│   │   ├── request_id.py           # X-Request-ID propagation middleware
│   │   └── warehouse_scope.py      # Warehouse-level access scope dependency
│   ├── core/
│   │   ├── constants.py            # All domain enums and shared constants (single source)
│   │   ├── config/settings.py      # Pydantic BaseSettings, env loading, prod validation
│   │   ├── apis/
│   │   │   ├── api.py              # APIRouter aggregator for all domain routers
│   │   │   ├── routes/             # Thin HTTP handlers (validate, authenticate, delegate)
│   │   │   └── schemas/            # Pydantic request/response models per domain
│   │   ├── controllers/            # Domain orchestration: business rules + transactions
│   │   ├── cruds/                  # SQLAlchemy persistence; row locking; outbox writes
│   │   ├── models/                 # SQLAlchemy 2.x ORM models
│   │   ├── services/
│   │   │   ├── ai/                 # Gemini 2.5 Flash RAG provider, safety guards, tools
│   │   │   ├── import_export/      # Excel/CSV opening inventory ingestion
│   │   │   └── voice/              # Web Speech API and Sarvam STT/TTS pipeline
│   │   ├── database/               # Engine lifecycle, async session factory, Alembic seed
│   │   └── jobs/                   # Periodic ASGI background workers
│   ├── mcp_server/                 # FastMCP protocol server (GET /mcp, POST /mcp/call)
│   ├── cli/                        # Typer CLI commands for operational tooling
│   ├── tests/
│   │   ├── unit/                   # 21 pytest modules — domain logic, controllers, jobs
│   │   └── e2e/                    # 8 end-to-end test scripts against a live API
│   └── tools/                      # Operational scripts: seeding, load tests, audits
├── frontend/                       # Vite + React 19 + TanStack Router SPA
│   ├── src/
│   │   ├── routes/                 # File-based TanStack Router pages
│   │   ├── components/             # Feature components (AI, Voice, Migration, etc.)
│   │   ├── hooks/                  # TanStack Query data hooks
│   │   ├── lib/                    # API client, TypeScript interfaces, auth utils
│   │   └── styles.css              # Global CSS and design tokens
│   ├── e2e/                        # Playwright E2E and axe-core accessibility tests
│   ├── Dockerfile                  # Multi-stage production frontend container
│   └── package.json                # Node dependencies
├── docs/
│   ├── ARCHITECTURE.md             # This document
│   └── runbooks/                   # Operational runbooks and launch checklists
├── .github/workflows/ci.yml        # 4-job GitHub Actions CI pipeline
├── Dockerfile                      # Root multi-stage container (backend)
├── docker-compose.yml              # Local/cloud multi-container orchestration
└── README.md                       # Project overview, quick start, and API explorer
```

---

## 3. Request Lifecycle

```
HTTP Request
    ↓
FastAPI Route Handler          (auth, schema validation, no SQL)
    ↓
Domain Controller              (business rules, transaction boundary)
    ↓
CRUD Function(session)         (SQLAlchemy; SELECT FOR UPDATE where needed)
    ↓
PostgreSQL                     (movement ledger + balance tables + outbox_events)
```

**Invariants enforced at each layer:**

- **Routes** never call `session.execute()` or contain business logic.
- **Controllers** own the transaction context (`async with transaction_session()`).
- **CRUDs** accept an `AsyncSession` as first argument; never open their own transactions.
- **Controllers** always append to `outbox_events` within the same transaction as the domain write.

---

## 4. Domain Modules

| Domain | Route Prefix | Key Entities |
|---|---|---|
| Identity | `/api/v1/auth`, `/api/v1/users` | User, Seller, Warehouse, Location |
| Catalog | `/api/v1/products`, `/api/v1/skus` | Product, SKU, SellerPolicy |
| Inventory | `/api/v1/inventory` | InventoryBalance, InventoryMovement |
| Receiving | `/api/v1/receipts` | ReceivingReceipt, ReceivingLine |
| Orders | `/api/v1/orders` | Order, OrderLine, InventoryReservation |
| Fulfillment | `/api/v1/fulfillment` | PickTask, Shipment |
| Transfers | `/api/v1/transfers` | TransferOrder, TransferLine |
| Returns | `/api/v1/returns` | CustomerReturn, ReturnLine |
| Migration | `/api/v1/migration` | MigrationBatch, StagedInventoryRow |
| AI Copilot | `/api/v1/ai` | AIInteraction, AIDraftAction, AIFeedback |
| Voice | `/api/v1/voice` | VoiceInteraction, VoiceReceivingDraft |
| MCP Server | `/mcp` | Tool catalog + tool call dispatcher |
| Reporting | `/api/v1/reports` | Cross-domain aggregated queries |

---

## 5. Inventory Ledger Model

Every stock change is explained by an `InventoryMovement` record with:
- `actor_user_id` — who triggered it
- `source_type` / `source_id` — originating workflow record (receipt, order, transfer, etc.)
- `movement_type` — enum from `InventoryMovementType` in `core/constants.py`
- `quantity_delta` — signed integer (positive = in, negative = out)
- `from_state` / `to_state` — inventory bucket transition

Supported inventory states: `AVAILABLE`, `RESERVED`, `DAMAGED`, `QUARANTINED`, `IN_TRANSIT`, `SHIPPED`, `RETURN_INSPECTION`.

`InventoryBalance` rows are the query-optimized projection updated within the same transaction as each movement. They are never edited directly.

**Concurrency:** All reservation writes lock the balance row with `SELECT ... FOR UPDATE` before modifying it.

---

## 6. Transactional Outbox

Every controller that modifies inventory state also writes a row to `outbox_events` **inside the same database transaction**. This enforces at-least-once event delivery without distributed transactions.

The `_periodic_outbox_dispatch_worker` polls every 10 seconds and dispatches pending events with exponential backoff (`min(3600, 2^(attempt+1) × 10)`). Events failing after 5 attempts transition to `DEAD_LETTER`.

**22 supported event types** across receipts, orders, fulfillment, transfers, returns, and inventory.

---

## 7. Background Workers

All workers are `asyncio.Task` objects started in the ASGI lifespan and cancelled on shutdown.

| Worker | Interval | Function |
|---|---|---|
| Outbox Dispatcher | 10 s | Dispatch pending outbox events with exponential backoff |
| Reservation Expiry | 60 s | Release `RESERVED` balances for expired orders back to `AVAILABLE` |
| Receipt Aging Monitor | 300 s | Emit `RECEIPT_AGING_ALERT` for receipts stalled > 48 h |
| Transfer Delay Scanner | 300 s | Emit `TRANSFER_DELAY_ALERT` for in-transit transfers > 7 days |
| Return Aging Monitor | 300 s | Emit `RETURN_AGING_ALERT` for returns awaiting inspection > 24 h |

---

## 8. Security Model

| Control | Implementation |
|---|---|
| Authentication | HS256 JWT tokens; `get_current_user` FastAPI dependency |
| Authorization | 5 RBAC roles via `UserRole` enum; `get_warehouse_scope` restricts facility access |
| Tenant isolation | All queries filtered by `seller_id` extracted from JWT claims |
| Rate limiting | Token-bucket limiter in `common/rate_limit.py`; configurable via env |
| Trusted hosts | `TrustedHostMiddleware` when `TRUSTED_HOSTS != "*"` |
| AI guardrails | `core/services/ai/safety.py` enforces read-only constraint; mutations refused and audited |
| Secret scanning | `tools/audit_frontend_secrets.py` CI step verifies no credentials in client bundles |

---

## 9. AI & MCP Subsystem

### Gemini Copilot (Read-Only RAG)
- Model: `gemini-2.0-flash-lite` (configurable via `AI_MODEL`)
- Grounded against live PostgreSQL data via 8 internal read tools
- All interactions stored in `ai_interactions` with full audit trail
- Safety guard refuses mutations, cross-tenant queries, and secret disclosure

### FastMCP Protocol Server (`/mcp`)
Implements the MCP 2024-11-05 specification:
- `GET /mcp` — tool catalog
- `POST /mcp/call` — tool execution with JWT auth

**8 Tools:** `inventory_lookup`, `ledger_explanation`, `order_status`, `receipt_status`, `transfer_status`, `shipment_status`, `return_status`, `exception_listing`.

---

## 10. Frontend Architecture

| Concern | Implementation |
|---|---|
| Framework | React 19 + Vite 8 + TypeScript 5.8 |
| Routing | TanStack Router (file-based, type-safe, SSR-capable) |
| Data fetching | TanStack React Query (optimistic updates, background refetch) |
| Styling | TailwindCSS v4 + custom design tokens in `styles.css` |
| Error handling | `ErrorBoundary` class component wrapping the router root and feature sections |
| Auth | JWT stored in `sessionStorage`; decoded via `lib/auth.ts` |
| API client | Typed fetch wrapper in `lib/api-client.ts` |
| Voice | `ReceivingVoiceDraftPanel` using Web Speech API with Sarvam STT/TTS fallback |
| E2E tests | Playwright + axe-core WCAG 2.1 AA accessibility assertions |

---

## 11. CI Pipeline

Four-job GitHub Actions workflow (`.github/workflows/ci.yml`):

1. **backend-checks** — import check, `compileall`, full pytest suite (122 tests), frontend secret audit
2. **e2e-checks** — live FastAPI server + 6 end-to-end scenario scripts + concurrency load test
3. **frontend-checks** — TypeScript typecheck, ESLint, Vite production build
4. **frontend-e2e** — Playwright browser E2E + axe-core accessibility tests

Triggers: push to `main`, `master`, `develop`; PR to `main`, `master`.

---

## 12. Configuration Reference

All settings are loaded from environment variables via `core/config/settings.py` (Pydantic `BaseSettings`). See `backend/.env.example` for the full annotated list.

**Critical production settings:**

| Variable | Description |
|---|---|
| `DATABASE_URL` | asyncpg connection URL (Supabase / Neon / RDS) |
| `JWT_SECRET` | Long random secret (≥ 32 chars recommended) |
| `APP_ENV` | `production` hides `/docs`, `/redoc`, `/openapi.json` |
| `INITIALIZE_SCHEMA_ON_STARTUP` | Set `false` in production; apply Alembic migrations externally |
| `TRUSTED_HOSTS` | Comma-separated allowed `Host` header values |
| `GOOGLE_GENAI_API_KEY` | Required when `AI_ENABLED=true` |
| `SARVAM_API_KEY` | Required for Sarvam STT/TTS voice pipeline |

---

## 13. Operational Runbooks

| Runbook | Purpose |
|---|---|
| [`reconciliation_operations_runbook.md`](runbooks/reconciliation_operations_runbook.md) | Ledger reconciliation, migration rehearsal, background job monitoring |
| [`phase5_controlled_launch_checklist.md`](runbooks/phase5_controlled_launch_checklist.md) | Pre-flight, cutover, rollback criteria, SLA compliance checks |
| [`phase5_migration_runbook.md`](runbooks/phase5_migration_runbook.md) | Opening inventory import: staging, validation, rehearsal, apply |
| [`security_operations_runbook.md`](runbooks/security_operations_runbook.md) | Secret rotation, JWT expiry policy, audit log review |
| [`voice_receiving_runbook.md`](runbooks/voice_receiving_runbook.md) | Voice dock setup, browser permissions, Sarvam key configuration |
| [`ai_operations_runbook.md`](runbooks/ai_operations_runbook.md) | AI copilot health check, Gemini API key rotation, audit review |
| [`ui_acceptance_runbook.md`](runbooks/ui_acceptance_runbook.md) | Role-by-role UAT checklist for all 5 personas |

---

## 14. Non-Negotiable Invariants

1. A completed receipt cannot be applied twice without a manager-approved, audited exception.
2. Concurrent orders cannot reserve the same last available units.
3. Every stock change has an actor, timestamp, reason, source workflow, and source record.
4. Damaged, quarantined, returned-uninspected, and in-transit units are never sellable.
5. Inventory is isolated by seller, SKU, warehouse, location, lot (when applicable), and state.
6. Sellers access only their own records.
7. AI cannot directly mutate inventory, orders, transfers, shipments, returns, or seller communications.
