# Specification: WMS Repository Simplification & Build Alignment

## 1. Context & Purpose
The Whitfield Warehouse Management System (WMS) is an enterprise fulfillment platform comprising:
- A FastAPI backend (Python 3.11/3.13) with PostgreSQL 16 (asyncpg/SQLAlchemy 2.0).
- A React 19 / TanStack Router / Vite 8 / TailwindCSS 4 frontend with SSR capabilities via Nitro.
- Bicoastal multi-tenant logistics (Reno `RNO`, Columbus `CMH`).

This simplification effort traces all files, features, documentation, and build targets to their concrete purpose. It resolves build path defects, eliminates obsolete or redundant configuration, aligns standard ports (standardizing on `8080`), and ensures accurate, unified documentation without modifying core WMS domain behavior.

---

## 2. Goals & Non-Goals

### Goals
1. **Document & Tooling Hygiene:**
   - Audit untracked directories (`.agent`, `.agents`, `.gemini`, `adapters`, `scripts`) and tracked docs (`README.md`, `docs/ARCHITECTURE.md`, runbooks).
   - Clean up empty, unreferenced tooling directories while preserving all local development data, secrets (`.env`), caches, logs, and generated artifacts.
   - Accurately classify all repository documents as **keep**, **update**, or **remove**.
2. **Build Path & Deployment Simplification:**
   - Confirm and preserve the established dual-target production deployment: **Render** for FastAPI backend container (`render.yaml`) and **Vercel** for Vite/Nitro frontend (`warehouse-management-system-jade-seven.vercel.app`).
   - Preserve local development workflow via Docker Compose (PostgreSQL, backend, frontend dev server) and native host execution.
   - Add a root `.dockerignore` to streamline Render Docker builds and prevent leaking unneeded frontend bundles or local secrets into backend images.
   - Unblock backend CLI tools in containerized environments by ensuring `tools/` is not excluded in `backend/.dockerignore`.
3. **Concrete Defect Remediation:**
   - Resolve the frontend Docker build defect where `frontend/Dockerfile` expected `.output/server/index.mjs` but `vite.config.ts` hardcoded the `vercel` preset even in non-Vercel environments.
   - Set `ENV NITRO_PRESET=node-server` in `frontend/Dockerfile` and correct `frontend/vite.config.ts` preset logic so Vercel builds use `vercel` while standalone Docker/Node builds use `node-server`.
   - Standardize default backend port from `8000` to `8080` in `settings.py`, E2E test defaults, Postman collections, and runbooks.
   - Fix documentation discrepancies (e.g., `/readyz` -> `/health/ready` probe in `backend/README.md`).
4. **CI Pipeline Optimization:**
   - Adopt deterministic `npm ci` in GitHub Actions frontend workflow.
   - Keep all essential regression prevention checks (backend unit tests, secret audit, live E2E scenarios, concurrency load tests, frontend typecheck/lint/build, and Playwright E2E).

### Non-Goals
- Redesigning or rewriting WMS business logic, controllers, database models, or API contracts.
- Migrating frontend away from Vercel or backend away from Render.
- Altering core RBAC permissions, outbox event schema, or double-entry ledger mechanics.
- Deleting local developer databases, virtual environments, logs, or `.env` files.

---

## 3. Document Classification Matrix

| Document / Path | Status | Justification / Action |
|---|---|---|
| `README.md` | **KEEP & UPDATE** | Primary repository landing page. Align status badges, port numbers, and deployment descriptions. |
| `docs/ARCHITECTURE.md` | **KEEP** | Authoritative architecture and invariant reference. Highly accurate; retain as source of truth. |
| `docs/runbooks/*.md` (7 runbooks) | **KEEP & UPDATE** | Critical operational runbooks (reconciliation, launch checklist, migration, security, voice, AI). Update `ui_acceptance_runbook.md` to reference port 8080 instead of 8000. |
| `frontend/README.md` | **KEEP** | Accurate frontend component and local dev reference. |
| `backend/README.md` | **KEEP & UPDATE** | Core backend guide. Fix `/readyz` probe reference to `/health/ready`. |
| `frontend/src/routes/README.md` | **KEEP** | Concise TanStack Router file-based convention reference. |
| `backend/core/database/migrations/README` | **KEEP** | Standard Alembic configuration marker. |
| `.agent/`, `.agents/`, `adapters/`, `scripts/` | **REMOVE** | Empty, untracked directories left by prior external tooling templates. No files or references exist. |
| `.gsd/` | **KEEP** | Houses this specification (`SPEC.md`) and project planning artifacts. |

---

## 4. Implementation Plan

1. **Clean Untracked Tooling Residue:**
   - Remove empty directories `.agent`, `.agents`, `adapters`, `scripts`, `.gemini` (leaving `.gsd` with `SPEC.md`).
2. **Frontend Build & Nitro Preset Alignment:**
   - In `frontend/vite.config.ts`, update Nitro preset to `process.env["NITRO_PRESET"] || (process.env["VERCEL"] ? "vercel" : "node-server")`.
   - In `frontend/Dockerfile`, set `ENV NITRO_PRESET=node-server` before build step, ensuring `.output/server/index.mjs` is compiled for the container runner.
3. **Backend & Root Docker Improvements:**
   - Create root `.dockerignore` to keep Render build contexts small and secure.
   - Adjust `backend/.dockerignore` to ensure `tools/` is accessible for CLI commands.
   - Align `backend/Dockerfile` CMD with root `Dockerfile` (avoid fixed `--workers 2` memory contention on free tiers).
4. **Port & Probe Normalization:**
   - Update `warehouse_api_base_url` default in `backend/core/config/settings.py` to `http://127.0.0.1:8080`.
   - Update `DEFAULT_API_BASE_URL` in `backend/tests/e2e/*.py` to `http://127.0.0.1:8080/api/v1`.
   - Update port 8000 to 8080 in Postman collections and `ui_acceptance_runbook.md`.
   - Correct `/readyz` reference to `/health/ready` in `backend/README.md`.
5. **CI Optimization:**
   - In `.github/workflows/ci.yml`, update frontend dependency installation to `npm ci` with `cache-dependency-path: frontend/package-lock.json`.
6. **Verification:**
   - Run frontend `typecheck`, `lint`, and `build` (both default and with `NITRO_PRESET=node-server`).
   - Run backend compilation (`python -m compileall`) and test suite.
   - Verify documentation and cross-references.
