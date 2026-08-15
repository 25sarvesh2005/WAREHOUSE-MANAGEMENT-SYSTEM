# Whitfield Fulfillment Warehouse Operations Platform Web Application

Custom-built web application for the Whitfield Fulfillment Warehouse Operations Platform, providing multi-warehouse inventory management, transactional ledger tracking, order fulfillment, stock transfer orchestration, customer returns processing, and Phase 5 opening inventory migration tooling.

## Features

- **Dashboard**: Live operational metrics across Reno (RNO) and Columbus (CMH) facilities.
- **Inventory & Ledger**: Query-optimized operational balances and append-only movement ledger views.
- **Receiving & Drafts**: Carrier tracking and drop-off ticket intake with sellable, damaged, and quarantine state separation.
- **Orders & Pick Tasks**: Transactional stock reservation, picking tasks, short-pick exception handling, and packing confirmation.
- **Transfers**: Inter-warehouse transfer dispatch, in-transit accounting, variance tracking, and manager discrepancy resolution.
- **Returns Intake**: Expected and unidentified return intake, condition inspection, and inventory disposition workflows.
- **Opening Inventory Migration**: Staged import batch management, automated raw row validation, role-guarded approval, and ledger application.
- **Seller Portal & Visibility**: Scoped inventory, order, receipt, shipment, and return views isolated by seller tenant.
- **Admin Panel**: User role assignment, staff hierarchy, pending seller approvals, warehouse locations, and catalog SKUs.

## Tech Stack

- **Framework**: Vite, React 19, TypeScript
- **Routing**: TanStack Router
- **Data Fetching & State**: TanStack Query v5
- **UI & Iconography**: TailwindCSS 4, Radix UI primitives, Lucide Icons, Recharts
- **Forms & Validation**: React Hook Form, Zod

## Running Locally

```sh
npm install
npm run dev
```

The application connects to the backend API at `http://127.0.0.1:8080/api/v1` (proxied via Vite during development — set `VITE_API_BASE_URL` in `.env` to override).
