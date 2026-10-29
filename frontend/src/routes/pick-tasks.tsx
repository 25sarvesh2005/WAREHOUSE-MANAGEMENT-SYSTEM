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
      initial[line.id] = String(line.requested_quantity);
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
      <div className={`grid gap-6 ${active ? "xl:grid-cols-[1.5fr_1fr] 2xl:grid-cols-[1.7fr_1.1fr]" : "grid-cols-1"} min-w-0`}>
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
                      <Th className="w-36">Pick Task ID</Th>
                      <Th>Order Reference</Th>
                      <Th className="w-24">Lines</Th>
                      <Th>Facility</Th>
                      <Th className="w-20">Priority</Th>
                      <Th>Status</Th>
                      <Th className="text-right w-28">Action</Th>
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
                              ? "bg-blue-50/70 dark:bg-blue-950/40 font-medium"
                              : "hover:bg-slate-50 dark:hover:bg-slate-800/40"
                          }`}
                        >
                          <Td className="font-mono font-semibold text-slate-900 dark:text-slate-100">
                            TASK-{task.id.slice(0, 8)}
                          </Td>
                          <Td className="font-medium text-slate-800 dark:text-slate-200">
                            {orderRef}
                          </Td>
                          <Td className="font-medium text-slate-700 dark:text-slate-300">
                            {task.lines?.length || 0} {task.lines?.length === 1 ? "SKU" : "SKUs"}
                          </Td>
                          <Td>
                            <FacilityBadge code={whCode} />
                          </Td>
                          <Td>
                            <span className="inline-flex items-center rounded-md bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-xs font-semibold text-slate-700 dark:text-slate-300">
                              P{task.priority ?? 1}
                            </span>
                          </Td>
                          <Td>
                            <StatusBadge value={task.status} />
                          </Td>
                          <Td className="text-right">
                            <Button
                              variant={isSelected ? "primary" : "secondary"}
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                selectTask(task);
                              }}
                            >
                              Pick Lines
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
            <Card className="sticky top-20 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-xs space-y-4">
              <div className="flex items-start justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
                <div className="flex items-center gap-2.5">
                  <span className="flex size-8 items-center justify-center rounded-lg bg-blue-50 dark:bg-blue-950/60 text-primary dark:text-blue-400 border border-blue-200/80 dark:border-blue-900/60">
                    <Package className="size-4" aria-hidden="true" />
                  </span>
                  <div>
                    <span className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                      Active Floor Pick Station
                    </span>
                    <h3 className="font-mono text-sm font-bold text-slate-900 dark:text-slate-100 mt-0.5">
                      TASK-{active.id.slice(0, 8)}
                    </h3>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <StatusBadge value={active.status} />
                  <button
                    type="button"
                    onClick={() => setActive(null)}
                    aria-label="Close pick station"
                    className="flex size-7 items-center justify-center rounded-md text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                  >
                    <X className="size-4" aria-hidden="true" />
                  </button>
                </div>
              </div>

              {completeError ? <ErrorState message={completeError} /> : null}

              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-semibold text-slate-600 dark:text-slate-300">
                    Pick Verification Items
                  </span>
                  <span className="text-[11px] text-slate-400">
                    {active.lines?.length || 0} line(s)
                  </span>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400 mb-3">
                  Verify SKU barcode and enter physical picked quantity from bin:
                </p>

                <div className="space-y-3">
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
                        className={`rounded-lg border p-3.5 text-xs transition-colors ${
                          isShort
                            ? "border-rose-300 dark:border-rose-900/70 bg-rose-50/50 dark:bg-rose-950/20"
                            : "border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/60"
                        }`}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <span className="inline-block font-mono font-bold text-slate-900 dark:text-slate-100 bg-white dark:bg-slate-800 px-2 py-0.5 rounded border border-slate-200 dark:border-slate-700 text-xs">
                              {sku}
                            </span>
                            <p className="text-xs text-slate-600 dark:text-slate-400 mt-1 truncate">
                              {name}
                            </p>
                          </div>
                          <span className="shrink-0 font-medium text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-800 px-2 py-1 rounded-md border border-slate-200 dark:border-slate-700 text-[11px]">
                            Req: <strong className="font-semibold text-slate-900 dark:text-slate-100 font-mono">{requested}</strong>
                          </span>
                        </div>

                        <div className="mt-3 flex items-center justify-between border-t border-slate-200/70 dark:border-slate-800 pt-2.5">
                          <label className="text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                            Actual Picked Units:
                          </label>

                          <div className="flex items-center gap-1.5">
                            <button
                              type="button"
                              onClick={handleDecrement}
                              disabled={currentPicked <= 0}
                              aria-label={`Decrease picked quantity for ${sku}`}
                              className="flex size-7 items-center justify-center rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-40 cursor-pointer"
                            >
                              <Minus className="size-3" />
                            </button>

                            <input
                              type="number"
                              min="0"
                              max={requested}
                              value={picked[line.id] ?? requested}
                              onChange={(e) => setPicked({ ...picked, [line.id]: e.target.value })}
                              aria-label={`Picked quantity for ${sku}`}
                              className="w-16 rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-2 py-1 font-mono text-xs font-bold text-center text-slate-900 dark:text-slate-100 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary/20"
                            />

                            <button
                              type="button"
                              onClick={handleIncrement}
                              disabled={currentPicked >= requested}
                              aria-label={`Increase picked quantity for ${sku}`}
                              className="flex size-7 items-center justify-center rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 disabled:opacity-40 cursor-pointer"
                            >
                              <Plus className="size-3" />
                            </button>
                          </div>
                        </div>

                        {isShort ? (
                          <p className="mt-2 text-[11px] font-semibold text-rose-700 dark:text-rose-400 flex items-center gap-1.5 bg-rose-100/60 dark:bg-rose-950/40 px-2 py-1 rounded">
                            <AlertTriangle className="size-3.5 shrink-0" />
                            Short pick: {requested - currentPicked} missing from bin
                          </p>
                        ) : null}
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
                  className="w-full font-bold gap-2"
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
