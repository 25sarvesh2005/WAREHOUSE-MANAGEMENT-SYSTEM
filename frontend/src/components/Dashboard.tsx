import { Link } from "@tanstack/react-router";
import {
  AlertTriangle,
  ArrowRight,
  Boxes,
  CheckCircle2,
  ClipboardList,
  Layers,
  PackageCheck,
  PackagePlus,
  Repeat,
  ShieldCheck,
  ShoppingCart,
  Truck,
  Undo2,
} from "lucide-react";
import type { ElementType } from "react";
import { ErrorState, LoadingState } from "@/components/ui-kit";
import { useManagerDashboardQuery, useManagerExceptionsQuery } from "@/hooks/use-api";
import { ROLE_SECTIONS } from "@/lib/auth";
import type { User } from "@/lib/types";

interface WorkflowItem {
  description?: string;
  icon?: ElementType;
  label: string;
  to: string;
}

function safeNumber(val: unknown): number {
  const num = Number(val ?? 0);
  return Number.isFinite(num) ? num : 0;
}

function formatRole(role: string): string {
  return role
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

function filterAllowedWorkflows(user: User, workflows: WorkflowItem[]): WorkflowItem[] {
  const allowed = ROLE_SECTIONS[user.role] ?? [];
  return workflows.filter((w) => allowed.includes(w.to));
}

function DashboardHeader({
  user,
  isManager,
}: {
  isManager: boolean;
  user: User;
}) {
  const firstName = user.name.trim().split(/\s+/)[0] || user.name;
  const formattedRole = formatRole(user.role);

  return (
    <header className="card-surface rounded-xl p-6 sm:p-7 transition-all">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md bg-blue-50 dark:bg-blue-950/60 border border-blue-200/80 dark:border-blue-900/60 text-[11px] font-semibold text-primary dark:text-blue-400">
              <span className="size-1.5 rounded-full bg-primary" />
              Operations overview
            </span>
          </div>

          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 sm:text-3xl">
            Welcome back, {firstName}.
          </h1>

          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-md bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-xs font-medium text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
              Signed in as <span className="font-semibold text-slate-900 dark:text-slate-100">{formattedRole}</span>
            </span>
          </div>

          <p className="max-w-2xl text-sm leading-relaxed text-slate-500 dark:text-slate-400 pt-0.5">
            {isManager
              ? "Review current inventory totals, open work, and exception queues reported by the WMS."
              : "Open the operational workflows available to your assigned role."}
          </p>
        </div>

        {/* Clean System Status Pill */}
        <div className="hidden lg:flex flex-col items-end gap-1.5 shrink-0">
          <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/60 p-3 flex items-center gap-3">
            <div className="size-8 rounded-md bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center justify-center text-primary dark:text-blue-400 shadow-2xs">
              <ShieldCheck className="size-4" />
            </div>
            <div className="text-right">
              <p className="text-[10px] font-semibold tracking-wider text-slate-400 dark:text-slate-500 uppercase">
                Outbox & Invariant Engine
              </p>
              <p className="text-xs font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-1.5 justify-end">
                <span className="size-1.5 rounded-full bg-emerald-500" />
                Ledger Balanced
              </p>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}

function MetricCard({
  label,
  value,
  to,
  isException = false,
  icon: Icon,
  accentColor,
}: {
  accentColor?: string;
  icon?: ElementType;
  isException?: boolean;
  label: string;
  to: string;
  value: number | string;
}) {
  return (
    <Link
      to={to}
      className={`group relative flex min-h-[44px] flex-col justify-between rounded-xl p-5 transition-all duration-150 hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
        isException
          ? "bg-amber-50/60 dark:bg-amber-950/20 border border-amber-200/90 dark:border-amber-900/50 hover:border-amber-300 dark:hover:border-amber-800 hover:shadow-xs"
          : "card-surface hover:border-slate-300 dark:hover:border-slate-700 hover:shadow-xs"
      }`}
    >
      {/* Top Header: Label + Icon */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p
            className={`text-xs font-semibold uppercase tracking-wider ${
              isException ? "text-amber-900 dark:text-amber-300" : "text-slate-500 dark:text-slate-400"
            }`}
          >
            {label}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {Icon ? (
            <div
              className={`size-8 rounded-lg flex items-center justify-center border transition-colors ${
                isException
                  ? "bg-amber-100/70 dark:bg-amber-900/40 border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-300"
                  : "bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 group-hover:text-primary group-hover:bg-blue-50 dark:group-hover:bg-blue-950/50 group-hover:border-blue-200 dark:group-hover:border-blue-800"
              }`}
            >
              <Icon className="size-4" />
            </div>
          ) : null}
          <div className="size-6 flex items-center justify-center text-slate-400 dark:text-slate-500 group-hover:text-primary group-hover:translate-x-0.5 transition-all">
            <ArrowRight className="size-3.5" />
          </div>
        </div>
      </div>

      {/* Value Display */}
      <div className="mt-4 flex items-baseline justify-between">
        <p className="font-mono text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100 sm:text-3xl tabular-nums">
          {value}
        </p>

        {accentColor ? (
          <span className="flex items-center gap-1.5 text-[11px] font-medium text-slate-500 dark:text-slate-400">
            <span className={`size-2 rounded-full ${accentColor}`} />
            Tracked
          </span>
        ) : null}
      </div>
    </Link>
  );
}

function WorkflowCard({
  item,
}: {
  item: WorkflowItem;
}) {
  const Icon = item.icon || Layers;

  return (
    <Link
      to={item.to}
      className="group flex min-h-[44px] items-center justify-between gap-3.5 rounded-xl card-surface p-4 transition-all duration-150 hover:border-slate-300 dark:hover:border-slate-700 hover:shadow-xs hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
    >
      <div className="flex items-center gap-3.5 min-w-0 flex-1">
        <div className="size-10 rounded-lg bg-blue-50 dark:bg-blue-950/60 border border-blue-200/80 dark:border-blue-900/60 flex items-center justify-center text-primary dark:text-blue-400 group-hover:bg-primary group-hover:text-white transition-colors shrink-0">
          <Icon className="size-5" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-slate-900 dark:text-slate-100 group-hover:text-primary transition-colors truncate">
            {item.label}
          </p>
          {item.description ? (
            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400 truncate">{item.description}</p>
          ) : null}
        </div>
      </div>

      <div className="size-7 flex items-center justify-center text-slate-400 dark:text-slate-500 group-hover:text-primary group-hover:translate-x-0.5 transition-all shrink-0">
        <ArrowRight className="size-4" />
      </div>
    </Link>
  );
}

function ManagerDashboard({ user }: { user: User }) {
  const dashboardQuery = useManagerDashboardQuery();
  const exceptionsQuery = useManagerExceptionsQuery();

  const hasData = Boolean(dashboardQuery.data && exceptionsQuery.data);
  const isError = (dashboardQuery.isError || exceptionsQuery.isError) && !hasData;
  const isLoading = (dashboardQuery.isPending || exceptionsQuery.isPending) && !hasData;

  function handleRetry() {
    void Promise.all([
      dashboardQuery.refetch(),
      exceptionsQuery.refetch(),
    ]);
  }

  if (isError) {
    return (
      <div className="space-y-6">
        <DashboardHeader user={user} isManager />
        <ErrorState
          message="The operational overview could not be loaded."
          onRetry={handleRetry}
        />
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <DashboardHeader user={user} isManager />
        <LoadingState message="Loading operational overview..." />
      </div>
    );
  }

  const dashboardData = dashboardQuery.data!;
  const exceptionsData = exceptionsQuery.data!;

  // Exception counts
  const shortPickCount = exceptionsData.short_pick_exceptions?.length ?? 0;
  const transferDiscrepancyCount = exceptionsData.transfer_discrepancies?.length ?? 0;
  const unidentifiedReturnCount = exceptionsData.unidentified_returns?.length ?? 0;
  const totalExceptions = shortPickCount + transferDiscrepancyCount + unidentifiedReturnCount;

  // Open work counts
  const openReceipts = safeNumber(dashboardData.open_receipts_count);
  const pendingPickTasks = safeNumber(dashboardData.pending_pick_tasks_count);
  const activeTransfers = safeNumber(dashboardData.active_transfers_count);
  const uninspectedReturns = safeNumber(dashboardData.uninspected_returns_count);

  // Balances by state
  const balances = dashboardData.balances_by_state ?? {};
  const available = safeNumber(balances["AVAILABLE"]);
  const reserved = safeNumber(balances["RESERVED"]);
  const controlled =
    safeNumber(balances["DAMAGED"]) +
    safeNumber(balances["QUARANTINED"]) +
    safeNumber(balances["RETURN_INSPECTION"]);
  const inTransit = safeNumber(balances["IN_TRANSIT"]);

  const managerWorkflows: WorkflowItem[] = filterAllowedWorkflows(user, [
    { label: "Inventory", to: "/inventory", description: "Balances and state control", icon: Boxes },
    { label: "Receipts", to: "/receipts", description: "Inbound dock receiving", icon: PackageCheck },
    { label: "Orders", to: "/orders", description: "Outbound customer demand", icon: ShoppingCart },
    { label: "Pick tasks", to: "/pick-tasks", description: "Warehouse picking work", icon: ClipboardList },
    { label: "Transfers", to: "/transfers", description: "Inter-facility stock moves", icon: Repeat },
    { label: "Returns", to: "/returns", description: "Customer return inspections", icon: Undo2 },
  ]);

  return (
    <div className="space-y-7">
      <DashboardHeader user={user} isManager />

      {/* 1. Needs attention (Must appear before general metrics) */}
      <section aria-labelledby="needs-attention-heading" className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 id="needs-attention-heading" className="text-base font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center gap-2">
              <span className="size-2 rounded-full bg-amber-500" />
              Needs attention
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Exception queues reported by the WMS.
            </p>
          </div>
          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-md bg-amber-100 dark:bg-amber-950/60 text-amber-900 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
            {totalExceptions} Active
          </span>
        </div>

        <div className="grid gap-3.5 sm:grid-cols-3">
          <MetricCard
            label="Short-pick exceptions"
            value={shortPickCount}
            to="/pick-tasks"
            isException
            icon={AlertTriangle}
          />
          <MetricCard
            label="Transfer discrepancies"
            value={transferDiscrepancyCount}
            to="/transfers"
            isException
            icon={Repeat}
          />
          <MetricCard
            label="Unidentified returns"
            value={unidentifiedReturnCount}
            to="/returns"
            isException
            icon={Undo2}
          />
        </div>

        {totalExceptions === 0 ? (
          <div className="card-surface rounded-xl p-5 text-center text-sm font-medium text-slate-500 dark:text-slate-400 flex items-center justify-center gap-2">
            <CheckCircle2 className="size-4 text-emerald-600" />
            No active manager exceptions were reported.
          </div>
        ) : null}
      </section>

      {/* 2. Open work */}
      <section aria-labelledby="open-work-heading" className="space-y-3">
        <div>
          <h2 id="open-work-heading" className="text-base font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Open work
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Active warehouse operations requiring processing.
          </p>
        </div>
        <div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            label="Open receipts"
            value={openReceipts}
            to="/receipts"
            icon={PackagePlus}
          />
          <MetricCard
            label="Pending pick tasks"
            value={pendingPickTasks}
            to="/pick-tasks"
            icon={ClipboardList}
          />
          <MetricCard
            label="Active transfers"
            value={activeTransfers}
            to="/transfers"
            icon={Repeat}
          />
          <MetricCard
            label="Returns awaiting inspection"
            value={uninspectedReturns}
            to="/returns"
            icon={Undo2}
          />
        </div>
      </section>

      {/* 3. Inventory by state */}
      <section aria-labelledby="inventory-state-heading" className="space-y-3">
        <div>
          <h2 id="inventory-state-heading" className="text-base font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Inventory by state
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Total units reported across all warehouses by inventory state.
          </p>
        </div>
        <div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            label="Available"
            value={available.toLocaleString()}
            to="/inventory"
            icon={Boxes}
            accentColor="bg-emerald-500"
          />
          <MetricCard
            label="Reserved"
            value={reserved.toLocaleString()}
            to="/inventory"
            icon={ShoppingCart}
            accentColor="bg-blue-500"
          />
          <MetricCard
            label="Controlled"
            value={controlled.toLocaleString()}
            to="/inventory"
            icon={AlertTriangle}
            accentColor="bg-amber-500"
          />
          <MetricCard
            label="In transit"
            value={inTransit.toLocaleString()}
            to="/inventory"
            icon={Truck}
            accentColor="bg-purple-500"
          />
        </div>
      </section>

      {/* 4. Available workflows */}
      <section aria-labelledby="available-workflows-heading" className="space-y-3 pt-1">
        <div>
          <h2 id="available-workflows-heading" className="text-base font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Available workflows
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Direct operational access to fulfillment areas.
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {managerWorkflows.map((item) => (
            <WorkflowCard key={item.to} item={item} />
          ))}
        </div>
      </section>
    </div>
  );
}

function RoleWorkspaceDashboard({ user }: { user: User }) {
  let defaultWorkflows: WorkflowItem[] = [];

  switch (user.role) {
    case "RECEIVER":
      defaultWorkflows = [
        { label: "Receive inventory", to: "/receipts", description: "Process inbound purchase orders and dock receipts", icon: PackageCheck },
        { label: "Review inventory", to: "/inventory", description: "View warehouse balances and location states", icon: Boxes },
        { label: "Process returns", to: "/returns", description: "Inspect and disposition customer returns", icon: Undo2 },
      ];
      break;
    case "PICKER_PACKER":
      defaultWorkflows = [
        { label: "Review orders", to: "/orders", description: "Monitor active order fulfillment statuses", icon: ShoppingCart },
        { label: "Open pick tasks", to: "/pick-tasks", description: "Claim and execute item picking assignments", icon: ClipboardList },
        { label: "Manage shipments", to: "/shipments", description: "Stage and verify outbound package shipments", icon: Truck },
      ];
      break;
    case "SELLER":
      defaultWorkflows = [
        { label: "Review inventory", to: "/inventory", description: "Track your catalog quantities and states", icon: Boxes },
        { label: "Review orders", to: "/orders", description: "View order fulfillment progression", icon: ShoppingCart },
        { label: "Track shipments", to: "/shipments", description: "Monitor dispatched outbound carrier tracking", icon: Truck },
        { label: "Review returns", to: "/returns", description: "Inspect customer return request statuses", icon: Undo2 },
      ];
      break;
    default:
      defaultWorkflows = [];
  }

  const allowedWorkflows = filterAllowedWorkflows(user, defaultWorkflows);

  return (
    <div className="space-y-7">
      <DashboardHeader user={user} isManager={false} />

      <section aria-labelledby="role-workflows-heading" className="space-y-3">
        <div>
          <h2 id="role-workflows-heading" className="text-base font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Available workflows
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Workflows authorized for your account role.
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {allowedWorkflows.map((item) => (
            <WorkflowCard key={item.to} item={item} />
          ))}
        </div>
      </section>
    </div>
  );
}

export function Dashboard({ user }: { user: User }) {
  const isManager =
    user.role === "ADMINISTRATOR" ||
    user.role === "WAREHOUSE_MANAGER";

  return isManager ? (
    <ManagerDashboard user={user} />
  ) : (
    <RoleWorkspaceDashboard user={user} />
  );
}
