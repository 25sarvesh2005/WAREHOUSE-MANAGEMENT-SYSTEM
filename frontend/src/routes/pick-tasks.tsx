import { createFileRoute } from "@tanstack/react-router";
import {
  AlertTriangle,
  Barcode,
  CheckCircle2,
  ClipboardList,
  Layers,
  Package,
  Plus,
  ShieldAlert,
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
import { productName, productSku, warehouseLabel } from "@/lib/display";
import { formatDate, formatQty } from "@/lib/format";
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
      <div className="grid gap-6 xl:grid-cols-[1.6fr_1.1fr] min-w-0">
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
                      <Th>Pick Task ID</Th>
                      <Th>Order Reference</Th>
                      <Th>Lines</Th>
                      <Th>Facility</Th>
                      <Th>Priority</Th>
                      <Th>Status</Th>
                      <Th className="text-right">Action</Th>
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
                            isSelected ? "bg-blue-50/80 font-medium" : "hover:bg-slate-50"
                          }`}
                        >
                          <Td className="font-mono font-bold text-slate-900">
                            TASK-{task.id.slice(0, 8)}
                          </Td>
                          <Td className="font-mono text-slate-700">{orderRef}</Td>
                          <Td className="font-mono font-semibold text-slate-800">
                            {task.lines?.length || 0} SKUs
                          </Td>
                          <Td>
                            <FacilityBadge code={whCode} />
                          </Td>
                          <Td>
                            <span className="font-mono font-bold text-slate-800">
                              P{task.priority ?? 1}
                            </span>
                          </Td>
                          <Td>
                            <StatusBadge value={task.status} />
                          </Td>
                          <Td className="text-right">
                            <Button
                              variant="secondary"
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
                          <p className="font-mono font-bold text-slate-900 break-all text-sm">
                            TASK-{task.id.slice(0, 8)}
                          </p>
                        </div>
                        <StatusBadge value={task.status} />
                      </div>

                      <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <dt className="text-muted-foreground text-[11px]">Order Reference</dt>
                          <dd className="font-mono text-slate-700 font-medium break-all">{orderRef}</dd>
                        </div>
                        <div>
                          <dt className="text-muted-foreground text-[11px]">Facility</dt>
                          <dd className="mt-0.5">
                            <FacilityBadge code={whCode} />
                          </dd>
                        </div>
                        <div>
                          <dt className="text-muted-foreground text-[11px]">Lines</dt>
                          <dd className="font-mono font-semibold text-slate-800">{task.lines?.length || 0} SKUs</dd>
                        </div>
                        <div>
                          <dt className="text-muted-foreground text-[11px]">Priority</dt>
                          <dd className="font-mono font-bold text-slate-800">P{task.priority ?? 1}</dd>
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
        <div className="min-w-0">
          {active ? (
            <Card className="sticky top-20 border-t-4 border-t-blue-600 p-5 shadow-sm space-y-4">
              <div className="flex items-start justify-between border-b border-slate-100 pb-3">
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                    Active Floor Pick Station
                  </span>
                  <h3 className="font-mono text-base font-bold text-slate-900 mt-0.5">
                    TASK-{active.id.slice(0, 8)}
                  </h3>
                </div>
                <StatusBadge value={active.status} />
              </div>

              {completeError ? <ErrorState message={completeError} /> : null}

              <div>
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                  Pick Verification Items
                </span>
                <p className="text-xs text-slate-500 mb-2">
                  Verify SKU and enter physical picked count from bin:
                </p>

                <div className="space-y-3">
                  {active.lines?.map((line) => {
                    const sku = productSku(products, line.product_id);
                    const name = productName(products, line.product_id);
                    const requested = Number(line.requested_quantity || 0);
                    const currentPicked = Number(picked[line.id] ?? requested);
                    const isShort = currentPicked < requested;

                    return (
                      <div
                        key={line.id}
                        className={`rounded-lg border p-3 text-xs ${
                          isShort ? "border-rose-300 bg-rose-50/50" : "border-slate-200 bg-slate-50"
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <div>
                            <p className="font-mono font-bold text-slate-900">{sku}</p>
                            <p className="text-[11px] text-slate-600">{name}</p>
                          </div>
                          <span className="font-mono font-bold text-slate-700 text-xs">
                            Req: {requested}
                          </span>
                        </div>

                        <div className="mt-2 flex items-center justify-between border-t border-slate-200/60 pt-2">
                          <label className="font-bold text-slate-700 text-[10px] uppercase">
                            Actual Picked Quantity:
                          </label>
                          <input
                            type="number"
                            min="0"
                            max={requested}
                            value={picked[line.id] ?? requested}
                            onChange={(e) => setPicked({ ...picked, [line.id]: e.target.value })}
                            className="w-20 rounded-md border border-slate-300 bg-white px-2 py-1 font-mono text-xs font-bold text-right text-slate-900 focus:outline-none"
                          />
                        </div>

                        {isShort ? (
                          <p className="mt-1 text-[10px] font-bold text-rose-700 flex items-center gap-1">
                            <AlertTriangle className="size-3" /> Short pick detected (
                            {requested - currentPicked} missing)
                          </p>
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="border-t border-slate-100 pt-3 flex gap-2">
                <Button
                  variant="primary"
                  size="md"
                  onClick={complete}
                  disabled={completePickTaskMutation.isPending}
                  className="w-full font-bold bg-emerald-600 hover:bg-emerald-700"
                >
                  <CheckCircle2 className="size-4" />
                  <span>
                    {completePickTaskMutation.isPending
                      ? "Confirming..."
                      : "Confirm Pick & Pack Complete"}
                  </span>
                </Button>
              </div>
            </Card>
          ) : (
            <Card className="p-6 text-center text-xs text-slate-500">
              Select a pick task from the queue to enter floor picking mode.
            </Card>
          )}
        </div>
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
            <label className="block font-bold text-slate-700 uppercase tracking-wider text-[10px]">
              Select Reserved Order
            </label>
            <select
              value={newTask.order_id}
              onChange={(e) => setNewTask({ ...newTask, order_id: e.target.value })}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-800 focus:border-blue-600 focus:outline-none"
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
            <label className="block font-bold text-slate-700 uppercase tracking-wider text-[10px]">
              Wave Priority Level (1-5)
            </label>
            <input
              type="number"
              min="1"
              max="5"
              value={newTask.priority}
              onChange={(e) => setNewTask({ ...newTask, priority: e.target.value })}
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-mono text-xs font-bold text-slate-900 focus:outline-none"
            />
          </div>
        </div>

        <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:items-center sm:justify-end border-t border-slate-100 pt-4">
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
