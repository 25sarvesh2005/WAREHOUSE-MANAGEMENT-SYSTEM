# Codebase cleanup and optimization plan

## Goal

Reduce code and runtime work that the application does not need, make the frontend and backend easier to navigate, and preserve the warehouse workflows and their safety rules. “AI bloat” means dead code, duplicated scaffolding, inflated copy, and unnecessarily eager code loading; it does not mean removing the read-only AI or voice features without evidence that they are unused or unwanted.

## Guardrails

- Trace references and runtime entry points before deleting or moving a file.
- Keep generated files such as `frontend/src/routeTree.gen.ts` generated; change their source configuration instead.
- Keep the backend's routes/controllers/CRUDs/services separation and database migrations in place. Inventory, authorization, idempotency, and audit behavior must remain intact.
- Avoid dependency upgrades and broad formatting churn in this cleanup.
- Make small, reviewable changes and check the production build, type checking, and lint after each meaningful frontend step. Run backend static checks when the required tool is available; do not substitute for tests when behavior changes.

## Steps

1. **Inventory and dead-code baseline — active**
   - Map repository and feature-folder structure, production entry points, generated code, and build scripts.
   - Enable TypeScript unused-local/parameter checks and remove confirmed unused imports.
   - Check source files and dependencies for unreferenced items before removal.

2. **Runtime and bundle audit**
   - Record production chunk sizes and identify eager imports of large, tab-only or workflow-only panels.
   - Lazy-load verified noncritical panels where doing so reduces initial work without changing loading or error behavior.
   - Simplify demonstrably redundant request, render, or serialization work; retain query caching and server-side authorization.

3. **Frontend feature organization**
   - Keep route files under `frontend/src/routes` and shared primitives in `components/ui` or a small shared area.
   - Group larger domain components by feature (AI, receiving, migration, administration/integrations) only where import references are clear.
   - Update imports and generated route artifacts through the router tooling; avoid a mass move of small, already discoverable files.

4. **Backend code and dependency audit**
   - Use static analysis to find unused imports, unreachable helpers, duplicate code, and unused dependencies.
   - Keep infrastructure in `common`, domain orchestration in controllers/services, persistence in CRUD modules, and route schemas at the API boundary.
   - Refactor only after callers and transaction boundaries are understood; do not remove jobs, migrations, operational tools, or AI/voice capabilities based on names alone.

5. **Closeout and structure documentation**
   - Re-run typecheck, lint, production build, and available backend static checks.
   - Update architecture documentation to match the verified tree and list any remaining high-risk candidates for separate work.

## Initial findings

- The backend already has a recognizable layered structure (`apis`, `controllers`, `cruds`, `models`, `services`, `jobs`, `database`); there is no evidence yet that a backend folder migration would help.
- The frontend has generated TanStack route registration and feature route files. Keep the generated route tree out of hand edits.
- The frontend TypeScript config initially disabled unused-local and unused-parameter diagnostics. They are now enabled, and the three unused Lucide imports found in `WebhookIntegrationsPanel.tsx` have been removed.
- Admin API queries now run only for the selected data tab; panel code also loads only when its tab is selected.
- Production output showed the admin route at 67.61 KB (14.16 KB gzip). Loading the four inactive tab panels on demand reduced that route chunk to about 22.6 KB (5.4 KB gzip), a 67% reduction in raw chunk size.
- The source import graph reaches all 60 frontend TypeScript modules from the application entry points; no orphan frontend source modules were found.
- Larger frontend panels now live under `src/features/{ai,admin,migration,receiving}/components`; shared shell, dialog, badge, and UI primitives remain in `src/components`.
- Backend Ruff analysis found 59 unused imports and two unused local assignments in addition to the frontend dead imports. Those confirmed symbols have been removed, as have 27 import-order/deprecated-import/style findings and one ambiguous local name. All E501 long-line findings have now been cleared across runtime, operational, seed, and test files. The broader Ruff scan reports only 24 delayed imports, reviewed as intentional for dotenv initialization or the load-test script's path setup; one avoidable test import was moved to the top.
- The backend reachability review confirmed two future-only stubs with no runtime callers: the unused idempotency normalizer (which was only tested as planned functionality) and a Pipecat streaming-session placeholder. Both and their placeholder-only references/tests were removed. Existing idempotency keys in inventory and workflow operations remain unchanged.
- MCP status tools now share evidence summary/detail serialization helpers, preserving their existing UUID handling while removing repeated conversion expressions.
- Reflowed long expressions and schema descriptions in webhook and MCP runtime modules; behavior and returned text remain unchanged.
- Reflowed remaining long conditions and output formatting in the production environment verifier and reservation load tool.
- Reflowed request/report lines in the Postman verifier without changing its URLs or output messages.
- Reflowed seed fixture records, seed conditions, and inventory reconciliation output without changing seeded values or calculations.
- Updated the architecture guide, reconciliation runbook, and README to document outbox claim leases, retry behavior, and at-least-once delivery. Worker-cycle logs now include dead-letter transitions.
- A backend AST scan found repeated database reads inside seller-assignment and order-line loops. Seller activation now loads assigned seller rows in one query, and order creation fetches all referenced products in one query. Other loop awaits inspected so far perform transaction-sensitive inventory movements, validation, seed setup, or job dispatch and were retained.
- Reservation expiry now recomputes each affected order's status once after processing the batch instead of rescanning its lines for every expired reservation. Outbox dispatch now commits a per-event claim with a lease before network work, records delivery attempts afterward, and finalizes only when the claim token still matches. Expired claims can be retried after worker failure.
- The largest frontend AI module mixed view state with its supported intent catalog. The catalog and query-prefix routing now live in `src/features/ai/intent-catalog.ts`, reducing `AiAssistant.tsx` from 1,127 to 944 lines without changing its runtime imports or routes. Other large files are domain workflows; size alone did not establish dead or duplicate code.
- Alembic migration revisions, package initializers, and operational modules were retained because they are loaded by framework conventions or operational workflows rather than ordinary static imports.
- The dependency source audit found two unused frontend direct dependencies (`@radix-ui/react-slot`, `@tanstack/router-plugin`) and an unused backend `passlib` dependency. Frontend packages were removed as direct dependencies (the router plugin remains as a declared transitive dependency of TanStack Start); backend manifests no longer install `passlib` because authentication uses `bcrypt` directly.
- Backend `pytest` and `pytest-asyncio` were installed in production via `requirements.txt`. They now live in `requirements-dev.txt`, and CI’s unit-test job installs that dev manifest while Docker and E2E jobs keep the runtime manifest.
- CI now runs the passing Ruff dead-symbol, import-order, deprecated-import, and ambiguous-name checks to prevent those categories from regressing.
- `npm audit` initially found 11 production advisories. TanStack Start/Router were updated to the upstream patched releases and compatible versions; non-forced transitive fixes cleared the remaining advisories. The full npm audit now reports zero vulnerabilities.
- Rolldown’s documented module-directive warning was limited to third-party `"use client"` markers that are not used as React Server Component boundaries in this app. The Vite and Nitro bundler hooks now filter only that warning code/message; other warnings continue through unchanged. Both client and SSR builds complete without those warnings.
- The working tree contains existing backend and frontend modifications. Cleanup must preserve those changes.

## Progress

- [x] Plan and cleanup guardrails recorded.
- [x] Remove confirmed unused imports and enforce TypeScript unused checks.
- [x] Measure and optimize route/panel loading.
- [x] Move larger frontend feature panels into feature-owned folders and update imports.
- [x] Remove confirmed unused frontend/backend imports and unused script locals.
- [x] Complete the frontend import-graph and direct-dependency audit; remove verified unused dependencies.
- [x] Patch dependency advisories without a forced major upgrade.
- [x] Complete backend module/dependency reachability audit and remove confirmed future-only scaffolding.
- [x] Filter the verified third-party Vite/Rolldown directive warnings while preserving all other warnings.
- [x] Separate AI intent definitions and routing from the assistant view.
- [x] Centralize repeated MCP status evidence serialization.
- [x] Review delayed imports and reflow overlong expressions in webhook and MCP runtime modules.
- [x] Clear the remaining long-line findings across backend test files without changing test behavior.
- [x] Scan database-await loops for per-record lookups and batch-confirmed identity/order reads.
- [x] Reduce repeated order-line scans in reservation-expiry processing.
- [x] Add leased outbox claims so HTTP delivery does not hold database row locks.
- [x] Update architecture documentation to reflect the verified frontend feature folders.
- [x] Run final static checks after this cleanup pass (frontend typecheck, lint and production build; backend Ruff hygiene and compileall; `git diff --check`).
