import { Link } from "@tanstack/react-router";
import { ArrowRight } from "lucide-react";
import { ErrorState, LoadingState } from "@/components/ui-kit";
import { useManagerDashboardQuery, useManagerExceptionsQuery } from "@/hooks/use-api";
import { ROLE_SECTIONS } from "@/lib/auth";
import type { User } from "@/lib/types";

interface WorkflowItem {
  description?: string;
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
    <header className="rounded-3xl border border-border bg-white p-6 sm:p-8 shadow-card">
      <p className="text-xs font-bold uppercase tracking-wider text-primary">
        Operations overview
      </p>
      <h1 className="mt-2 text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
        Welcome back, {firstName}.
      </h1>
      <p className="mt-1 text-xs font-semibold text-muted-foreground">
        Signed in as <span className="text-foreground">{formattedRole}</span>
      </p>
      <p className="mt-3 max-w-3xl text-sm leading-relaxed text-muted-foreground">
        {isManager
          ? "Review current inventory totals, open work, and exception queues reported by the WMS."
          : "Open the operational workflows available to your assigned role."}
      </p>
    </header>
  );
}

function MetricCard({
  label,
  value,
  to,
  isException = false,
}: {
  isException?: boolean;
  label: string;
  to: string;
  value: number | string;
}) {
  return (
    <Link
      to={to}
      className={`group flex min-h-[44px] flex-col justify-between rounded-2xl border p-4 sm:p-5 transition-all hover:-translate-y-0.5 hover:shadow-panel focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary ${
        isException
          ? "border-amber-200/80 bg-amber-50/40 hover:border-amber-400"
          : "border-border bg-white hover:border-primary/30"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          {label}
        </p>
        <ArrowRight className="size-4 shrink-0 text-muted-foreground/60 transition-transform group-hover:translate-x-0.5 group-hover:text-primary" />
      </div>
      <p className="mt-3 font-mono text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
        {value}
      </p>
    </Link>
  );
}

function WorkflowCard({
  item,
}: {
  item: WorkflowItem;
}) {
  return (
    <Link
      to={item.to}
      className="group flex min-h-[44px] items-center justify-between gap-3 rounded-2xl border border-border bg-white p-4 shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-panel focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
    >
      <div className="min-w-0 flex-1">
        <p className="text-sm font-bold text-foreground group-hover:text-primary transition-colors truncate">
          {item.label}
        </p>
        {item.description ? (
          <p className="mt-0.5 text-xs text-muted-foreground truncate">{item.description}</p>
        ) : null}
      </div>
      <ArrowRight className="size-4 shrink-0 text-muted-foreground group-hover:translate-x-0.5 group-hover:text-primary transition-all" />
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
    { label: "Inventory", to: "/inventory", description: "Balances and state control" },
    { label: "Receipts", to: "/receipts", description: "Inbound dock receiving" },
    { label: "Orders", to: "/orders", description: "Outbound customer demand" },
    { label: "Pick tasks", to: "/pick-tasks", description: "Warehouse picking work" },
    { label: "Transfers", to: "/transfers", description: "Inter-facility stock moves" },
    { label: "Returns", to: "/returns", description: "Customer return inspections" },
  ]);

  return (
    <div className="space-y-8">
      <DashboardHeader user={user} isManager />

      {/* 1. Needs attention (Must appear before general metrics) */}
      <section aria-labelledby="needs-attention-heading" className="space-y-3">
        <div>
          <h2 id="needs-attention-heading" className="text-lg font-bold tracking-tight text-foreground">
            Needs attention
          </h2>
          <p className="text-xs text-muted-foreground">
            Exception queues reported by the WMS.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <MetricCard
            label="Short-pick exceptions"
            value={shortPickCount}
            to="/pick-tasks"
            isException
          />
          <MetricCard
            label="Transfer discrepancies"
            value={transferDiscrepancyCount}
            to="/transfers"
            isException
          />
          <MetricCard
            label="Unidentified returns"
            value={unidentifiedReturnCount}
            to="/returns"
            isException
          />
        </div>

        {totalExceptions === 0 ? (
          <div className="rounded-2xl border border-dashed border-border bg-white/60 p-6 text-center text-sm text-muted-foreground">
            No active manager exceptions were reported.
          </div>
        ) : null}
      </section>

      {/* 2. Open work */}
      <section aria-labelledby="open-work-heading" className="space-y-3">
        <div>
          <h2 id="open-work-heading" className="text-lg font-bold tracking-tight text-foreground">
            Open work
          </h2>
          <p className="text-xs text-muted-foreground">
            Active warehouse operations requiring processing.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            label="Open receipts"
            value={openReceipts}
            to="/receipts"
          />
          <MetricCard
            label="Pending pick tasks"
            value={pendingPickTasks}
            to="/pick-tasks"
          />
          <MetricCard
            label="Active transfers"
            value={activeTransfers}
            to="/transfers"
          />
          <MetricCard
            label="Returns awaiting inspection"
            value={uninspectedReturns}
            to="/returns"
          />
        </div>
      </section>

      {/* 3. Inventory by state */}
      <section aria-labelledby="inventory-state-heading" className="space-y-3">
        <div>
          <h2 id="inventory-state-heading" className="text-lg font-bold tracking-tight text-foreground">
            Inventory by state
          </h2>
          <p className="text-xs text-muted-foreground">
            Total units reported across all warehouses by inventory state.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <MetricCard
            label="Available"
            value={available.toLocaleString()}
            to="/inventory"
          />
          <MetricCard
            label="Reserved"
            value={reserved.toLocaleString()}
            to="/inventory"
          />
          <MetricCard
            label="Controlled"
            value={controlled.toLocaleString()}
            to="/inventory"
          />
          <MetricCard
            label="In transit"
            value={inTransit.toLocaleString()}
            to="/inventory"
          />
        </div>
      </section>

      {/* 4. Available workflows */}
      <section aria-labelledby="available-workflows-heading" className="space-y-3 pt-2">
        <div>
          <h2 id="available-workflows-heading" className="text-base font-bold tracking-tight text-foreground">
            Available workflows
          </h2>
          <p className="text-xs text-muted-foreground">
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
        { label: "Receive inventory", to: "/receipts", description: "Process inbound purchase orders and dock receipts" },
        { label: "Review inventory", to: "/inventory", description: "View warehouse balances and location states" },
        { label: "Process returns", to: "/returns", description: "Inspect and disposition customer returns" },
      ];
      break;
    case "PICKER_PACKER":
      defaultWorkflows = [
        { label: "Review orders", to: "/orders", description: "Monitor active order fulfillment statuses" },
        { label: "Open pick tasks", to: "/pick-tasks", description: "Claim and execute item picking assignments" },
        { label: "Manage shipments", to: "/shipments", description: "Stage and verify outbound package shipments" },
      ];
      break;
    case "SELLER":
      defaultWorkflows = [
        { label: "Review inventory", to: "/inventory", description: "Track your catalog quantities and states" },
        { label: "Review orders", to: "/orders", description: "View order fulfillment progression" },
        { label: "Track shipments", to: "/shipments", description: "Monitor dispatched outbound carrier tracking" },
        { label: "Review returns", to: "/returns", description: "Inspect customer return request statuses" },
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
          <p className="text-xs text-muted-foreground">
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
