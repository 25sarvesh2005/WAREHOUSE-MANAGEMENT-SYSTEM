import { Link } from "@tanstack/react-router";
import {
  ArrowRight,
  Bot,
  Boxes,
  ClipboardList,
  Database,
  FileSpreadsheet,
  Mic,
  PackageCheck,
  Repeat,
  SearchCheck,
  ShieldCheck,
  ShoppingCart,
  Truck,
  Undo2,
  Warehouse,
} from "lucide-react";
import { FacilityBadge, StatusBadge } from "@/components/StatusBadge";
import { Card, LedgerNoticeBanner, TableShell, Td, Th } from "@/components/ui-kit";
import {
  useBalancesQuery,
  useMovementsQuery,
  useOrdersQuery,
  usePickTasksQuery,
  useProductsQuery,
  useReceiptsQuery,
  useReturnsQuery,
  useSellersQuery,
  useTransfersQuery,
  useWarehousesQuery,
} from "@/hooks/use-api";
import { productSku, sellerLabel, warehouseLabel } from "@/lib/display";
import { formatQty, relativeTime } from "@/lib/format";
import type { Balance, Movement, Product, User, Warehouse as WarehouseRecord } from "@/lib/types";

function numericQuantity(value: unknown): number {
  return Number(value || 0);
}

function sumState(balances: Balance[], inventoryState: string, warehouseId?: string): number {
  return Math.round(
    balances
      .filter(
        (balance) =>
          balance.inventory_state === inventoryState &&
          (!warehouseId || balance.warehouse_id === warehouseId),
      )
      .reduce((total, balance) => total + numericQuantity(balance.quantity), 0),
  );
}

function findFacility(warehouses: WarehouseRecord[], matchers: string[], fallbackIndex: number) {
  return (
    warehouses.find((warehouse) =>
      matchers.some((matcher) =>
        `${warehouse.code} ${warehouse.name} ${warehouse.city ?? ""}`
          .toUpperCase()
          .includes(matcher),
      ),
    ) ?? warehouses[fallbackIndex]
  );
}

function MetricCard({
  label,
  value,
  description,
  icon: Icon,
  to,
}: {
  description: string;
  icon: typeof Boxes;
  label: string;
  to?: string;
  value: string | number;
}) {
  const content = (
    <Card className="group h-full p-5 transition-all hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-panel">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-muted-foreground">{label}</p>
          <p className="mt-2 font-mono text-3xl font-semibold tracking-tight text-foreground">
            {value}
          </p>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">{description}</p>
        </div>
        <span className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-primary-tint text-primary transition-colors group-hover:bg-primary group-hover:text-white">
          <Icon className="size-6" />
        </span>
      </div>
    </Card>
  );

  return to ? <Link to={to}>{content}</Link> : content;
}

function FacilityPanel({
  warehouse,
  balances,
  openOrders,
  pendingReceipts,
}: {
  balances: Balance[];
  openOrders: number;
  pendingReceipts: number;
  warehouse: WarehouseRecord | undefined;
}) {
  if (!warehouse) {
    return (
      <Card>
        <p className="text-sm font-semibold text-foreground">Warehouse not configured</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Add Reno and Columbus warehouse master data before launch.
        </p>
      </Card>
    );
  }

  const available = sumState(balances, "AVAILABLE", warehouse.id);
  const reserved = sumState(balances, "RESERVED", warehouse.id);
  const damaged = sumState(balances, "DAMAGED", warehouse.id);
  const quarantined = sumState(balances, "QUARANTINED", warehouse.id);
  const inTransit = sumState(balances, "IN_TRANSIT", warehouse.id);

  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <FacilityBadge code={warehouse.code} />
          <h3 className="mt-3 text-lg font-semibold tracking-tight text-foreground">
            {warehouse.name}
          </h3>
          <p className="mt-1 text-sm text-muted-foreground">
            {warehouse.city ?? "Warehouse"}, {warehouse.state ?? "US"}
          </p>
        </div>
        <span className="flex size-12 items-center justify-center rounded-2xl bg-primary-tint text-primary">
          <Warehouse className="size-6" />
        </span>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3">
        {[
          ["Available", available],
          ["Reserved", reserved],
          ["Damaged", damaged],
          ["Quarantine", quarantined],
          ["In transit", inTransit],
          ["Open work", openOrders + pendingReceipts],
        ].map(([label, value]) => (
          <div key={label} className="rounded-2xl bg-primary-tint px-4 py-3">
            <p className="text-xs font-medium text-primary">{label}</p>
            <p className="mt-1 font-mono text-xl font-semibold text-foreground">
              {Number(value).toLocaleString()}
            </p>
          </div>
        ))}
      </div>
    </Card>
  );
}

function OptionCard({
  label,
  count,
  detail,
  to,
  icon: Icon,
}: {
  count: number;
  detail: string;
  icon: typeof ClipboardList;
  label: string;
  to: string;
}) {
  return (
    <Link
      to={to}
      className="group flex items-center justify-between gap-4 rounded-3xl border border-border bg-white p-4 shadow-card transition-all hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-panel"
    >
      <span className="flex items-center gap-3">
        <span className="flex size-11 shrink-0 items-center justify-center rounded-2xl bg-primary-tint text-primary transition-colors group-hover:bg-primary group-hover:text-white">
          <Icon className="size-5" />
        </span>
        <span>
          <span className="block text-sm font-semibold text-foreground">{label}</span>
          <span className="block text-xs text-muted-foreground">{detail}</span>
        </span>
      </span>
      <span className="font-mono text-2xl font-semibold text-primary">{count}</span>
    </Link>
  );
}

function MovementTable({
  movements,
  products,
  warehouses,
}: {
  movements: Movement[];
  products: Product[];
  warehouses: WarehouseRecord[];
}) {
  return (
    <TableShell>
      <thead>
        <tr>
          <Th>Recorded</Th>
          <Th>SKU</Th>
          <Th>Warehouse</Th>
          <Th>Type</Th>
          <Th>State</Th>
          <Th className="text-right">Delta</Th>
        </tr>
      </thead>
      <tbody>
        {movements.slice(0, 10).map((movement) => (
          <tr key={movement.id} className="hover:bg-primary-tint/40">
            <Td className="font-mono text-xs text-muted-foreground">
              {relativeTime(movement.occurred_at)}
            </Td>
            <Td className="font-mono font-semibold">{productSku(products, movement.product_id)}</Td>
            <Td>{warehouseLabel(warehouses, movement.warehouse_id)}</Td>
            <Td>
              <StatusBadge value={movement.movement_type} />
            </Td>
            <Td>
              <StatusBadge value={movement.inventory_state} />
            </Td>
            <Td className="text-right font-mono font-semibold text-primary">
              {numericQuantity(movement.quantity_delta) >= 0 ? "+" : ""}
              {formatQty(movement.quantity_delta)}
            </Td>
          </tr>
        ))}
      </tbody>
    </TableShell>
  );
}

export function Dashboard({ user }: { user: User }) {
  const { data: balances = [] } = useBalancesQuery();
  const { data: sellers = [] } = useSellersQuery();
  const { data: warehouses = [] } = useWarehousesQuery();
  const { data: products = [] } = useProductsQuery();
  const { data: orders = [] } = useOrdersQuery();
  const { data: receipts = [] } = useReceiptsQuery();
  const { data: pickTasks = [] } = usePickTasksQuery();
  const { data: transfers = [] } = useTransfersQuery();
  const { data: returnOrders = [] } = useReturnsQuery();
  const { data: movements = [] } = useMovementsQuery(200);

  const renoWarehouse = findFacility(warehouses, ["RNO", "RENO"], 0);
  const columbusWarehouse = findFacility(warehouses, ["CMH", "COLUMBUS"], 1);
  const availableUnits = sumState(balances, "AVAILABLE");
  const reservedUnits = sumState(balances, "RESERVED");
  const nonSellableUnits =
    sumState(balances, "DAMAGED") +
    sumState(balances, "QUARANTINED") +
    sumState(balances, "RETURN_INSPECTION") +
    sumState(balances, "IN_TRANSIT");

  const pendingReceipts = receipts.filter((receipt) =>
    ["DRAFT", "PENDING_OVERRIDE", "IN_PROGRESS"].includes(receipt.status),
  );
  const duplicateSensitiveReceipts = receipts.filter(
    (receipt) => receipt.status === "PENDING_OVERRIDE" || receipt.is_duplicate_override,
  );
  const unreservedOrders = orders.filter((order) =>
    ["PENDING", "PARTIALLY_RESERVED", "BACKORDERED"].includes(order.status),
  );
  const activeFulfillment = orders.filter((order) =>
    ["RESERVED", "PICKING", "PACKED"].includes(order.status),
  );
  const shortPicks = pickTasks.filter((task) => task.status === "SHORT_PICK_EXCEPTION");
  const transferExceptions = transfers.filter((transfer) =>
    ["PENDING_APPROVAL", "DISCREPANCY_REVIEW"].includes(transfer.status),
  );
  const returnsInInspection = returnOrders.filter((returnOrder) =>
    ["EXPECTED", "INSPECTION", "PARTIALLY_DISPOSED"].includes(returnOrder.status),
  );
  const renoOpenWork =
    orders.filter((order) => order.warehouse_id === renoWarehouse?.id).length +
    pickTasks.filter((task) => task.warehouse_id === renoWarehouse?.id).length;
  const columbusOpenWork =
    orders.filter((order) => order.warehouse_id === columbusWarehouse?.id).length +
    pickTasks.filter((task) => task.warehouse_id === columbusWarehouse?.id).length;

  return (
    <div className="space-y-6">
      <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <Card className="relative overflow-hidden p-7">
          <div className="absolute right-0 top-0 h-40 w-40 rounded-bl-[64px] bg-primary-tint" />
          <div className="relative">
            <p className="text-sm font-semibold text-primary">
              Whitfield Operations Command Center
            </p>
            <h1 className="mt-3 max-w-3xl text-3xl font-semibold tracking-tight text-foreground md:text-4xl">
              Welcome back, {user.name.split(" ")[0] || user.name}.
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-muted-foreground">
              Bicoastal operations overview for Reno (RNO) and Columbus (CMH) hubs: real-time stock
              balances, inbound receipts, active fulfillment, and hub transfers.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                to="/receipts"
                className="inline-flex items-center gap-2 rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-white shadow-[0_8px_20px_rgba(37,99,235,0.22)] transition hover:bg-primary-dark"
              >
                Inbound dock receipts <ArrowRight className="size-4" />
              </Link>
              <Link
                to="/inventory"
                className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-white px-5 py-2.5 text-sm font-semibold text-primary transition hover:bg-primary-tint"
              >
                Live inventory matrix
              </Link>
            </div>
          </div>
        </Card>

        <Card className="p-5">
          <div className="mb-4 flex items-center gap-3">
            <span className="flex size-12 items-center justify-center rounded-2xl bg-primary-tint text-primary">
              <SearchCheck className="size-6" />
            </span>
            <div>
              <h2 className="font-semibold text-foreground">Operational Overview</h2>
              <p className="text-sm text-muted-foreground">
                Signed in as {user.role.replaceAll("_", " ")}
              </p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {[
              ["Sellers", sellers.length],
              ["SKUs", products.length],
              [
                "Exceptions",
                pendingReceipts.length +
                  shortPicks.length +
                  transferExceptions.length +
                  returnsInInspection.length,
              ],
              ["Active orders", activeFulfillment.length],
            ].map(([label, value]) => (
              <div key={label} className="rounded-2xl bg-primary-tint px-4 py-3">
                <p className="text-xs font-medium text-primary">{label}</p>
                <p className="mt-1 font-mono text-2xl font-semibold text-foreground">{value}</p>
              </div>
            ))}
          </div>
        </Card>
      </section>

      <LedgerNoticeBanner message="Live Real-Time Inventory: All balances are synchronized across Reno (RNO) and Columbus (CMH) fulfillment centers with audit-grade ledger precision." />

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          icon={Boxes}
          label="Sellable available"
          value={availableUnits.toLocaleString()}
          description="Good stock ready to reserve."
          to="/inventory"
        />
        <MetricCard
          icon={ShoppingCart}
          label="Reserved"
          value={reservedUnits.toLocaleString()}
          description="Locked for orders."
          to="/orders"
        />
        <MetricCard
          icon={ShieldCheck}
          label="Controlled stock"
          value={nonSellableUnits.toLocaleString()}
          description="Damaged, quarantine or in transit."
          to="/inventory"
        />
        <MetricCard
          icon={Truck}
          label="Active fulfillment"
          value={activeFulfillment.length}
          description="Reserved, picking or packed."
          to="/pick-tasks"
        />
      </section>

      <section className="grid gap-5 xl:grid-cols-2">
        <FacilityPanel
          warehouse={renoWarehouse}
          balances={balances}
          openOrders={renoOpenWork}
          pendingReceipts={
            pendingReceipts.filter((receipt) => receipt.warehouse_id === renoWarehouse?.id).length
          }
        />
        <FacilityPanel
          warehouse={columbusWarehouse}
          balances={balances}
          openOrders={columbusOpenWork}
          pendingReceipts={
            pendingReceipts.filter((receipt) => receipt.warehouse_id === columbusWarehouse?.id)
              .length
          }
        />
      </section>

      <section className="grid gap-5 xl:grid-cols-[0.9fr_1.1fr]">
        <Card>
          <div className="mb-4 flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-primary">Option board</p>
              <h2 className="text-xl font-semibold tracking-tight text-foreground">
                What needs attention
              </h2>
            </div>
            <ClipboardList className="size-5 text-primary" />
          </div>
          <div className="space-y-3">
            <OptionCard
              icon={PackageCheck}
              label="Inbound receipts"
              count={pendingReceipts.length}
              detail="Dock work not completed"
              to="/receipts"
            />
            <OptionCard
              icon={Database}
              label="Duplicate checks"
              count={duplicateSensitiveReceipts.length}
              detail="Potential replay or override"
              to="/receipts"
            />
            <OptionCard
              icon={ShoppingCart}
              label="Orders not reserved"
              count={unreservedOrders.length}
              detail="Backorder or partial allocation"
              to="/orders"
            />
            <OptionCard
              icon={ClipboardList}
              label="Short picks"
              count={shortPicks.length}
              detail="Floor shortage exceptions"
              to="/pick-tasks"
            />
            <OptionCard
              icon={Repeat}
              label="Transfers and returns"
              count={transferExceptions.length + returnsInInspection.length}
              detail="Review in-transit and inspection"
              to="/transfers"
            />
          </div>
        </Card>

        <Card>
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-primary">Audit stream</p>
              <h2 className="text-xl font-semibold tracking-tight text-foreground">
                Recent inventory movements
              </h2>
            </div>
            <Link
              to="/inventory"
              className="inline-flex items-center gap-1 rounded-full bg-primary-tint px-3 py-1.5 text-xs font-semibold text-primary"
            >
              Open ledger <ArrowRight className="size-3.5" />
            </Link>
          </div>
          {movements.length === 0 ? (
            <div className="rounded-3xl border border-dashed border-border bg-background p-8 text-center text-sm text-muted-foreground">
              No ledger movements yet. Completing controlled workflows will populate this stream.
            </div>
          ) : (
            <MovementTable movements={movements} products={products} warehouses={warehouses} />
          )}
        </Card>
      </section>

      <section className="grid gap-5 lg:grid-cols-3">
        <SmallWorkflowCard
          icon={Mic}
          label="Voice receiving"
          copy="Speak draft quantities while scanning UPCs. Voice never completes a receipt."
          to="/receipts"
        />
        <SmallWorkflowCard
          icon={Bot}
          label="AI assistant"
          copy="Read-only answers and draft-only operational help with scoped data."
          to="/ai-assistant"
        />
        <SmallWorkflowCard
          icon={FileSpreadsheet}
          label="Excel cutover"
          copy="Stage, validate, approve and apply opening inventory through ledger movements."
          to="/migration"
        />
      </section>

      <section className="grid gap-5 xl:grid-cols-2">
        <Card>
          <div className="mb-3 flex items-center gap-2">
            <PackageCheck className="size-5 text-primary" />
            <h3 className="text-lg font-semibold text-foreground">Newest receiving work</h3>
          </div>
          <div className="space-y-2">
            {receipts.slice(0, 5).map((receipt) => (
              <Link
                key={receipt.id}
                to="/receipts/$id"
                params={{ id: receipt.id }}
                className="flex items-center justify-between gap-3 rounded-2xl border border-border bg-white px-4 py-3 text-sm transition hover:bg-primary-tint"
              >
                <span className="min-w-0">
                  <span className="block truncate font-mono font-semibold text-foreground">
                    {receipt.receipt_number}
                  </span>
                  <span className="block truncate text-muted-foreground">
                    {sellerLabel(sellers, receipt.seller_id)} - {receipt.source_reference}
                  </span>
                </span>
                <StatusBadge value={receipt.status} />
              </Link>
            ))}
            {receipts.length === 0 ? (
              <p className="rounded-3xl border border-dashed border-border bg-background p-5 text-sm text-muted-foreground">
                No receipts staged yet.
              </p>
            ) : null}
          </div>
        </Card>

        <Card>
          <div className="mb-3 flex items-center gap-2">
            <Undo2 className="size-5 text-primary" />
            <h3 className="text-lg font-semibold text-foreground">Transfer and return control</h3>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <Link
              to="/transfers"
              className="rounded-3xl bg-primary-tint p-5 transition hover:bg-blue-100"
            >
              <p className="text-sm font-medium text-primary">Transfers requiring attention</p>
              <p className="mt-2 font-mono text-3xl font-semibold text-foreground">
                {transferExceptions.length}
              </p>
            </Link>
            <Link
              to="/returns"
              className="rounded-3xl bg-primary-tint p-5 transition hover:bg-blue-100"
            >
              <p className="text-sm font-medium text-primary">Returns awaiting inspection</p>
              <p className="mt-2 font-mono text-3xl font-semibold text-foreground">
                {returnsInInspection.length}
              </p>
            </Link>
          </div>
        </Card>
      </section>
    </div>
  );
}

function SmallWorkflowCard({
  copy,
  icon: Icon,
  label,
  to,
}: {
  copy: string;
  icon: typeof Mic;
  label: string;
  to: string;
}) {
  return (
    <Link to={to}>
      <Card className="group h-full transition-all hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-panel">
        <div className="flex items-center gap-3">
          <span className="flex size-12 items-center justify-center rounded-2xl bg-primary-tint text-primary transition-colors group-hover:bg-primary group-hover:text-white">
            <Icon className="size-6" />
          </span>
          <h3 className="font-semibold text-foreground">{label}</h3>
        </div>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">{copy}</p>
        <span className="mt-4 inline-flex items-center gap-1 text-sm font-semibold text-primary">
          Open workflow <ArrowRight className="size-4" />
        </span>
      </Card>
    </Link>
  );
}
