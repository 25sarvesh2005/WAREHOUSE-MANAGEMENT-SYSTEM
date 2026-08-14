# Whitfield Operations Platform — UI Acceptance & E2E Runbook

This runbook defines the operational procedures for executing automated browser tests (Playwright), performing role-based UI acceptance testing, and verifying production launch readiness for the Whitfield Fulfillment Warehouse Operations Platform.

---

## 1. Local Environment Startup

### 1.1 Backend API (FastAPI)
Run from repository root (`c:\Partition\major_project`):

```bash
# 1. Activate Python virtual environment (if applicable)
# 2. Verify database schema status
python -m alembic current

# 3. Start FastAPI server on port 8000
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Backend Health Check:
```bash
curl http://127.0.0.1:8000/api/v1/health/status
```

### 1.2 Frontend Web App (Vite / TanStack Start)
Run from `frontend/` directory:

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Frontend URL: [http://127.0.0.1:5173](http://127.0.0.1:5173)

---

## 2. Automated Playwright E2E Testing

Playwright tests run in headless Chromium with deterministic API mock responders for safe local and CI execution without database mutation.

### 2.1 Test Commands

```bash
# Run complete E2E test suite (Headless Chromium)
npm --prefix frontend run test:e2e

# Run with interactive Playwright UI Runner (for debugging)
npm --prefix frontend run test:e2e:ui

# Run in headed browser mode (visible browser window)
npm --prefix frontend run test:e2e:headed

# Run a specific spec suite
npx --prefix frontend playwright test e2e/auth.spec.ts
npx --prefix frontend playwright test e2e/navigation.spec.ts
npx --prefix frontend playwright test e2e/operations.spec.ts
npx --prefix frontend playwright test e2e/ai_assistant.spec.ts
npx --prefix frontend playwright test e2e/admin_console.spec.ts
```

### 2.2 Test Suite Architecture

| Spec File | Coverage Area | Key Assertions |
|---|---|---|
| `e2e/auth.spec.ts` | Sign In, Validation & Sign Out | Branding rendering, 8+ char password validation, session storage, clean logout redirection |
| `e2e/navigation.spec.ts` | App Shell & Sidebar | All 11 navigation links rendered, active tab transitions across all warehouse pages |
| `e2e/operations.spec.ts` | Core Warehouse Pages | Balances, Inbound Receipts, Orders, Transfers, Returns, and Migration staging |
| `e2e/ai_assistant.spec.ts` | Read-only AI Assistant | Safety banner, read-only mode switching, SKU availability lookup, feedback widget |
| `e2e/admin_console.spec.ts` | Admin & Launch Governance | Master data tabs, AI Audit table & detail drawer, Controlled Launch checklist & evidence export |

---

## 3. Production Hardening & Security Checks

Before any deployment, execute the autonomous security verification tools:

```bash
# 1. Verify environment configuration, secret strength, and .env.example safety
python tools/verify_production_env.py

# 2. Audit frontend codebase for leaked API keys, tokens, or backend credentials
python tools/audit_frontend_secrets.py

# 3. Run full backend static compilation and unit test suite
python -m compileall main.py common core cli tools tests
python -m pytest

# 4. Run frontend typecheck, linter, and production build
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

---

## 4. Role-Based Manual Acceptance Checklists

### 4.1 Administrator (`ADMINISTRATOR`)
- [ ] **Authentication**: Sign in with Administrator credentials (`admin@whitfield.local`).
- [ ] **Navigation**: Verify sidebar displays all sections: Dashboard, Inventory, Receipts, Orders, Pick Tasks, Shipments, Transfers, Returns, Migration, AI Assistant, and Admin.
- [ ] **User & Staff Hierarchy**: Navigate to Admin -> Users & Staff Hierarchy. Confirm staff list renders with assigned roles and warehouse assignments.
- [ ] **Pending Seller Approvals**: Navigate to Admin -> Pending Sellers. Verify pending seller accounts can be reviewed and approved.
- [ ] **Master Data**: Verify Warehouses and Products tabs show live warehouse and SKU catalogs with add/edit capabilities.
- [ ] **Opening Inventory Migration**: Navigate to Migration tab. Verify file upload staging, 4-tier validation, and approval workflow.
- [ ] **AI Audit & Provider Health**: Navigate to Admin -> AI Audit & Provider Health. Verify:
  - Provider health card shows `Google Gemini` (`gemini-3.1-flash-lite-preview`) as `Operational & Healthy`.
  - AI Interaction Audit Log renders recent prompts, safety decisions (`ALLOW_READ_ONLY`), and feedback counts.
  - Detail drawer displays full sanitized prompt excerpt and tool execution trace.
- [ ] **Controlled Launch & Health**: Navigate to Admin -> Controlled Launch & Health. Verify:
  - System diagnostics cards: Database connected, Alembic revision current, AI provider healthy.
  - Pre-Launch Verification Checklist: 10 automated health checks present.
  - Click `Export Launch Evidence` and verify JSON download initiates.

---

### 4.2 Warehouse Manager (`WAREHOUSE_MANAGER`)
- [ ] **Operational Dashboard**: Sign in as Warehouse Manager. Verify SKU count, total units, active orders, and pending receipts KPI cards render.
- [ ] **Inventory Visibility**: Navigate to Inventory. Verify filtering by state (`AVAILABLE`, `ALLOCATED`, `DAMAGED`, `RESERVED_TRANSFER`, `INSPECTION`).
- [ ] **Exceptions Monitoring**: Check Manager Dashboard for exception alerts (overdue receipts, short picks, transfer discrepancies).
- [ ] **Transfer Orchestration**: Navigate to Transfers. Verify initiating inter-warehouse stock transfer drafts between origin and destination centers.
- [ ] **Return RMA Authorizations**: Navigate to Returns. Verify RMA receipts and routing to quality inspection.

---

### 4.3 Warehouse Staff (`RECEIVER`, `PICKER`, `PACKER`)
- [ ] **Inbound Receiving (`RECEIVER`)**:
  - Navigate to Receipts.
  - Verify inbound staging queue.
  - Stage a receipt, enter received line quantities, and complete receiving to trigger movement ledger entry.
- [ ] **Pick Tasks (`PICKER`)**:
  - Navigate to Pick Tasks.
  - Verify allocated orders appear in pick queue with bin locations and quantities.
  - Confirm pick task completion transitions order status.
- [ ] **Packing & Shipping (`PACKER`)**:
  - Navigate to Shipments.
  - Verify package weight, dimensions, tracking carrier assignment, and dispatch confirmation.

---

### 4.4 Seller (`SELLER`)
- [ ] **Seller Onboarding**: Access `/signup` to register a seller organization. Status enters `PENDING_APPROVAL`.
- [ ] **Seller-Scoped Inventory**: Sign in as approved Seller. Verify inventory balances show ONLY products owned by this seller.
- [ ] **Order Tracking**: Verify customer orders containing seller SKUs are visible with fulfillment progress status.
- [ ] **Read-Only AI Assistant**: Access `/ai-assistant`. Ask stock availability queries; confirm seller-scoped records are returned without cross-seller data leakage.

---

## 5. Troubleshooting & Support

| Symptom | Cause | Resolution |
|---|---|---|
| E2E test timeout on page load | Vite dev server not running or proxy unreachable | Run `npm --prefix frontend run dev` or verify port `5173` is available. |
| 401 Unauthorized during manual testing | Session token expired | Click `Reset local session` on login page or sign in again. |
| AI Assistant returns mock fallback | `GEMINI_API_KEY` not set in `.env` | Add valid Gemini API key to `.env` or run in simulated mock mode for offline testing. |
| Alembic revision mismatch | Pending database migrations | Run `python -m alembic upgrade head`. |
