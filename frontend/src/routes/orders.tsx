import { createFileRoute } from "@tanstack/react-router";
import {
  AlertTriangle,
  Clock,
  Database,
  Lock,
  PackageCheck,
  Plus,
  Search,
  ShieldCheck,
  ShoppingCart,
  Trash2,
  Truck,
  XCircle,
} from "lucide-react";
import { useMemo, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { FacilityBadge, StatusBadge } from "@/components/StatusBadge";
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  IconTile,
  LoadingState,
  PageHeader,
  ScannerInputField,
  TableShell,
  Td,
  Th,
} from "@/components/ui-kit";
import {
  orderDestination,
  productName,
  productSku,
  sellerLabel,
  warehouseLabel,
} from "@/lib/display";
import { formatDate, formatQty } from "@/lib/format";
import {
  useCancelOrderMutation,
  useCreateOrderMutation,
  useOrdersQuery,
  useProductsQuery,
  useReserveOrderMutation,
  useSellersQuery,
  useWarehousesQuery,
} from "@/hooks/use-api";
import type { Order, Product, Seller, Warehouse } from "@/lib/types";

export const Route = createFileRoute("/orders")({
  head: () => ({
    meta: [
      { title: "Customer Orders & Reservation | Whitfield Ops" },
      {
        name: "description",
        content:
          "Order queue with server-confirmed inventory reservation preventing overselling race conditions.",
      },
      { property: "og:title", content: "Customer Orders & Reservation | Whitfield Ops" },
      {
        property: "og:description",
        content: "Transactional stock reservation and order allocation across Reno and Columbus.",
      },
    ],
  }),
  component: OrdersPage,
});

type SortKey = "priority" | "seller_order_number" | "destination" | "status";
const EMPTY_ORDERS: Order[] = [];
const EMPTY_SELLERS: Seller[] = [];
const EMPTY_WAREHOUSES: Warehouse[] = [];
const EMPTY_PRODUCTS: Product[] = [];

function OrdersPage() {
  const ordersQuery = useOrdersQuery();
  const sellersQuery = useSellersQuery();
  const warehousesQuery = useWarehousesQuery();
  const productsQuery = useProductsQuery();
  const orders = ordersQuery.data ?? EMPTY_ORDERS;
  const sellers = sellersQuery.data ?? EMPTY_SELLERS;
  const warehouses = warehousesQuery.data ?? EMPTY_WAREHOUSES;
  const products = productsQuery.data ?? EMPTY_PRODUCTS;
  const createOrderMutation = useCreateOrderMutation();
  const reserveOrderMutation = useReserveOrderMutation();
  const cancelOrderMutation = useCancelOrderMutation();

  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<SortKey>("priority");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [confirmCancel, setConfirmCancel] = useState<string | null>(null);
  const [openCreate, setOpenCreate] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [orderForm, setOrderForm] = useState({
    seller_id: "",
    warehouse_id: "",
    seller_order_number: "",
    channel: "DIRECT",
    customer_name: "",
    shipping_address_line1: "",
    city: "",
    state: "",
    postal_code: "",
  });
  const [lineForm, setLineForm] = useState({ product_id: "", quantity: "1" });
  const [orderLines, setOrderLines] = useState<
    Array<{ product_id: string; ordered_quantity: number }>
  >([]);

  const createSellerId = orderForm.seller_id || sellers[0]?.id || "";
  const createWarehouseId = orderForm.warehouse_id || warehouses[0]?.id || "";
  const createProductOptions = products.filter(
    (product) => !createSellerId || product.seller_id === createSellerId,
  );
  const selectedLineProductId = lineForm.product_id || createProductOptions[0]?.id || "";

  // Real operational counts computed from live dataset
  const openOrdersCount = orders.filter(
    (o) => o.status !== "CLOSED" && o.status !== "CANCELLED",
  ).length;
  const inFlightCount = orders.filter((o) =>
    ["RESERVED", "PICKING", "PACKED"].includes(o.status),
  ).length;
  const backorderedCount = orders.filter((o) =>
    ["PENDING", "PARTIALLY_RESERVED"].includes(o.status),
  ).length;

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return orders
      .filter(
        (o: Order) =>
          !q ||
          (o.seller_order_number || "").toLowerCase().includes(q) ||
          orderDestination(o).toLowerCase().includes(q) ||
          sellerLabel(sellers, o.seller_id).toLowerCase().includes(q),
      )
      .slice()
      .sort((a: Order, b: Order) => {
        const pA = Number(a.policy_snapshot?.["priority"] ?? 5);
        const pB = Number(b.policy_snapshot?.["priority"] ?? 5);
        return sort === "priority"
          ? pA - pB
          : sort === "destination"
            ? orderDestination(a).localeCompare(orderDestination(b))
            : String((a as unknown as Record<string, unknown>)[sort] || "").localeCompare(
                String((b as unknown as Record<string, unknown>)[sort] || ""),
              );
      });
  }, [orders, query, sellers, sort]);

  const activeSelectedId = selectedId || rows[0]?.id || null;
  const selected = orders.find((o: Order) => o.id === activeSelectedId) ?? null;

  const handleConfirmReservation = async (orderId: string) => {
    try {
      await reserveOrderMutation.mutateAsync(orderId);
      ordersQuery.refetch();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to reserve order stock.");
    }
  };

  const handleCancelOrder = async (orderId: string) => {
    try {
      await cancelOrderMutation.mutateAsync({ id: orderId });
      setConfirmCancel(null);
      ordersQuery.refetch();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to cancel order.");
    }
  };

  function addOrderLine() {
    setCreateError(null);
    const quantity = Number(lineForm.quantity || 0);
    if (!selectedLineProductId) return setCreateError("Select a product before adding a line.");
    if (Number.isNaN(quantity) || quantity <= 0) {
      return setCreateError("Line quantity must be greater than zero.");
    }

    setOrderLines((current) => {
      const existing = current.find((line) => line.product_id === selectedLineProductId);
      if (existing) {
        return current.map((line) =>
          line.product_id === selectedLineProductId
            ? { ...line, ordered_quantity: line.ordered_quantity + quantity }
            : line,
        );
      }
      return [...current, { product_id: selectedLineProductId, ordered_quantity: quantity }];
    });
    setLineForm({ product_id: selectedLineProductId, quantity: "1" });
  }

  async function createOrder(e: React.FormEvent) {
    e.preventDefault();
    setCreateError(null);
    const sellerOrderNumber = orderForm.seller_order_number.trim();
    if (!createSellerId) return setCreateError("Seller is required.");
    if (!createWarehouseId) return setCreateError("Warehouse is required.");
    if (!sellerOrderNumber) return setCreateError("Seller order number is required.");
    if (orderLines.length === 0) return setCreateError("Add at least one order line.");

    try {
      await createOrderMutation.mutateAsync({
        seller_id: createSellerId,
        warehouse_id: createWarehouseId,
        seller_order_number: sellerOrderNumber,
        channel: orderForm.channel.trim() || "DIRECT",
        ...(orderForm.customer_name.trim()
          ? { customer_name: orderForm.customer_name.trim() }
          : {}),
        ...(orderForm.shipping_address_line1.trim()
          ? { shipping_address_line1: orderForm.shipping_address_line1.trim() }
          : {}),
        ...(orderForm.city.trim() ? { city: orderForm.city.trim() } : {}),
        ...(orderForm.state.trim() ? { state: orderForm.state.trim() } : {}),
        ...(orderForm.postal_code.trim() ? { postal_code: orderForm.postal_code.trim() } : {}),
        lines: orderLines,
      });
      setOpenCreate(false);
      setOrderForm({
        seller_id: "",
        warehouse_id: "",
        seller_order_number: "",
        channel: "DIRECT",
        customer_name: "",
        shipping_address_line1: "",
        city: "",
        state: "",
        postal_code: "",
      });
      setLineForm({ product_id: "", quantity: "1" });
      setOrderLines([]);
      ordersQuery.refetch();
    } catch (err: unknown) {
      setCreateError(err instanceof Error ? err.message : "Could not create order.");
    }
  }

  return (
    <AppShell>
      <PageHeader
        title="Customer Orders & Allocation"
        subtitle="Manage customer orders with server-confirmed inventory reservations to eliminate oversell race conditions."
        actions={
          <Button onClick={() => setOpenCreate(true)} className="gap-2">
            <Plus className="size-4" /> New Customer Order
          </Button>
        }
      />

      <div className="mb-5 flex items-center gap-2.5 rounded-lg border border-blue-200/80 bg-blue-50/60 px-3.5 py-2 text-xs text-blue-900">
        <Lock className="size-4 shrink-0 text-blue-600" />
        <span>
          <strong className="font-semibold">No-Oversell Protection:</strong> When orders are placed,
          stock is atomically reserved on the server so two workers never confirm the same last
          units.
        </span>
      </div>

      {[ordersQuery, sellersQuery, warehousesQuery, productsQuery].some((q) => q.isLoading) ? (
        <LoadingState message="Loading orders queue..." />
      ) : null}
      {[ordersQuery, sellersQuery, warehousesQuery, productsQuery].find((q) => q.isError) ? (
        <ErrorState
          message="Could not load orders from the backend."
          onRetry={() => {
            ordersQuery.refetch();
            sellersQuery.refetch();
            warehousesQuery.refetch();
            productsQuery.refetch();
          }}
        />
      ) : null}

      {/* Live Operational Metrics */}
      <div className="mb-5 grid gap-3.5 sm:grid-cols-3">
        <Card className="border-l-4 border-l-blue-600 p-4">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
            Total Active Orders
          </span>
          <p className="mt-1 font-mono text-2xl font-extrabold text-slate-900">{openOrdersCount}</p>
          <p className="mt-1 text-[11px] text-slate-500">Across Reno and Columbus</p>
        </Card>

        <Card className="border-l-4 border-l-purple-600 p-4">
          <span className="text-[10px] font-bold text-purple-800 uppercase tracking-wider">
            In Pick / Pack Workflow
          </span>
          <p className="mt-1 font-mono text-2xl font-extrabold text-purple-900">{inFlightCount}</p>
          <p className="mt-1 text-[11px] text-slate-500">Stock reserved on server</p>
        </Card>

        <Card className="border-l-4 border-l-amber-500 p-4">
          <span className="text-[10px] font-bold text-amber-800 uppercase tracking-wider">
            Awaiting Stock / Backorder
          </span>
          <p className="mt-1 font-mono text-2xl font-extrabold text-amber-900">
            {backorderedCount}
          </p>
          <p className="mt-1 text-[11px] text-slate-500">Pending inbound receipts</p>
        </Card>
      </div>

      {/* Main Grid: Orders Table & Order Detail Drawer */}
      <div className="grid gap-6 xl:grid-cols-[1.7fr_1fr]">
        <div className="space-y-4">
          <Card className="p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="w-full sm:w-72">
                <ScannerInputField
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search order #, customer, seller..."
                />
              </div>
              <div className="flex items-center gap-2 text-xs font-bold text-foreground">
                <span>Sort by:</span>
                <select
                  value={sort}
                  onChange={(e) => setSort(e.target.value as SortKey)}
                  className="rounded-full border border-border bg-white px-3.5 py-1.5 text-xs font-bold text-foreground shadow-xs outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 transition-all cursor-pointer"
                >
                  <option value="priority">Priority</option>
                  <option value="seller_order_number">Order Number</option>
                  <option value="destination">Destination</option>
                  <option value="status">Status</option>
                </select>
              </div>
            </div>
          </Card>

          {rows.length === 0 ? (
            <Card className="p-8">
              <EmptyState
                message="No orders found matching search criteria"
                hint="Create a new customer order or clear filter query."
              />
            </Card>
          ) : (
            <TableShell>
              <thead>
                <tr>
                  <Th>Order Number</Th>
                  <Th>Seller Tenant</Th>
                  <Th>Facility</Th>
                  <Th>Customer Destination</Th>
                  <Th>Status</Th>
                  <Th className="text-right">Action</Th>
                </tr>
              </thead>
              <tbody>
                {rows.map((order) => {
                  const isSelected = order.id === activeSelectedId;
                  const whCode = warehouses.find((w) => w.id === order.warehouse_id)?.code || "WH";

                  return (
                    <tr
                      key={order.id}
                      onClick={() => setSelectedId(order.id)}
                      className={`cursor-pointer transition-colors ${
                        isSelected ? "bg-blue-50/80 font-medium" : "hover:bg-slate-50"
                      }`}
                    >
                      <Td className="font-mono font-bold text-slate-900">
                        {order.seller_order_number || `ORD-${order.id.slice(0, 8)}`}
                      </Td>
                      <Td className="text-slate-700">{sellerLabel(sellers, order.seller_id)}</Td>
                      <Td>
                        <FacilityBadge code={whCode} />
                      </Td>
                      <Td className="text-slate-600 truncate max-w-[140px]">
                        {orderDestination(order)}
                      </Td>
                      <Td>
                        <StatusBadge value={order.status} />
                      </Td>
                      <Td className="text-right">
                        {order.status === "PENDING" ? (
                          <Button
                            variant="primary"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleConfirmReservation(order.id);
                            }}
                            disabled={reserveOrderMutation.isPending}
                            className="text-xs"
                          >
                            Reserve
                          </Button>
                        ) : (
                          <span className="text-xs text-blue-600 font-semibold">Inspect</span>
                        )}
                      </Td>
                    </tr>
                  );
                })}
              </tbody>
            </TableShell>
          )}
        </div>

        {/* Right Column: Selected Order Detail Card */}
        <div>
          {selected ? (
            <Card className="sticky top-20 border-t-4 border-t-blue-600 p-5 shadow-sm space-y-4">
              <div className="flex items-start justify-between border-b border-slate-100 pb-3">
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                    Selected Order
                  </span>
                  <h3 className="font-mono text-base font-bold text-slate-900 mt-0.5">
                    {selected.seller_order_number || `ORD-${selected.id.slice(0, 8)}`}
                  </h3>
                  <p className="text-xs text-slate-500 font-medium">
                    Seller: {sellerLabel(sellers, selected.seller_id)}
                  </p>
                </div>
                <StatusBadge value={selected.status} />
              </div>

              {/* Destination Details */}
              <div className="rounded-lg bg-slate-50 p-3 border border-slate-200 text-xs">
                <span className="text-[10px] font-bold text-slate-500 uppercase">
                  Shipping Destination
                </span>
                <p className="font-semibold text-slate-800 mt-0.5">
                  {selected.customer_name || "Customer Direct"}
                </p>
                <p className="text-slate-600">
                  {selected.shipping_address_line1 || "No street address"}
                </p>
                <p className="text-slate-600">
                  {selected.city ? `${selected.city}, ` : ""}
                  {selected.state || ""} {selected.postal_code || ""}
                </p>
              </div>

              {/* Order Lines */}
              <div>
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                  Order Line Items ({selected.lines?.length || 0})
                </span>
                <div className="mt-2 space-y-2 max-h-48 overflow-y-auto">
                  {selected.lines?.map((line) => (
                    <div
                      key={line.id}
                      className="flex items-center justify-between rounded-lg border border-slate-100 p-2 text-xs bg-white"
                    >
                      <div>
                        <p className="font-mono font-bold text-slate-900">
                          {productSku(products, line.product_id)}
                        </p>
                        <p className="text-[11px] text-slate-500 truncate max-w-[160px]">
                          {productName(products, line.product_id)}
                        </p>
                      </div>
                      <div className="text-right">
                        <span className="font-mono font-bold text-slate-900">
                          Qty: {formatQty(line.ordered_quantity)}
                        </span>
                        <p className="text-[10px] text-emerald-700 font-medium">
                          Res: {formatQty(line.reserved_quantity)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Order Action Buttons */}
              <div className="border-t border-slate-100 pt-3 flex flex-wrap gap-2">
                {selected.status === "PENDING" ? (
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => handleConfirmReservation(selected.id)}
                    disabled={reserveOrderMutation.isPending}
                    className="flex-1 font-bold"
                  >
                    Confirm Stock Reservation
                  </Button>
                ) : null}

                {selected.status !== "CLOSED" && selected.status !== "CANCELLED" ? (
                  confirmCancel === selected.id ? (
                    <div className="flex w-full items-center gap-2">
                      <span className="text-xs text-rose-700 font-medium">Confirm cancel?</span>
                      <Button
                        variant="danger"
                        size="sm"
                        onClick={() => handleCancelOrder(selected.id)}
                        disabled={cancelOrderMutation.isPending}
                      >
                        Yes, Cancel
                      </Button>
                      <Button variant="secondary" size="sm" onClick={() => setConfirmCancel(null)}>
                        No
                      </Button>
                    </div>
                  ) : (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setConfirmCancel(selected.id)}
                      className="text-rose-700 hover:bg-rose-50 border-rose-200"
                    >
                      Cancel Order
                    </Button>
                  )
                ) : null}
              </div>
            </Card>
          ) : (
            <Card className="p-6 text-center text-xs text-slate-500">
              Select an order to view allocation and item breakdown.
            </Card>
          )}
        </div>
      </div>

      {/* Create Customer Order Modal */}
      {openCreate ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-xs">
          <div className="w-full max-w-xl rounded-xl border border-slate-200 bg-white p-6 shadow-2xl animate-rise max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900 text-base">Create Customer Order</h3>
              <button
                onClick={() => setOpenCreate(false)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 cursor-pointer"
              >
                ✕
              </button>
            </div>

            {createError ? (
              <div className="mt-3">
                <ErrorState message={createError} />
              </div>
            ) : null}

            <form onSubmit={createOrder} className="mt-4 space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                    Seller Account
                  </label>
                  <select
                    value={orderForm.seller_id}
                    onChange={(e) => setOrderForm({ ...orderForm, seller_id: e.target.value })}
                    className="mt-1.5 w-full rounded-xl border border-input bg-white px-3.5 py-2 text-xs font-bold text-foreground shadow-xs outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 transition-all cursor-pointer"
                  >
                    {sellers.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name} ({s.code})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                    Fulfillment Warehouse
                  </label>
                  <select
                    value={orderForm.warehouse_id}
                    onChange={(e) => setOrderForm({ ...orderForm, warehouse_id: e.target.value })}
                    className="mt-1.5 w-full rounded-xl border border-input bg-white px-3.5 py-2 text-xs font-bold text-foreground shadow-xs outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 transition-all cursor-pointer"
                  >
                    {warehouses.map((w) => (
                      <option key={w.id} value={w.id}>
                        {w.code} ({w.city || "Hub"}, {w.state || ""})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Seller Order Number
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. SO-2026-9041"
                  value={orderForm.seller_order_number}
                  onChange={(e) =>
                    setOrderForm({ ...orderForm, seller_order_number: e.target.value })
                  }
                  className="mt-1.5 w-full rounded-xl border border-input bg-white px-3.5 py-2 text-xs font-bold text-foreground shadow-xs outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 transition-all"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Customer Full Name
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Jane Doe"
                  value={orderForm.customer_name}
                  onChange={(e) => setOrderForm({ ...orderForm, customer_name: e.target.value })}
                  className="mt-1.5 w-full rounded-xl border border-input bg-white px-3.5 py-2 text-xs font-bold text-foreground shadow-xs outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 transition-all"
                />
              </div>

              {/* Physical Delivery Address */}
              <div className="rounded-xl bg-slate-50 p-3.5 border border-slate-200 space-y-2.5">
                <span className="font-bold text-slate-700 uppercase text-[10px] flex items-center gap-1.5">
                  <Truck className="size-3.5 text-primary" /> Delivery Destination Address
                </span>
                <input
                  type="text"
                  placeholder="Street Address Line 1"
                  value={orderForm.shipping_address_line1}
                  onChange={(e) =>
                    setOrderForm({ ...orderForm, shipping_address_line1: e.target.value })
                  }
                  className="w-full rounded-xl border border-input bg-white px-3 py-1.5 text-xs text-foreground shadow-xs outline-none focus:border-primary focus:ring-2 focus:ring-primary/15"
                />
                <div className="grid grid-cols-3 gap-2">
                  <input
                    type="text"
                    placeholder="City"
                    value={orderForm.city}
                    onChange={(e) => setOrderForm({ ...orderForm, city: e.target.value })}
                    className="rounded-xl border border-input bg-white px-3 py-1.5 text-xs text-foreground shadow-xs outline-none focus:border-primary focus:ring-2 focus:ring-primary/15"
                  />
                  <input
                    type="text"
                    placeholder="State"
                    value={orderForm.state}
                    onChange={(e) => setOrderForm({ ...orderForm, state: e.target.value })}
                    className="rounded-xl border border-input bg-white px-3 py-1.5 text-xs text-foreground shadow-xs outline-none focus:border-primary focus:ring-2 focus:ring-primary/15"
                  />
                  <input
                    type="text"
                    placeholder="ZIP"
                    value={orderForm.postal_code}
                    onChange={(e) => setOrderForm({ ...orderForm, postal_code: e.target.value })}
                    className="rounded-xl border border-input bg-white px-3 py-1.5 text-xs text-foreground shadow-xs outline-none focus:border-primary focus:ring-2 focus:ring-primary/15"
                  />
                </div>
              </div>

              {/* Order Line Builder */}
              <div className="border-t border-slate-200 pt-3">
                <span className="font-bold text-slate-700 uppercase text-[10px]">
                  Add Order Line Items
                </span>
                <div className="mt-2 flex gap-2">
                  <select
                    value={lineForm.product_id}
                    onChange={(e) => setLineForm({ ...lineForm, product_id: e.target.value })}
                    className="flex-1 rounded-xl border border-input bg-white px-3.5 py-2 text-xs font-mono font-bold text-foreground shadow-xs outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 transition-all cursor-pointer"
                  >
                    <option value="">-- Select Product SKU --</option>
                    {createProductOptions.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.sku} — {p.name}
                      </option>
                    ))}
                  </select>
                  <input
                    type="number"
                    min="1"
                    value={lineForm.quantity}
                    onChange={(e) => setLineForm({ ...lineForm, quantity: e.target.value })}
                    className="w-20 rounded-xl border border-input bg-white px-3 py-2 font-mono text-xs font-bold text-foreground text-right outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 shadow-xs"
                  />
                  <Button type="button" variant="secondary" size="sm" onClick={addOrderLine}>
                    Add Line
                  </Button>
                </div>

                {/* Staged Lines List */}
                <div className="mt-3 space-y-1.5">
                  {orderLines.map((line, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between rounded-lg bg-slate-50 p-2 border border-slate-200"
                    >
                      <span className="font-mono font-bold text-slate-900">
                        {productSku(products, line.product_id)}
                      </span>
                      <div className="flex items-center gap-3">
                        <span className="font-mono font-bold text-slate-700">
                          Qty: {line.ordered_quantity}
                        </span>
                        <button
                          type="button"
                          onClick={() => setOrderLines(orderLines.filter((_, i) => i !== idx))}
                          className="text-rose-600 hover:text-rose-800"
                        >
                          ✕
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-6 flex items-center justify-end gap-2 border-t border-slate-100 pt-4">
                <Button
                  type="button"
                  variant="secondary"
                  size="md"
                  onClick={() => setOpenCreate(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="md"
                  disabled={createOrderMutation.isPending}
                >
                  {createOrderMutation.isPending ? "Creating..." : "Save Customer Order"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </AppShell>
  );
}
