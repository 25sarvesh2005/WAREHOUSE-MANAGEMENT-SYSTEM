# Whitfield Fulfillment — Warehouse Operations Platform

A multi-warehouse, multi-tenant (seller) warehouse management system built for
two physical locations (Reno, NV and Columbus, OH). It replaces spreadsheet
operations with an auditable, transactional inventory ledger covering
receiving, orders/fulfillment, transfers, returns, and a read-only AI
assistant.

Full architecture and design rationale live in [`IMPLEMENTATION.md`](./IMPLEMENTATION.md).
This README describes what is actually implemented in the codebase today.

## Status

Early-stage, single-branch backend + frontend scaffold (~35k lines of Python,
~95 API routes, 17 frontend route files). Not yet production-launched — no
tagged releases, no pilot/cutover has occurred. Treat this as a working
foundation, not a finished product.

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Database | PostgreSQL (async SQLAlchemy 2.x + `asyncpg`), Alembic migrations |
| Auth | JWT (`python-jose`), bcrypt password hashing |
| Frontend | Vite, React, TypeScript, TanStack Router |
| AI | Read-only assistant behind permission-scoped application tools (no direct DB access, no autonomous mutation) |
| Voice | Optional Deepgram/Sarvam providers for structured receiving drafts |
| CLI | Typer-based operational commands |

## What's implemented

- **Domain coverage**: identity/auth, catalog (products, identifiers,
  locations), inventory ledger + balances, receiving, orders & fulfillment,
  transfers, returns, seller portal, reporting, migration/import tooling, AI
  read-only assistant, and voice-assisted receiving — each with its own
  model, CRUD, controller, and route module (`core/models`, `core/cruds`,
  `core/controllers`, `core/apis/routes`).
- **Inventory integrity**: `core/cruds/inventory_crud.py` uses
  `SELECT ... FOR UPDATE` row locking when reading/mutating balance rows,
  matching the concurrency-safety design in the spec.
- **Layering**: routes → controllers → CRUD/services boundaries are followed
  consistently; CRUD modules don't raise `HTTPException`, controllers don't
  touch SQLAlchemy queries directly.
- **CI**: `.github/workflows/ci.yml` spins up a real PostgreSQL service
  container, runs a FastAPI import check, `compileall`, the pytest suite, a
  frontend-secret audit script, and separate frontend lint/typecheck/build
  jobs.
- **Frontend**: route tree exists for receipts, returns, and transfers with
  a component/hooks/lib structure in place.
- **Tooling**: CLI commands, opening-inventory import/reconciliation
  scripts, an expired-reservation release job, and a frontend
  secret-leak auditor (`tools/audit_frontend_secrets.py`).

## Known gaps vs. the design spec

These are worth knowing before relying on this as "production":

- **Outbox pattern is modeled but not wired up.** `core/models/outbox_model.py`
  exists, but no controller or CRUD currently inserts an `outbox_events` row
  — the async event-publishing described in `IMPLEMENTATION.md` §13.1 isn't
  connected to business transactions yet.
- **Unit tests are shallow.** `tests/unit/*` mostly validate Pydantic
  schemas and enum values, not transactional business logic, concurrency, or
  permission boundaries.
- **"E2E tests" are manual smoke scripts**, not CI-integrated pytest
  suites — they're standalone scripts (`tests/e2e/phase*_e2e_test.py`) meant
  to be run against a live server (`python -m tests.e2e.phase3_e2e_test`),
  covering things like the concurrent last-unit reservation race and ledger
  reconciliation. They are not automatically executed by CI today.
- **No `mcp_server/` directory** despite the MCP server being specified in
  §14.5 — not yet built.
- **Single commit history** — the repository currently reflects one large
  initial push rather than incremental, reviewed development, so there's no
  changelog or PR history to evaluate yet.
- **No tagged release, no completed pilot/reconciliation window** — the
  10-business-day pilot and cutover process described in the spec (§18) has
  not happened.

## Getting started (backend)

1. Create a Python 3.11+ environment.
2. `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and set `DATABASE_URL`,
   `MIGRATION_DATABASE_URL`, and `JWT_SECRET`.
4. Use the direct Supabase connection for both URLs when IPv6 is available.
   On an IPv4-only runtime, use the Supavisor session pooler on port 5432 for
   `DATABASE_URL` and keep the direct URL for migrations when reachable.
   Port 6543 (transaction pooling) is intentionally rejected — it's reserved
   for serverless deployments, and this is a persistent backend.
5. Run database migrations, then start the API:
   ```bash
   alembic upgrade head
   uvicorn main:app --reload
   ```

Never commit real credentials or place Supabase secret/service-role keys in
frontend environment files — `tools/audit_frontend_secrets.py` scans for
exactly that.

## Getting started (frontend)

```bash
cd frontend
bun install   # or npm install
bun run dev
```

## Running tests

```bash
# Unit tests (schema/enum-level; no live DB required)
pytest tests/unit

# Manual E2E smoke scripts (require a running API + database)
python -m tests.e2e.phase2_e2e_test
python -m tests.e2e.phase3_e2e_test
python -m tests.e2e.phase4_e2e_test
python -m tests.e2e.phase5_e2e_test
```

## Launch hardening checks

Before any controlled launch, run the Phase 5 checklist in
[`docs/runbooks/phase5_controlled_launch_checklist.md`](./docs/runbooks/phase5_controlled_launch_checklist.md).
The repeatable frontend secret audit:

```bash
python -m tools.audit_frontend_secrets
```

It scans browser-delivered source and build artifacts for backend-only
secret markers (Supabase service-role keys, database URLs, JWT secrets).

## Repository layout

See [`IMPLEMENTATION.md`](./IMPLEMENTATION.md) §5 for the full intended
structure; the top-level layout in this repo is:

```
common/        shared auth, logging, pagination, rate limiting, idempotency, warehouse scope
core/          models, cruds, controllers, apis/routes, services, jobs, database, config
cli/           operational CLI (Typer)
tools/         import/reconciliation/migration/audit scripts
tests/         unit tests + manual e2e smoke scripts
docs/runbooks/ operational runbooks (launch checklist, etc.)
frontend/      Vite + React + TypeScript app
```

## Contributing / next steps

If you're picking this up, the highest-leverage next steps based on the gaps
above are: wire the outbox pattern into the receiving/order/transfer/return
controllers, replace schema-only unit tests with transactional PostgreSQL
integration tests (per `IMPLEMENTATION.md` §17), add the MCP server, and get
the e2e smoke scripts running in CI against the Postgres service container
that's already configured.
