# Whitfield frontend rehaul notes

Document ID: `DOC-FE-REHAUL-2026-08-14`

Scope: public entry pages and authenticated warehouse operations frontend.

Authority:

- `IMPLEMENTATION.md`
- `eigi-skills-main/problem/Case-Study-Whitfield-Fulfillment.pdf`

## Purpose

The frontend was adjusted away from a generic SaaS or marketing feel and toward a professional warehouse operations console for Whitfield Fulfillment.

The client problem is operational: two warehouses, spreadsheet replacement, duplicate receipt prevention, damaged-stock separation, server-side reservations, ledger-backed inventory, role-based access, and manager visibility. The UI should make those constraints obvious before an operator clicks anything dangerous.

## Rehaul decisions

- The visual language now follows the referenced `sparky-frontend-craft` style direction without copying unlicensed source: white is the primary surface color, blue is the secondary/accent color, and the interface uses rounded card/pill structures.
- The public landing, login, and signup pages now read as an operations entry point, not a generic SaaS marketing site.
- The authenticated shell now uses a light sidebar, pill navigation, rounded search, and soft blue status chips.
- Navigation is grouped by warehouse workflow: command, warehouse floor, fulfillment, control, and administration.
- Reno and Columbus are surfaced as first-class operational facilities.
- Ledger-backed and role-scoped behavior is called out in the chrome and dashboard.
- The dashboard is exception-first but modernized into large rounded option cards.
- Warehouse identifiers such as SKUs, tracking numbers, movement references, and location codes use compact monospace treatment.
- AI and voice UI are framed as read-only or draft-only helpers, not autonomous mutation tools.

## Main files updated

- `frontend/src/components/AppShell.tsx`
- `frontend/src/components/Dashboard.tsx`
- `frontend/src/components/Landing.tsx`
- `frontend/src/components/ReceivingVoiceDraftPanel.tsx`
- `frontend/src/components/ui-kit.tsx`
- `frontend/src/routes/login.tsx`
- `frontend/src/routes/signup.tsx`

Formatting was also normalized by the frontend lint fixer in adjacent files that already existed.

## Validation evidence

The following checks passed after the rehaul:

| Check | Command | Result |
| --- | --- | --- |
| Lint | `npm.cmd --prefix frontend run lint` | Passed |
| TypeScript | `npm.cmd --prefix frontend run typecheck` | Passed |
| Production build | `npm.cmd --prefix frontend run build` | Passed |
| Frontend secret audit | `.venv\Scripts\python tools\audit_frontend_secrets.py` | Passed |
| Encoding artifact scan | scanned frontend source for common mojibake replacement characters | No matches |

## Remaining frontend polish

The public entry pages and authenticated console are now aligned with the warehouse operations direction. The remaining frontend polish should focus on:

1. Browser UAT for dashboard, receipt creation, AI assistant, voice draft, migration panel, transfers, and returns.
2. Role-specific walkthrough checks for admin, warehouse manager, floor operator, and seller users.
3. Mobile or tablet dock-flow tuning for barcode scanner use at receiving stations.
