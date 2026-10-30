import { createFileRoute } from "@tanstack/react-router";
import {
  AlertTriangle,
  CheckCircle2,
  Minus,
  Plus,
  X,
  Package,
} from "lucide-react";
import { useRef, useState } from "react";
import { AppDialog } from "@/components/AppDialog";
import { AppShell } from "@/components/AppShell";
import { FacilityBadge, StatusBadge } from "@/components/StatusBadge";
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  ExceptionBanner,
  LoadingState,
  MobileRecordCard,
  MobileRecordList,
  PageHeader,
  TableShell,
  Td,
  Th,
} from "@/components/ui-kit";
import { productName, productSku } from "@/lib/display";
import {
  useCompletePickTaskMutation,
  useCreatePickTaskMutation,
  useOrdersQuery,
  usePickTasksQuery,
  useProductsQuery,
  useWarehousesQuery,
} from "@/hooks/use-api";
import type { PickTask } from "@/lib/types";

export const Route = createFileRoute("/pick-tasks")({
  head: () => ({
    meta: [
      { title: "Pick Tasks & Floor Packing | Whitfield Ops" },
      {
        name: "description",
        content:
          "Assigned picking tasks, per-line picked quantities, and short-pick exception handling for floor workers.",
      },
      { property: "og:title", content: "Pick Tasks & Floor Packing | Whitfield Ops" },
      {
        property: "og:description",
        content: "Warehouse floor picking queue with shortage exception controls.",
      },
    ],
  }),
  component: PickTasksPage,
});

function PickTasksPage() {
  const tasksQuery = usePickTasksQuery();
  const ordersQuery = useOrdersQuery();
  const productsQuery = useProductsQuery();
  const warehousesQuery = useWarehousesQuery();
  const createPickTaskMutation = useCreatePickTaskMutation();
  const completePickTaskMutation = useCompletePickTaskMutation();

  const tasks = tasksQuery.data ?? [];
  const orders = ordersQuery.data ?? [];
  const products = productsQuery.data ?? [];
  const warehouses = warehousesQuery.data ?? [];

  const [active, setActive] = useState<PickTask | null>(null);
  const generatePickTaskTriggerRef = useRef<HTMLButtonElement | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newTask, setNewTask] = useState({
    order_id: "",
    priority: "1",
  });
  const [picked, setPicked] = useState<Record<string, string>>({});
  const [completeError, setCompleteError] = useState<string | null>(null);

  const shorts = tasks.filter((t: PickTask) => t.status === "SHORT_PICK_EXCEPTION").length;
  const eligibleOrders = orders.filter((order) =>
    ["RESERVED", "PARTIALLY_RESERVED"].includes(order.status),
  );

  async function createTask() {
    if (!newTask.order_id) return;
    await createPickTaskMutation.mutateAsync({
      order_id: newTask.order_id,
      priority: Number(newTask.priority || 1),
    });
    setShowCreate(false);
    setNewTask({ order_id: "", priority: "1" });
    tasksQuery.refetch();
  }

  async function complete() {
    if (!active) return;
    setCompleteError(null);
    try {
      await completePickTaskMutation.mutateAsync({
        id: active.id,
        lines: active.lines.map((line) => {
          const requested = Number(line.requested_quantity || 0);
          const pickedQuantity = Number(picked[line.id] ?? requested);
          return {
            pick_task_line_id: line.id,
            picked_quantity: pickedQuantity,
            short_quantity: Math.max(requested - pickedQuantity, 0),
          };
        }),
      });
      setActive(null);
      setPicked({});
      tasksQuery.refetch();
    } catch (err: unknown) {
      setCompleteError(err instanceof Error ? err.message : "Could not complete pick task.");
    }
  }

  function selectTask(task: PickTask) {
    setActive(task);
    const initial: Record<string, string> = {};
    task.lines?.forEach((line) => {
      const requested = Number(line.requested_quantity || 0);
      initial[line.id] = Number.isInteger(requested) ? String(requested) : String(requested);
    });
    setPicked(initial);
  }

  return (
    <AppShell>
      <PageHeader
        title="Floor Picking & Packing Tasks"
        subtitle="Execute warehouse pick waves with bin verification and real-time short-pick exception handling."
        actions={
          <Button
            onClick={(event) => {
              generatePickTaskTriggerRef.current = event.currentTarget;
              setShowCreate(true);
            }}
            className="gap-2"
          >
            <Plus className="size-4" /> Generate Pick Task
          </Button>
        }
      />

      {shorts > 0 ? (
        <ExceptionBanner>
          <strong>{shorts} Short-Pick Exception(s) Active:</strong> Floor stock was fewer than
          requested. Review physical bin counts or trigger stock re-allocation.
        </ExceptionBanner>
      ) : null}

      {[tasksQuery, ordersQuery, productsQuery, warehousesQuery].some((q) => q.isLoading) ? (
        <LoadingState message="Loading pick queue..." />
      ) : null}

      {/* Main Grid: Pick Tasks Table & Active Picking Drawer */}
      <div className={`grid gap-6 ${active ? "xl:grid-cols-[1fr_360px] 2xl:grid-cols-[1fr_390px]" : "grid-cols-1"} min-w-0`}>
        <div className="min-w-0">
          {tasks.length === 0 ? (
            <Card className="p-8">
              <EmptyState
                message="No pick tasks currently in queue"
                hint="Generate pick tasks for reserved customer orders to start warehouse picking waves."
              />
            </Card>
          ) : (
            <>
              <div data-testid="pick-tasks-desktop-table" className="hidden md:block">
                <TableShell>
                  <thead>
                    <tr>
                      <Th className="whitespace-nowrap px-2.5 py-2 text-xs">Pick Task ID</Th>
                      <Th className="whitespace-nowrap px-2 py-2 text-xs">Order Reference</Th>
                      <Th className="whitespace-nowrap px-2 py-2 text-xs">Lines</Th>
                      <Th className="whitespace-nowrap px-2 py-2 text-xs">Facility</Th>
                      <Th className="whitespace-nowrap px-2 py-2 text-xs">Priority</Th>
                      <Th className="whitespace-nowrap px-2 py-2 text-xs">Status</Th>
                      <Th className="whitespace-nowrap px-2 py-2 text-xs text-right">Action</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {tasks.map((task: PickTask) => {
                      const isSelected = active?.id === task.id;
                      const orderRef =
                        orders.find((o) => o.id === task.order_id)?.seller_order_number ||
                        `ORD-${task.order_id?.slice(0, 6)}`;
                      const whCode = warehouses.find((w) => w.id === task.warehouse_id)?.code || "WH";

                      return (
                        <tr
                          key={task.id}
                          onClick={() => selectTask(task)}
                          className={`cursor-pointer transition-colors ${
                            isSelected
                              ? "bg-blue-50/80 dark:bg-blue-950/50 font-medium"
                              : "hover:bg-slate-50 dark:hover:bg-slate-800/40"
                          }`}
                        >
                          <Td className="whitespace-nowrap px-2.5 py-2 font-mono font-semibold text-xs text-slate-900 dark:text-slate-100">
                            TASK-{task.id.slice(0, 8)}
                          </Td>
                          <Td className="whitespace-nowrap px-2 py-2 text-xs font-medium text-slate-800 dark:text-slate-200">
                            {orderRef}
                          </Td>
                          <Td className="whitespace-nowrap px-2 py-2 text-xs font-medium text-slate-700 dark:text-slate-300">
                            {task.lines?.length || 0} {task.lines?.length === 1 ? "SKU" : "SKUs"}
                          </Td>
                          <Td className="whitespace-nowrap px-2 py-2 text-xs">
                            <FacilityBadge code={whCode} compact />
                          </Td>
                          <Td className="whitespace-nowrap px-2 py-2 text-xs">
                            <span className="inline-flex items-center rounded-md bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                              P{task.priority ?? 1}
                            </span>
                          </Td>
                          <Td className="whitespace-nowrap px-2 py-2 text-xs">
                            <StatusBadge value={task.status} />
                          </Td>
                          <Td className="whitespace-nowrap px-2 py-2 text-xs text-right">
                            <Button
                              variant={isSelected ? "primary" : "secondary"}
                              size="sm"
                              className="h-7 px-2.5 py-0.5 text-xs"
                              onClick={(e) => {
                                e.stopPropagation();
                                selectTask(task);
                              }}
                            >
                              {isSelected ? "Selected" : "Pick Lines"}
                            </Button>
                          </Td>
                        </tr>
                      );
                    })}
                  </tbody>
                </TableShell>
              </div>

              <MobileRecordList label="Floor Picking Tasks" testId="pick-tasks-mobile-list">
                {tasks.map((task: PickTask) => {
                  const isSelected = active?.id === task.id;
                  const orderRef =
                    orders.find((o) => o.id === task.order_id)?.seller_order_number ||
                    `ORD-${task.order_id?.slice(0, 6)}`;
                  const whCode = warehouses.find((w) => w.id === task.warehouse_id)?.code || "WH";

                  return (
                    <MobileRecordCard key={task.id} selected={isSelected}>
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="font-mono font-bold text-slate-900 dark:text-slate-100 break-all text-sm">
                            TASK-{task.id.slice(0, 8)}
                          </p>
                        </div>
                        <StatusBadge value={task.status} />
                      </div>

                      <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <dt className="text-muted-foreground text-[11px]">Order Reference</dt>
                          <dd className="text-slate-800 dark:text-slate-200 font-medium break-all">{orderRef}</dd>
                        </div>
                        <div>
                          <dt className="text-muted-foreground text-[11px]">Facility</dt>
                          <dd className="mt-0.5">
                            <FacilityBadge code={whCode} />
                          </dd>
                        </div>
                        <div>
                          <dt className="text-muted-foreground text-[11px]">Lines</dt>
                          <dd className="font-medium text-slate-800 dark:text-slate-200">{task.lines?.length || 0} SKUs</dd>
                        </div>
                        <div>
                          <dt className="text-muted-foreground text-[11px]">Priority</dt>
                          <dd className="font-bold text-slate-800 dark:text-slate-200">P{task.priority ?? 1}</dd>
                        </div>
                      </dl>

                      <div className="mt-4 pt-3 border-t border-border">
                        <Button
                          variant={isSelected ? "primary" : "secondary"}
                          size="sm"
                          className="min-h-[44px] w-full"
                          onClick={() => selectTask(task)}
                        >
                          Pick lines
                        </Button>
                      </div>
                    </MobileRecordCard>
                  );
                })}
              </MobileRecordList>
            </>
          )}
        </div>

        {/* Right Column: Pick Station Controls */}
        {active ? (
          <div className="min-w-0">
            <Card className="sticky top-20 border border-slate-200/90 dark:border-slate-800/90 bg-white dark:bg-slate-900 p-5 shadow-[0_4px_20px_-4px_rgba(15,23,42,0.08),inset_0_1px_0_rgba(255,255,255,0.8)] dark:shadow-[0_4px_20px_-4px_rgba(0,0,0,0.4),inset_0_1px_0_rgba(255,255,255,0.05)] rounded-2xl space-y-4">
              <div className="border-b border-slate-100 dark:border-slate-800 pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="flex size-7 items-center justify-center rounded-lg bg-blue-50 dark:bg-blue-950/60 text-primary dark:text-blue-400 border border-blue-200/80 dark:border-blue-900/60 shadow-xs">
                      <Package className="size-3.5" aria-hidden="true" />
                    </span>
                    <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                      Active Floor Pick Station
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setActive(null)}
                    aria-label="Close pick station"
                    className="flex size-7 items-center justify-center rounded-md text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                  >
                    <X className="size-4" aria-hidden="true" />
                  </button>
                </div>
                <div className="mt-2.5 flex items-center justify-between gap-2">
                  <h3 className="font-mono text-sm font-bold text-slate-900 dark:text-slate-100">
                    TASK-{active.id.slice(0, 8)}
                  </h3>
                  <StatusBadge value={active.status} />
                </div>
              </div>

              {completeError ? <ErrorState message={completeError} /> : null}

              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-bold text-slate-700 dark:text-slate-300">
                    Pick Verification Items
                  </span>
                  <span className="text-[11px] font-mono text-slate-400">
                    {active.lines?.length || 0} line(s)
                  </span>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400 mb-3">
                  Verify SKU barcode and enter physical picked quantity from bin:
                </p>

                <div className="space-y-3.5">
                  {active.lines?.map((line) => {
                    const sku = productSku(products, line.product_id);
                    const name = productName(products, line.product_id);
                    const requested = Number(line.requested_quantity || 0);
                    const currentPicked = Number(picked[line.id] ?? requested);
                    const isShort = currentPicked < requested;

                    const handleIncrement = () => {
                      const next = Math.min(requested, currentPicked + 1);
                      setPicked({ ...picked, [line.id]: String(next) });
                    };

                    const handleDecrement = () => {
                      const next = Math.max(0, currentPicked - 1);
                      setPicked({ ...picked, [line.id]: String(next) });
                    };

                    return (
                      <div
                        key={line.id}
                        className={`rounded-xl border p-4 text-xs transition-colors shadow-xs ${
                          isShort
                            ? "border-amber-300 dark:border-amber-900/70 bg-amber-50/40 dark:bg-amber-950/20"
                            : "border-slate-200/90 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-900/60"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <span className="inline-block font-mono font-bold text-slate-900 dark:text-slate-100 bg-white dark:bg-slate-800 px-2.5 py-1 rounded-md border border-slate-200 dark:border-slate-700 text-xs shadow-xs">
                              {sku}
                            </span>
                            <p className="text-xs font-medium text-slate-700 dark:text-slate-300 mt-1 truncate">
                              {name}
                            </p>
                          </div>
                          <span className="shrink-0 font-medium text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-800 px-2.5 py-1 rounded-md border border-slate-200 dark:border-slate-700 text-xs shadow-xs">
                            Req: <strong className="font-bold text-slate-900 dark:text-slate-100 font-mono">{requested}</strong> units
                          </span>
                        </div>

                        <div className="mt-3 flex items-center justify-between border-t border-slate-200/70 dark:border-slate-800/80 pt-3">
                          <label className="text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                            Actual Picked Units:
                          </label>

                          <div className="flex items-center gap-1.5">
                            <button
                              type="button"
                              onClick={handleDecrement}
                              disabled={currentPicked <= 0}
                              aria-label={`Decrease picked quantity for ${sku}`}
                              className="flex size-8 items-center justify-center rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 active:scale-95 disabled:opacity-40 cursor-pointer shadow-xs transition-all"
                            >
                              <Minus className="size-3.5" />
                            </button>

                            <input
                              type="number"
                              min="0"
                              max={requested}
                              value={picked[line.id] ?? requested}
                              onChange={(e) => setPicked({ ...picked, [line.id]: e.target.value })}
                              aria-label={`Picked quantity for ${sku}`}
                              className="w-20 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 py-1 font-mono text-sm font-bold text-center text-slate-900 dark:text-slate-100 focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/20 shadow-inner"
                            />

                            <button
                              type="button"
                              onClick={handleIncrement}
                              disabled={currentPicked >= requested}
                              aria-label={`Increase picked quantity for ${sku}`}
                              className="flex size-8 items-center justify-center rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 active:scale-95 disabled:opacity-40 cursor-pointer shadow-xs transition-all"
                            >
                              <Plus className="size-3.5" />
                            </button>
                          </div>
                        </div>

                        {/* Quick Action Buttons for floor speed */}
                        <div className="mt-2.5 flex items-center justify-between gap-2 pt-2 border-t border-slate-200/50 dark:border-slate-800/60">
                          <span className="text-[10px] uppercase font-bold text-slate-400">Quick Fill:</span>
                          <div className="flex items-center gap-1.5">
                            <button
                              type="button"
                              onClick={() => setPicked({ ...picked, [line.id]: String(requested) })}
                              className="text-[11px] font-semibold text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-950/50 px-2 py-0.5 rounded border border-blue-200/70 dark:border-blue-900/60 transition-colors cursor-pointer"
                            >
                              Full ({requested})
                            </button>
                            <button
                              type="button"
                              onClick={() => setPicked({ ...picked, [line.id]: "0" })}
                              className="text-[11px] font-semibold text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/50 px-2 py-0.5 rounded border border-rose-200/70 dark:border-rose-900/60 transition-colors cursor-pointer"
                            >
                              Zero (0)
                            </button>
                          </div>
                        </div>

                        {isShort ? (
                          <div className="mt-2.5 rounded-lg bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900/70 px-2.5 py-1.5 text-[11px] font-medium text-amber-900 dark:text-amber-200 flex items-center gap-2">
                            <AlertTriangle className="size-3.5 text-amber-600 shrink-0" />
                            <span>
                              Short pick: <strong>{requested - currentPicked} unit(s)</strong> short. Will trigger exception handling on confirm.
                            </span>
                          </div>
                        ) : (
                          <div className="mt-2.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200/60 dark:border-emerald-900/50 px-2.5 py-1 text-[11px] font-medium text-emerald-800 dark:text-emerald-300 flex items-center gap-1.5">
                            <CheckCircle2 className="size-3.5 text-emerald-600 shrink-0" />
                            <span>All {requested} unit(s) verified from bin</span>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="border-t border-slate-100 dark:border-slate-800 pt-3">
                <Button
                  variant="primary"
                  size="md"
                  onClick={complete}
                  disabled={completePickTaskMutation.isPending}
                  className="w-full font-bold gap-2 py-2.5 rounded-xl shadow-[inset_0_1px_0_rgba(255,255,255,0.25),0_2px_8px_rgba(37,99,235,0.25)] hover:shadow-[0_4px_12px_rgba(37,99,235,0.35)]"
                >
                  <CheckCircle2 className="size-4" />
                  <span>
                    {completePickTaskMutation.isPending
                      ? "Confirming Pick..."
                      : "Confirm Pick & Pack Complete"}
                  </span>
                </Button>
              </div>
            </Card>
          </div>
        ) : null}
      </div>

      {/* Generate Pick Task Modal */}
      <AppDialog
        open={showCreate}
        onOpenChange={setShowCreate}
        title="Generate Pick Task"
        description="Select an eligible reserved order and assign its picking priority."
        className="max-w-md"
        pending={createPickTaskMutation.isPending}
        returnFocusRef={generatePickTaskTriggerRef}
      >
        <div className="space-y-3.5 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-300 text-xs mb-1">
              Select Reserved Order
            </label>
            <select
              value={newTask.order_id}
              onChange={(e) => setNewTask({ ...newTask, order_id: e.target.value })}
              className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-xs font-semibold text-slate-800 dark:text-slate-200 focus:border-primary focus:outline-none"
            >
              <option value="">-- Choose Order to Pick --</option>
              {eligibleOrders.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.seller_order_number || `ORD-${o.id.slice(0, 8)}`} ({o.status})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-300 text-xs mb-1">
              Wave Priority Level (1-5)
            </label>
            <input
              type="number"
              min="1"
              max="5"
              value={newTask.priority}
              onChange={(e) => setNewTask({ ...newTask, priority: e.target.value })}
              className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 font-mono text-xs font-bold text-slate-900 dark:text-slate-100 focus:outline-none focus:border-primary"
            />
          </div>
        </div>

        <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:items-center sm:justify-end border-t border-slate-100 dark:border-slate-800 pt-4">
          <Button
            type="button"
            variant="secondary"
            size="md"
            disabled={createPickTaskMutation.isPending}
            onClick={() => setShowCreate(false)}
            className="w-full sm:w-auto"
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="primary"
            size="md"
            onClick={createTask}
            disabled={createPickTaskMutation.isPending || !newTask.order_id}
            className="w-full sm:w-auto"
          >
            {createPickTaskMutation.isPending ? "Generating..." : "Generate Pick Task"}
          </Button>
        </div>
      </AppDialog>
    </AppShell>
  );
}
