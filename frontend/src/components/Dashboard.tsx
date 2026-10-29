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
    <header className="neu-card rounded-3xl p-6 sm:p-8 transition-all relative overflow-hidden">
      {/* Subtle ambient highlight line */}
      <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-white/80 to-transparent" />

      <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2.5">
            <span className="neu-pill-inset inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider text-primary">
              <span className="size-1.5 rounded-full bg-primary animate-pulse" />
              Operations overview
            </span>
            
          </div>

          <h1 className="text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl lg:text-4xl">
            Welcome back, {firstName}.
          </h1>

          <div className="flex items-center gap-2">
            <span className="neu-pill inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold text-muted-foreground">
              Signed in as <span className="font-bold text-foreground">{formattedRole}</span>
            </span>
          </div>

          <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground pt-1">
            {isManager
              ? "Review current inventory totals, open work, and exception queues reported by the WMS."
              : "Open the operational workflows available to your assigned role."}
          </p>
        </div>

        {/* Minimalist Tactile System Status Pill */}
        <div className="hidden lg:flex flex-col items-end gap-2 shrink-0">
          <div className="neu-inset rounded-2xl p-3.5 flex items-center gap-3">
            <div className="size-9 rounded-xl neu-flat flex items-center justify-center text-primary">
              <ShieldCheck className="size-4" />
            </div>
            <div className="text-right">
              <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground">
                Outbox & Invariant Engine
              </p>
              <p className="text-xs font-semibold text-foreground flex items-center gap-1 justify-end">
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
      className={`group relative flex min-h-[44px] flex-col justify-between rounded-2xl p-5 transition-all duration-300 hover:-translate-y-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
        isException
          ? "neu-card-exception hover:shadow-neu-exception-hover active:shadow-neu-inset"
          : "neu-card hover:shadow-neu-raised active:shadow-neu-inset"
      }`}
    >
      {/* Top Header: Label + Tactile Icon Pill */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p
            className={`text-xs font-bold uppercase tracking-wider ${
              isException ? "text-amber-900" : "text-muted-foreground"
            }`}
          >
            {label}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {Icon ? (
            <div
              className={`size-8 rounded-xl flex items-center justify-center transition-transform group-hover:scale-105 ${
                isException
                  ? "neu-inset text-amber-700"
                  : "neu-inset text-muted-foreground group-hover:text-primary"
              }`}
            >
              <Icon className="size-4" />
            </div>
          ) : null}
          <div className="size-7 rounded-lg neu-pill-inset flex items-center justify-center text-muted-foreground/70 group-hover:text-primary group-hover:translate-x-0.5 transition-all">
            <ArrowRight className="size-3.5" />
          </div>
        </div>
      </div>

      {/* Value Display in Tactile Recessed Well */}
      <div className="mt-4 flex items-baseline justify-between">
        <div className="neu-inset px-3.5 py-1.5 rounded-xl flex items-center">
          <p className="font-mono text-2xl font-extrabold tracking-tight text-foreground sm:text-3xl">
            {value}
          </p>
        </div>

        {accentColor ? (
          <span className="flex items-center gap-1.5 text-[11px] font-semibold text-muted-foreground">
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
      className="group flex min-h-[44px] items-center justify-between gap-4 rounded-2xl neu-card p-4 transition-all duration-300 hover:-translate-y-1 hover:shadow-neu-raised active:shadow-neu-inset focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
    >
      <div className="flex items-center gap-3.5 min-w-0 flex-1">
        <div className="size-11 rounded-2xl neu-inset flex items-center justify-center text-primary group-hover:scale-105 group-hover:text-primary-dark transition-all shrink-0">
          <Icon className="size-5" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-bold text-foreground group-hover:text-primary transition-colors truncate">
            {item.label}
          </p>
          {item.description ? (
            <p className="mt-0.5 text-xs text-muted-foreground truncate">{item.description}</p>
          ) : null}
        </div>
      </div>

      <div className="size-8 rounded-xl neu-pill flex items-center justify-center text-muted-foreground group-hover:text-primary group-hover:translate-x-0.5 transition-all shrink-0">
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
    <div className="space-y-8">
      <DashboardHeader user={user} isManager />

      {/* 1. Needs attention (Must appear before general metrics) */}
      <section aria-labelledby="needs-attention-heading" className="space-y-3.5">
        <div className="flex items-center justify-between">
          <div>
            <h2 id="needs-attention-heading" className="text-lg font-bold tracking-tight text-foreground flex items-center gap-2">
              <span className="size-2 rounded-full bg-amber-500 animate-pulse" />
              Needs attention
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              Exception queues reported by the WMS.
            </p>
          </div>
          <span className="neu-pill-inset text-[11px] font-bold px-2.5 py-1 rounded-full text-amber-800">
            {totalExceptions} Active
          </span>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
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
          <div className="neu-inset rounded-2xl p-6 text-center text-sm font-medium text-muted-foreground flex items-center justify-center gap-2">
            <CheckCircle2 className="size-4 text-emerald-500" />
            No active manager exceptions were reported.
          </div>
        ) : null}
      </section>

      {/* 2. Open work */}
      <section aria-labelledby="open-work-heading" className="space-y-3.5">
        <div>
          <h2 id="open-work-heading" className="text-lg font-bold tracking-tight text-foreground">
            Open work
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Active warehouse operations requiring processing.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
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
      <section aria-labelledby="inventory-state-heading" className="space-y-3.5">
        <div>
          <h2 id="inventory-state-heading" className="text-lg font-bold tracking-tight text-foreground">
            Inventory by state
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Total units reported across all warehouses by inventory state.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
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
      <section aria-labelledby="available-workflows-heading" className="space-y-3.5 pt-2">
        <div>
          <h2 id="available-workflows-heading" className="text-base font-bold tracking-tight text-foreground">
            Available workflows
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Direct operational access to fulfillment areas.
          </p>
        </div>
        <div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
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
    <div className="space-y-8">
      <DashboardHeader user={user} isManager={false} />

      <section aria-labelledby="role-workflows-heading" className="space-y-4">
        <div>
          <h2 id="role-workflows-heading" className="text-lg font-bold tracking-tight text-foreground">
            Available workflows
          </h2>
          <p className="text-xs text-muted-foreground mt-0.5">
            Workflows authorized for your account role.
          </p>
        </div>

        <div className="grid gap-3.5 sm:grid-cols-2 lg:grid-cols-3">
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
