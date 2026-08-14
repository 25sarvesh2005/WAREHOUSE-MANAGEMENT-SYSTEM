# Codebase Guide — Whitfield Fulfillment Warehouse Operations Platform

This document walks through the repository folder by folder, in the order a
new engineer should read it to understand how a request flows through the
system. It reflects the code as it actually exists in the repository (not
just the design intent in `IMPLEMENTATION.md`).

---

## 0. The one-sentence mental model

```
HTTP request → route (validates + authenticates) → controller (business rules
+ transaction) → CRUD (SQL only) → PostgreSQL
```

Every folder below exists to keep exactly one of those responsibilities in
one place. Nothing is allowed to skip a layer — routes never touch SQL,
CRUD never returns HTTP errors, controllers never write raw queries.

---

## 1. Root level — where to start reading

```
main.py                 FastAPI app factory + startup/shutdown lifecycle
requirements.txt        Pinned Python dependencies
pyproject.toml          Project metadata, pytest config, ruff lint config
alembic.ini              Alembic migration tool configuration
.env.example             Every environment variable the app understands
.gitignore
README.md                Project overview and setup instructions
IMPLEMENTATION.md        1,600-line engineering spec/architecture authority
postman_collection.json  Importable Postman collection for manual API testing
postman_environment.json Postman environment variables (base URL, tokens)
```

**Step 1: open `main.py`.** This is the actual entry point — it builds the
FastAPI app, wires the lifespan (startup connects to the database and
optionally seeds schema; shutdown closes connections cleanly), registers
CORS, and mounts every router from `core/apis/api.py`. Reading this file
first tells you exactly what runs when the server starts.

**Step 2: skim `.env.example`.** Every setting the app reads is listed
here — database URL, JWT secret, AI provider keys, voice provider keys,
Cloudinary keys, MCP host/port, bootstrap admin credentials. This is the
fastest way to see what's configurable without reading `core/config/`.

---

## 2. `common/` — cross-cutting utilities used by everything

```
common/
├── auth.py              Password hashing (bcrypt), JWT encode/decode
├── logger.py            get_logger(__name__) — structured logging setup
├── warehouse_scope.py   Permission dependencies: get_warehouse_scope(),
│                        assert_seller_access(), assert_warehouse_access()
├── idempotency.py       Idempotency-Key request de-duplication helper
├── pagination.py        Cursor-based pagination helper for list endpoints
└── rate_limit.py        Rate limiters (e.g. ai_rate_limiter used on AI routes)
```

**Why this folder exists first:** almost every route and controller in the
codebase imports from here. `warehouse_scope.py` in particular is what
turns a JWT into "this user may only see seller X's data in warehouse Y" —
it's the single choke point for multi-tenant isolation, so it's worth
reading before anything else.

---

## 3. `core/config/` — typed settings

```
core/config/
└── settings.py    Pydantic BaseSettings class, loads from .env
```

**Step 3:** `settings.py` is where environment variables become typed,
validated Python objects (`Settings`), cached via `@lru_cache` through
`get_settings()`. Notably it also contains PostgreSQL/Supabase-specific
connection logic: it rejects port `6543` (Supabase's serverless transaction
pooler, unsafe for a persistent backend) and renders separate URLs for the
async runtime driver (`asyncpg`) versus the sync Alembic driver (`psycopg`).

---

## 4. `core/constants.py` — the vocabulary of the domain

A single file of enums: `InventoryState`, `InventoryMovementType`,
`OrderStatus`, `ReceiptStatus`, `TransferStatus`, `ReturnStatus`,
`UserRole`, `AISafetyDecision`, etc. **Read this before touching any
workflow code** — it's the shared vocabulary every model, schema, and
controller uses, and it tells you the full state machine for each entity
(e.g. every status an `Order` can be in) in one place.

---

## 5. `core/database/` — how the app talks to PostgreSQL

```
core/database/
├── base.py                 Declarative Base, TimestampMixin, UUIDPrimaryKeyMixin
├── database.py             Engine/session lifecycle: connect_to_database(),
│                            close_database_connection(), transaction_session(),
│                            check_database_ready()
├── seed.py                 Dev schema init + seed data + Supabase RLS lockdown
└── migrations/
    ├── env.py               Alembic environment (uses alembic_database_url)
    ├── script.py.mako       Template for new migration files
    └── versions/            11 migration files, in dependency order:
        ├── 3a78cc63e38a_initial_schema.py
        ├── e2b7a4c9d8f1_user_created_by_column.py
        ├── 99c67baa4a76_inventory_and_receiving.py
        ├── c9a20c29ffff_orders_and_fulfillment.py
        ├── 671b43c62846_transfers_and_returns.py
        ├── a6c2d8e4f0b1_staged_validation_errors_jsonb.py
        ├── d4a91f05c2e7_balance_non_negative_constraint.py
        ├── b7e6d5c4a3f2_ai_foundation_tables.py
        ├── c1f2e3d4a5b6_ai_feedback_table.py
        └── d2e3f4a5b6c7_voice_receiving_tables.py
```

**Step 4:** `database.py` owns exactly one `AsyncEngine` and one
`async_sessionmaker` for the whole app (singleton pattern). The important
function to understand is `transaction_session()` — an async context
manager that every controller uses to open a unit-of-work: if the block
raises, everything inside it rolls back automatically.

**Step 5:** open one migration file, e.g. `99c67baa4a76_inventory_and_receiving.py`.
Migrations run in the order shown above (each has a `down_revision` pointer
to the previous one) and are the actual source of truth for the database
schema — more reliable than reading the SQLAlchemy models alone, since they
show constraints (unique indexes, check constraints, foreign keys) exactly
as applied.

**`seed.py`** does two things at startup in development: creates all tables
from the SQLAlchemy models, and — specifically for Supabase — enables Row
Level Security on every table and revokes `anon`/`authenticated` role
privileges, so the only access path to data is through this FastAPI app,
never Supabase's auto-generated REST API.

---

## 6. `core/models/` — the database schema, as Python classes

```
core/models/
├── identity_model.py     User, Seller, Warehouse, assignments, service accounts
├── catalog_model.py      Product, ProductIdentifier, WarehouseLocation, policies
├── inventory_model.py    InventoryMovement (append-only ledger), InventoryBalance
├── receiving_model.py    Receipt, ReceiptLine, ReceiptEvent
├── order_model.py        Order, OrderLine, InventoryReservation
├── fulfillment_model.py  PickTask, PickTaskLine, Package, Shipment, ShipmentEvent
├── transfer_model.py     Transfer, TransferLine
├── return_model.py       Return, ReturnLine
├── migration_model.py    ImportBatch, staged rows for opening-inventory import
├── audit_model.py        AuditEvent — permission/policy/business action log
├── outbox_model.py       OutboxEvent — modeled but not yet written to (see §14)
├── ai_model.py            AIInteraction, AIToolCall, AIDraftAction, AIFeedback
└── voice_model.py         VoiceInteraction, VoiceReceivingDraft
```

**Step 6:** this is the most important folder to understand the *domain*.
Start with `inventory_model.py` — `InventoryMovement` is the append-only
ledger (every stock change ever made, immutable) and `InventoryBalance` is
the fast-read projection (current on-hand quantity per seller/product/
warehouse/location/state) that gets updated in the same transaction as each
movement insert. Every other model exists to produce movements against this
ledger through a specific workflow (receiving, ordering, transferring,
returning).

Models define **persistence shape only** — column types, constraints,
relationships. They never contain business logic; that lives in
controllers/services.

---

## 7. `core/cruds/` — raw database operations, one file per domain

```
core/cruds/
├── identity_crud.py
├── catalog_crud.py
├── inventory_crud.py      Includes get_balance_for_update() — SELECT FOR UPDATE
├── receiving_crud.py
├── order_crud.py
├── fulfillment_crud.py
├── transfer_crud.py
├── return_crud.py
├── migration_crud.py
├── audit_crud.py
├── reporting_crud.py
└── ai_crud.py
```

**Step 7:** each function here takes `session: AsyncSession` as its first
argument and does exactly one thing: run a SQLAlchemy query or write. CRUD
functions **never** raise `HTTPException` and **never** decide business
policy (e.g. whether a reservation is allowed) — they just fetch/write rows,
sometimes with explicit row-locking behavior named in the function itself
(`get_balance_for_update`). This is the layer to check when you want to know
exactly what SQL is executed for any given operation.

---

## 8. `core/controllers/` — where business rules actually live

```
core/controllers/
├── identity_controller.py
├── catalog_controller.py
├── inventory_controller.py
├── receiving_controller.py
├── order_controller.py
├── fulfillment_controller.py
├── transfer_controller.py
├── return_controller.py
├── migration_controller.py
├── reporting_controller.py
├── seller_portal_controller.py
├── ai_controller.py
└── voice_controller.py
```

**Step 8: this is the heart of the application.** Each controller class:

1. Opens a `transaction_session()` (the unit of work).
2. Checks permissions via `common/warehouse_scope.py` helpers.
3. Validates business rules (e.g. "is there enough available inventory?",
   "does this seller allow backorders?").
4. Calls one or more CRUD functions to read/write.
5. Assembles and returns response-ready data.
6. Raises a meaningful `HTTPException` (`403`, `404`, `409`, `422`) for
   expected rejections, or lets unexpected exceptions bubble up to be
   logged and converted to a `500` at the route layer.

Concurrency-critical logic lives here too: `inventory_controller.py` and
`order_controller.py` are where the "two orders race for the last unit"
problem is actually solved, by acquiring the balance row lock (via the CRUD
layer) inside a single transaction before deciding how much to reserve.

---

## 9. `core/apis/` — the HTTP surface

```
core/apis/
├── api.py                 Registers every router onto the FastAPI app
├── routes/                 13 route files, one per domain (thin wrappers)
│   ├── identity_routes.py
│   ├── catalog_routes.py
│   ├── inventory_routes.py
│   ├── receiving_routes.py
│   ├── order_routes.py
│   ├── fulfillment_routes.py
│   ├── transfer_routes.py
│   ├── return_routes.py
│   ├── migration_routes.py
│   ├── reporting_routes.py
│   ├── seller_routes.py
│   ├── ai_routes.py
│   └── voice_routes.py
└── schemas/
    ├── requests/            11 files — Pydantic models for request bodies
    └── responses/            11 files — Pydantic models for response bodies
```

**Step 9:** routes are intentionally boring. Each endpoint: declares a
`response_model`, gets the authenticated scope via `Depends(...)`, calls
**exactly one** controller method, and re-raises `HTTPException` unchanged
or converts unknown errors to a generic `500`. If you're trying to find
"what URL do I call to do X," start in `core/apis/routes/`; if you want to
know exactly what JSON shape is expected or returned, check the matching
file in `schemas/requests/` or `schemas/responses/`. There are 95 registered
endpoints across these 13 route files.

---

## 10. `core/services/` — external integrations and complex reusable logic

```
core/services/
├── import_export/
│   └── opening_inventory_parser.py   Parses CSV/XLSX opening-inventory files
├── ai/
│   ├── provider.py    SDK-isolated AI provider abstraction (Google Gen AI or Disabled)
│   ├── read_tools.py  Permission-scoped read-only queries the AI can call
│   ├── safety.py       Regex-based guardrails: refuse mutation/secret/cross-tenant asks
│   └── types.py         Provider-neutral request/response dataclasses
└── voice/
    ├── provider.py               Protocol for STT/TTS providers
    ├── deepgram_provider.py      Speech-to-text implementation
    ├── sarvam_provider.py        Alternate STT/TTS implementation
    ├── transcript_parser.py      Turns transcribed speech into structured drafts
    ├── pipecat_pipeline.py       Voice pipeline orchestration
    └── safety.py                  Voice-specific safety checks
```

**Step 10:** services own anything that talks to the outside world (AI
providers, voice providers, file parsing) or is complex enough to be reused
across controllers. Unlike controllers, services raise plain Python
exceptions, not `HTTPException` — the controller that calls them is
responsible for translating failures into the right HTTP status.

---

## 11. `core/jobs/` — background/scheduled work

```
core/jobs/
└── reservation_expiry_job.py   Releases expired inventory reservations
```

**Step 11:** currently the only implemented scheduled job. It finds
reservations past their expiry window and idempotently releases the
reserved quantity back to available stock through the normal ledger-write
path (not a direct balance edit). The design spec (`IMPLEMENTATION.md`
§13.2) describes several more scheduled jobs (aging receipts, delayed
transfers, uninspected returns, outbox dispatch) — only this one currently
exists in code.

---

## 12. `cli/` — operator command-line tool

```
cli/
├── main.py       Typer app: database-health, rehearse-migration,
│                 reconcile-migration, import-opening-inventory
└── __init__.py
```

**Step 12:** run with `python -m cli.main --help`. Each command is a thin
wrapper that calls the *same* controllers the API uses (e.g.
`rehearse-migration` drives `migration_controller` through create → stage →
validate → approve → apply → reconcile), so there's no separate/duplicated
business logic for the CLI path.

---

## 13. `tools/` — one-off / operational scripts

```
tools/
├── audit_frontend_secrets.py    Scans frontend build output for leaked secrets
├── import_opening_inventory.py  Called by the CLI import-opening-inventory command
├── reconcile_inventory.py       Rebuilds balances from the ledger and diffs them
├── reconcile_migration.py       Called by the CLI reconcile-migration command
├── rehearse_migration.py        Called by the CLI rehearse-migration command
├── release_expired_reservations.py  Standalone runner for the expiry job
└── verify_production_env.py     Pre-deploy environment sanity check
```

**Step 13:** these scripts back the CLI commands (§12) and are also runnable
directly, e.g. `python -m tools.audit_frontend_secrets`. Worth knowing:
`reconcile_inventory.py` is the practical implementation of the "ledger is
the source of truth" principle — it independently rebuilds balances from
`inventory_movements` and flags any mismatch against `inventory_balances`
rather than trusting the projection blindly.

---

## 14. `core/models/outbox_model.py` — a note on what's *not* wired up

The `OutboxEvent` model exists (table + columns for event type, payload,
attempt count, next-attempt time), matching the transactional-outbox
pattern described in the spec. However, **no controller or CRUD function
currently inserts a row into it.** If you're extending a workflow
(receiving, orders, transfers, returns) and want it to publish an event for
downstream consumers, this is the piece you'd need to connect — the model
is ready, the write-path isn't.

---

## 15. `tests/` — what's actually verified

```
tests/
├── conftest.py* (not present — see note below)
├── fixtures/
│   ├── opening_inventory_valid.csv
│   └── opening_inventory_invalid.csv
├── unit/                 19 files — schema/enum/helper-level tests, pytest-run
│   ├── test_auth_flows.py
│   ├── test_inventory_flows.py
│   ├── test_order_flows.py
│   ├── test_receiving_flows.py
│   ├── test_transfer_flows.py
│   ├── test_return_flows.py
│   ├── test_ai_foundation.py
│   ├── test_ai_read_only_flows.py
│   ├── test_ai_release_b_flows.py
│   ├── test_voice_receiving_flows.py
│   ├── test_master_data_flows.py
│   ├── test_migration_flows.py
│   ├── test_opening_inventory_parser.py
│   ├── test_common_helpers.py
│   └── test_fulfillment_flows.py
└── e2e/                  8 files — standalone smoke scripts, run manually
    ├── phase2_e2e_test.py    Receiving workflow against a live server
    ├── phase3_e2e_test.py    Concurrent last-unit reservation race, short-pick,
    │                          reservation expiry, ledger-vs-balance comparison
    ├── phase4_e2e_test.py    Transfers, returns, manager dashboards
    ├── phase5_e2e_test.py    Migration/cutover checks
    ├── phase5_file_import_e2e_test.py
    ├── ai_release_a_e2e_test.py
    └── ai_voice_receiving_e2e_test.py
```

**Step 14:**
- `pytest tests/unit` runs without a live database — these tests mostly
  validate Pydantic request/response schemas and enum values, not
  transactional correctness.
- The `tests/e2e/*.py` files are **not pytest tests** — they're standalone
  async scripts meant to be run directly against a running API + database
  (e.g. `python -m tests.e2e.phase3_e2e_test`), and they're where the
  *real* correctness guarantees (no oversell on concurrent reservation,
  ledger/balance parity) are actually exercised. They are not currently
  wired into CI.

---

## 16. `.github/workflows/ci.yml` — what runs automatically

On every push/PR to `main`/`master`/`develop`:

- **`backend-checks`**: spins up a real `postgres:15` service container,
  installs `requirements.txt`, runs a FastAPI import sanity check
  (`python -c "import main"`), `python -m compileall` across the backend,
  runs `pytest`, and runs `tools/audit_frontend_secrets.py`.
- **`frontend-checks`**: separate job, working directory `frontend/`,
  running lint/typecheck/build.

The manual `tests/e2e/*` scripts are **not** part of this pipeline today.

---

## 17. `frontend/` — the React application

```
frontend/
├── package.json / bun.lock / bunfig.toml   Bun-based package management
├── vite.config.ts
├── tsconfig.json
├── eslint.config.js
├── playwright.config.ts
├── components.json         shadcn/ui config
├── public/                 Static assets
├── e2e/                    Playwright test specs
└── src/
    ├── routes/              File-based routes (TanStack Router)
    │   ├── receipts/
    │   ├── returns/
    │   └── transfers/
    ├── components/
    │   └── ui/               shadcn/ui component primitives
    ├── hooks/                Custom React hooks
    ├── lib/                  API client and shared utilities
    └── assets/
```

**Step 15:** `bun install && bun run dev` (or `npm install && npm run dev`)
starts the dev server against `vite.config.ts`. Routes under `src/routes`
currently cover receipts, returns, and transfers — the rest of the intended
route map from `IMPLEMENTATION.md` §12.1 (dashboard, inventory, orders,
picking, shipments, exceptions, reports, admin, seller portal) is not yet
built out in the frontend folder tree.

---

## 18. `docs/runbooks/` — operational documentation

```
docs/runbooks/
├── phase5_controlled_launch_checklist.md
├── phase5_migration_runbook.md
├── reconciliation_operations_runbook.md
├── security_operations_runbook.md
├── ai_operations_runbook.md
├── voice_receiving_runbook.md
├── ui_acceptance_runbook.md
├── frontend_rehaul_notes.md
└── implementation_remaining_work_log.md
```

**Step 16:** these are written for warehouse managers/operators, not just
engineers — e.g. the controlled-launch checklist is the actual go/no-go
list to run through before cutting a warehouse over from spreadsheets. If
you want the most up-to-date, human-readable record of what's finished vs.
outstanding, `implementation_remaining_work_log.md` is the most current
source (more current than `IMPLEMENTATION.md`, which is the original spec
and doesn't get updated as work completes).

---

## 19. Suggested reading order, summarized

| Order | Path | Why |
|---|---|---|
| 1 | `main.py` | See what boots and in what order |
| 2 | `.env.example` | See every configurable setting |
| 3 | `core/constants.py` | Learn the domain vocabulary/state machines |
| 4 | `common/warehouse_scope.py` | Understand the permission model |
| 5 | `core/database/database.py` | Understand the transaction pattern |
| 6 | `core/models/inventory_model.py` | Understand the ledger/balance design |
| 7 | `core/cruds/inventory_crud.py` | See the row-locking implementation |
| 8 | `core/controllers/order_controller.py` | See business rules + concurrency handling |
| 9 | `core/apis/routes/order_routes.py` | See how it's exposed over HTTP |
| 10 | `tests/e2e/phase3_e2e_test.py` | See how the concurrency guarantee is actually tested |
| 11 | `core/services/ai/safety.py` | See how the AI assistant is constrained |
| 12 | `docs/runbooks/implementation_remaining_work_log.md` | See what's actually done vs. outstanding |

---

## 20. Quick facts

- **~35,000 lines** of Python across `main.py`, `common/`, `core/`, `cli/`, `tools/`, `tests/`
- **95 registered API endpoints** across 13 route files
- **13 domains**, each with a matching model / CRUD / controller / route file (identity, catalog, inventory, receiving, order, fulfillment, transfer, return, migration, reporting, seller portal, AI, voice)
- **11 Alembic migrations**, applied in sequence from initial schema through voice-receiving tables
- **19 unit test files**, **8 manual e2e smoke scripts**
- **17 frontend route files** under `frontend/src/routes`
- CI runs against a **real PostgreSQL 15 container**, not SQLite
