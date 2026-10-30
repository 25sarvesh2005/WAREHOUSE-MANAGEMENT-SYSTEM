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
    <header className="border-b border-border pb-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-2">
          <h1 className="text-[1.85rem] font-semibold tracking-tight text-slate-950 dark:text-slate-50 sm:text-3xl">
            {isManager ? "Operations" : `Welcome, ${firstName}`}
          </h1>

          <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
            <span>Signed in as {formattedRole}</span>
          </div>

          <p className="max-w-2xl text-sm leading-6 text-slate-600 dark:text-slate-400">
            {isManager
              ? "Current exceptions, work in progress, and inventory across your warehouses."
              : "Choose a workflow to continue."}
          </p>
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
}: {
  icon?: ElementType;
  isException?: boolean;
  label: string;
  to: string;
  value: number | string;
}) {
  const needsAttention = isException && safeNumber(value) > 0;
  return (
    <Link
      to={to}
      className={`group flex min-h-36 flex-col justify-between rounded-lg border p-4 transition-[border-color,box-shadow,background-color] duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
        needsAttention
          ? "border-amber-300 bg-amber-50/70 hover:border-amber-400 dark:border-amber-900/70 dark:bg-amber-950/25"
          : "card-surface hover:border-slate-300 dark:hover:border-slate-600"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <p className={`text-[13px] font-medium ${needsAttention ? "text-amber-900 dark:text-amber-200" : "text-slate-600 dark:text-slate-400"}`}>
          {label}
        </p>
        {Icon ? <Icon className={`size-[18px] shrink-0 ${needsAttention ? "text-amber-700 dark:text-amber-300" : "text-slate-400 dark:text-slate-500"}`} aria-hidden="true" /> : null}
      </div>

      <div className="mt-4 flex items-end justify-between gap-3">
        <p className={`font-mono text-[2rem] font-semibold leading-none tracking-tight tabular-nums ${needsAttention ? "text-amber-950 dark:text-amber-100" : "text-slate-950 dark:text-slate-50"}`}>
          {value}
        </p>
        <span className="flex items-center gap-1 text-xs font-medium text-slate-500 transition-colors group-hover:text-primary dark:text-slate-400">
          {needsAttention ? "Review" : "View"}
          <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
        </span>
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
      className="group flex min-h-[44px] items-center justify-between gap-3.5 rounded-lg card-surface p-4 transition-[border-color,box-shadow] duration-150 hover:border-slate-300 dark:hover:border-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
    >
      <div className="flex items-center gap-3.5 min-w-0 flex-1">
        <div className="size-9 rounded-md bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-600 dark:text-slate-300 shrink-0">
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

        <div className="size-7 flex items-center justify-center text-slate-400 dark:text-slate-500 group-hover:text-primary transition-colors shrink-0">
          <ArrowRight className="size-4" aria-hidden="true" />
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
            <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
              Work that needs review right now.
            </p>
          </div>
          <span className={`text-xs font-medium px-2.5 py-1 rounded-md border ${totalExceptions > 0 ? "bg-amber-50 dark:bg-amber-950/30 text-amber-800 dark:text-amber-300 border-amber-200 dark:border-amber-900/70" : "bg-slate-50 dark:bg-slate-900 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-800"}`}>
            {totalExceptions} {totalExceptions === 1 ? "active exception" : "active exceptions"}
          </span>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
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
          <div className="card-surface rounded-lg p-4 text-sm text-slate-600 dark:text-slate-400 flex items-center gap-2">
            <CheckCircle2 className="size-4 text-emerald-600" />
            No open exceptions.
          </div>
        ) : null}
      </section>

      {/* 2. Open work */}
      <section aria-labelledby="open-work-heading" className="space-y-3">
        <div>
          <h2 id="open-work-heading" className="text-base font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Open work
          </h2>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Work currently in progress.
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
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
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Units across all warehouses, grouped by state.
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            label="Available"
            value={available.toLocaleString()}
            to="/inventory"
            icon={Boxes}
          />
          <MetricCard
            label="Reserved"
            value={reserved.toLocaleString()}
            to="/inventory"
            icon={ShoppingCart}
          />
          <MetricCard
            label="Controlled"
            value={controlled.toLocaleString()}
            to="/inventory"
            icon={AlertTriangle}
          />
          <MetricCard
            label="In transit"
            value={inTransit.toLocaleString()}
            to="/inventory"
            icon={Truck}
          />
        </div>
      </section>

      {/* 4. Available workflows */}
      <section aria-labelledby="available-workflows-heading" className="space-y-3 pt-1">
        <div>
          <h2 id="available-workflows-heading" className="text-base font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Available workflows
          </h2>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Go directly to a warehouse workflow.
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
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
            Start with the work assigned to your team.
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
