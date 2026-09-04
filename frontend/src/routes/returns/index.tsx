import { createFileRoute, Link } from "@tanstack/react-router";
import {
  AlertTriangle,
  Boxes,
  CheckCircle2,
  FileSearch,
  Plus,
  Search,
  ShieldAlert,
  ShieldCheck,
  Trash2,
  Undo2,
} from "lucide-react";
import { useMemo, useRef, useState } from "react";
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
import { productName, productSku, sellerLabel, warehouseLabel } from "@/lib/display";
import { formatDate, formatQty } from "@/lib/format";
import { normalizeSearchQuery } from "@/lib/global-search";
import {
  useCreateReturnMutation,
  useOrdersQuery,
  useProductsQuery,
  useReturnsQuery,
  useSellersQuery,
  useWarehousesQuery,
} from "@/hooks/use-api";
import type { Order, Product, ReturnOrder, Seller, Warehouse } from "@/lib/types";

interface ReturnsSearchParams {
  q?: string;
}

export const Route = createFileRoute("/returns/")({
  validateSearch: (search: Record<string, unknown>): ReturnsSearchParams => {
    const q = normalizeSearchQuery(search["q"]);
    return q ? { q } : {};
  },
  head: () => ({
    meta: [
      { title: "Customer Returns & Inspection | Whitfield Ops" },
      {
        name: "description",
        content:
          "Inbound customer return intake and mandatory physical inspection before restock disposition.",
      },
      { property: "og:title", content: "Customer Returns & Inspection | Whitfield Ops" },
      {
        property: "og:description",
        content:
          "Returned goods enter inspection quarantine and are never posted straight to available.",
      },
    ],
  }),
  component: ReturnsPage,
});

const EMPTY_RETURNS: ReturnOrder[] = [];
const EMPTY_SELLERS: Seller[] = [];
const EMPTY_WAREHOUSES: Warehouse[] = [];
const EMPTY_PRODUCTS: Product[] = [];
const EMPTY_ORDERS: Order[] = [];

interface ReturnLineDraft {
  product_id: string;
  expected_quantity: string;
  received_quantity: string;
  reason_code: string;
  inspection_notes: string;
}

function newReturnLineDraft(): ReturnLineDraft {
  return {
    product_id: "",
    expected_quantity: "1",
    received_quantity: "0",
    reason_code: "CUSTOMER_RETURN",
    inspection_notes: "",
  };
}

function ReturnsPage() {
  const { q } = Route.useSearch();
  const navigate = Route.useNavigate();
  const returnsQuery = useReturnsQuery();
  const sellersQuery = useSellersQuery();
  const warehousesQuery = useWarehousesQuery();
  const productsQuery = useProductsQuery();
  const ordersQuery = useOrdersQuery();
  const createReturnMutation = useCreateReturnMutation();

  const handleSearchChange = (val: string) => {
    navigate({
      search: (prev) => {
        const normalized = normalizeSearchQuery(val);
        if (!normalized) {
          const { q: _, ...rest } = prev;
          return rest;
        }
        return { ...prev, q: normalized };
      },
      replace: true,
    });
  };

  const returns = returnsQuery.data ?? EMPTY_RETURNS;
  const sellers = sellersQuery.data ?? EMPTY_SELLERS;
  const warehouses = warehousesQuery.data ?? EMPTY_WAREHOUSES;
  const products = productsQuery.data ?? EMPTY_PRODUCTS;
  const orders = ordersQuery.data ?? EMPTY_ORDERS;

  const logReturnTriggerRef = useRef<HTMLButtonElement | null>(null);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    seller_id: "",
    warehouse_id: "",
    order_id: "",
    rma_number: "",
    inbound_tracking_number: "",
    is_unidentified: false,
    notes: "",
    lines: [newReturnLineDraft()],
  });

  const awaitingInspection = returns.filter(
    (r: ReturnOrder) => r.status === "INSPECTION" || r.status === "EXPECTED",
  ).length;

  function updateLine(index: number, patch: Partial<ReturnLineDraft>) {
    setForm({
      ...form,
      lines: form.lines.map((line, lineIndex) =>
        lineIndex === index ? { ...line, ...patch } : line,
      ),
    });
  }

  function addLine() {
    setForm({ ...form, lines: [...form.lines, newReturnLineDraft()] });
  }

  function removeLine(index: number) {
    if (form.lines.length === 1) return;
    setForm({
      ...form,
      lines: form.lines.filter((_, lineIndex) => lineIndex !== index),
    });
  }

  async function createReturn(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    const sellerId = form.seller_id || sellers[0]?.id;
    const warehouseId = form.warehouse_id || warehouses[0]?.id;
    if (!sellerId) return setError("Seller is required.");
    if (!warehouseId) return setError("Warehouse facility is required.");
    if (!form.is_unidentified && !form.rma_number.trim()) {
      return setError("RMA number is required for expected returns.");
    }
    if (form.lines.some((l) => !l.product_id || Number(l.expected_quantity) <= 0)) {
      return setError("All lines must specify a product and valid expected quantity.");
    }

    try {
      await createReturnMutation.mutateAsync({
        seller_id: sellerId,
        warehouse_id: warehouseId,
        ...(form.order_id ? { order_id: form.order_id } : {}),
        ...(form.rma_number.trim() ? { rma_number: form.rma_number.trim() } : {}),
        ...(form.inbound_tracking_number.trim()
          ? { inbound_tracking_number: form.inbound_tracking_number.trim() }
          : {}),
        is_unidentified: form.is_unidentified,
        ...(form.notes.trim() ? { notes: form.notes.trim() } : {}),
        lines: form.lines.map((l) => ({
          ...(l.product_id ? { product_id: l.product_id } : {}),
          expected_quantity: Number(l.expected_quantity),
          received_quantity: Number(l.received_quantity || 0),
          ...(l.reason_code.trim() ? { reason_code: l.reason_code.trim() } : {}),
          ...(l.inspection_notes.trim() ? { inspection_notes: l.inspection_notes.trim() } : {}),
        })),
      });
      setOpen(false);
      setForm({
        seller_id: "",
        warehouse_id: "",
        order_id: "",
        rma_number: "",
        inbound_tracking_number: "",
        is_unidentified: false,
        notes: "",
        lines: [newReturnLineDraft()],
      });
      returnsQuery.refetch();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not log customer return.");
    }
  }

  const filteredReturns = useMemo(() => {
    if (!q) return returns;
    const search = q.toLowerCase();
    return returns.filter((r: ReturnOrder) => {
      const retNum = (r.return_number || "").toLowerCase();
      const rma = (r.rma_number || "").toLowerCase();
      const track = (r.inbound_tracking_number || "").toLowerCase();
      const id = (r.id || "").toLowerCase();
      const seller = sellerLabel(sellers, r.seller_id).toLowerCase();
      const warehouse = (
        warehouses.find((w) => w.id === r.warehouse_id)?.code ||
        warehouseLabel(warehouses, r.warehouse_id) ||
        ""
      ).toLowerCase();
      const status = (r.status || "").toLowerCase();
      return (
        retNum.includes(search) ||
        rma.includes(search) ||
        track.includes(search) ||
        id.includes(search) ||
        seller.includes(search) ||
        warehouse.includes(search) ||
        status.includes(search)
      );
    });
  }, [returns, q, sellers, warehouses]);

  return (
    <AppShell>
      <PageHeader
        title="Customer Returns & Quarantine Inspection"
        subtitle="Manage returned stock with mandatory physical inspection before any item re-enters sellable inventory."
        actions={
          <Button
            onClick={(event) => {
              logReturnTriggerRef.current = event.currentTarget;
              setOpen(true);
            }}
            className="gap-2"
          >
            <Plus className="size-4" /> Log Customer Return
          </Button>
        }
      />

      <div className="mb-5 flex items-center gap-2.5 rounded-lg border border-purple-200/80 bg-purple-50/60 px-3.5 py-2 text-xs text-purple-900">
        <ShieldCheck className="size-4 shrink-0 text-purple-600" />
        <span>
          <strong className="font-semibold">Inspection Quarantine Rule:</strong> Returned goods
          never post directly to sellable stock. Every unit enters RETURN_INSPECTION until
          physically vetted by warehouse staff.
        </span>
      </div>

      {awaitingInspection > 0 ? (
        <ExceptionBanner>
          <strong>{awaitingInspection} Return(s) Awaiting Physical Inspection:</strong> Units in
          quarantine dock must be inspected for seal integrity, carton crushing, and defect
          disposition.
        </ExceptionBanner>
      ) : null}

      {[returnsQuery, sellersQuery, warehousesQuery, productsQuery].some((q) => q.isLoading) ? (
        <LoadingState message="Loading returns queue..." />
      ) : null}

      {/* Search Bar */}
      <Card className="mb-5 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="relative flex items-center w-full sm:w-80">
            <Search className="pointer-events-none absolute left-3.5 size-4 text-muted-foreground" />
            <label htmlFor="return-search" className="sr-only">
              Search returns
            </label>
            <input
              id="return-search"
              type="search"
              maxLength={100}
              value={q ?? ""}
              onChange={(e) => handleSearchChange(e.target.value)}
              placeholder="Search return, RMA, tracking number, seller, or facility…"
              className="w-full min-h-[44px] rounded-full border border-input bg-white py-2.5 pr-4 pl-10 font-mono text-sm font-semibold text-foreground outline-none placeholder:font-sans placeholder:font-normal placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/15"
            />
          </div>
        </div>
      </Card>

      {returns.length === 0 ? (
        <Card className="p-8">
          <EmptyState
            message="No customer returns recorded"
            hint="Log an expected RMA or unidentified customer return package above."
          />
        </Card>
      ) : filteredReturns.length === 0 ? (
        <Card className="p-8">
          <EmptyState
            message="No returns match this search"
            hint="Clear or adjust the search query to see other returns."
          />
        </Card>
      ) : (
        <>
          <div data-testid="returns-desktop-table" className="hidden md:block">
            <TableShell>
              <thead>
                <tr>
                  <Th>RMA / Return ID</Th>
                  <Th>Seller Tenant</Th>
                  <Th>Facility</Th>
                  <Th>Type</Th>
                  <Th>Status</Th>
                  <Th>Created Date</Th>
                  <Th className="text-right">Action</Th>
                </tr>
              </thead>
              <tbody>
                {filteredReturns.map((r: ReturnOrder) => {
                  const whCode = warehouses.find((w) => w.id === r.warehouse_id)?.code || "WH";

                  return (
                    <tr key={r.id} className="hover:bg-slate-50">
                      <Td className="font-mono font-bold text-slate-900">
                        <Link
                          to="/returns/$id"
                          params={{ id: r.id }}
                          className="text-blue-600 hover:underline"
                        >
                          {r.rma_number || `RET-${r.id.slice(0, 8)}`}
                        </Link>
                      </Td>
                      <Td className="text-slate-700 font-medium">
                        {sellerLabel(sellers, r.seller_id)}
                      </Td>
                      <Td>
                        <FacilityBadge code={whCode} />
                      </Td>
                      <Td>
                        <span
                          className={`inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-semibold border ${
                            !r.rma_number
                              ? "bg-amber-50 text-amber-800 border-amber-200"
                              : "bg-blue-50 text-blue-800 border-blue-200"
                          }`}
                        >
                          {!r.rma_number ? "Unidentified Drop" : "Expected RMA"}
                        </span>
                      </Td>
                      <Td>
                        <StatusBadge value={r.status} />
                      </Td>
                      <Td className="font-mono text-xs text-slate-500">{formatDate(r.created_at)}</Td>
                      <Td className="text-right">
                        <Link
                          to="/returns/$id"
                          params={{ id: r.id }}
                          className="inline-flex items-center gap-1 rounded-lg bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-800 hover:bg-blue-50 hover:text-blue-700 transition-colors"
                        >
                          Inspect & Dispose
                        </Link>
                      </Td>
                    </tr>
                  );
                })}
              </tbody>
            </TableShell>
          </div>

          <MobileRecordList label="Customer Returns" testId="returns-mobile-list">
            {filteredReturns.map((r: ReturnOrder) => {
              const whCode = warehouses.find((w) => w.id === r.warehouse_id)?.code || "WH";
              const rmaText = r.rma_number || `RET-${r.id.slice(0, 8)}`;
              const isExpected = Boolean(r.rma_number);

              return (
                <MobileRecordCard key={r.id}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="font-mono font-bold text-slate-900 break-all text-sm">
                        {rmaText}
                      </p>
                    </div>
                    <StatusBadge value={r.status} />
                  </div>

                  <dl className="mt-3 grid grid-cols-2 gap-2 text-xs pt-2 border-t border-border">
                    <div>
                      <dt className="text-muted-foreground text-[11px]">Type</dt>
                      <dd className="mt-0.5">
                        <span
                          className={`inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-semibold border ${
                            !isExpected
                              ? "bg-amber-50 text-amber-800 border-amber-200"
                              : "bg-blue-50 text-blue-800 border-blue-200"
                          }`}
                        >
                          {!isExpected ? "Unidentified Drop" : "Expected RMA"}
                        </span>
                      </dd>
                    </div>
                    <div>
                      <dt className="text-muted-foreground text-[11px]">Seller</dt>
                      <dd className="font-medium text-slate-700">{sellerLabel(sellers, r.seller_id)}</dd>
                    </div>
                    <div>
                      <dt className="text-muted-foreground text-[11px]">Facility</dt>
                      <dd className="mt-0.5">
                        <FacilityBadge code={whCode} />
                      </dd>
                    </div>
                    <div>
                      <dt className="text-muted-foreground text-[11px]">Created Date</dt>
                      <dd className="font-mono text-xs text-slate-500 mt-0.5">{formatDate(r.created_at)}</dd>
                    </div>
                  </dl>

                  <div className="mt-4 pt-3 border-t border-border">
                    <Link
                      to="/returns/$id"
                      params={{ id: r.id }}
                      className="min-h-[44px] w-full inline-flex items-center justify-center gap-1 rounded-lg bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-800 hover:bg-blue-50 hover:text-blue-700 transition-colors"
                    >
                      Inspect & Dispose
                    </Link>
                  </div>
                </MobileRecordCard>
              );
            })}
          </MobileRecordList>
        </>
      )}

      {/* Log Return Modal */}
      <AppDialog
        open={open}
        onOpenChange={setOpen}
        title="Log Inbound Customer Return"
        description="Record the related order, facility, return reason, and received item quantities."
        className="max-w-xl"
        pending={createReturnMutation.isPending}
        returnFocusRef={logReturnTriggerRef}
      >
        {error ? (
          <div className="mb-3">
            <ErrorState message={error} />
          </div>
        ) : null}

        <form onSubmit={createReturn} className="space-y-4 text-xs">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                Seller Account
              </label>
              <select
                value={form.seller_id}
                onChange={(e) => setForm({ ...form, seller_id: e.target.value })}
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
                Receiving Facility
              </label>
              <select
                value={form.warehouse_id}
                onChange={(e) => setForm({ ...form, warehouse_id: e.target.value })}
                className="mt-1.5 w-full rounded-xl border border-input bg-white px-3.5 py-2 text-xs font-bold text-foreground shadow-xs outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 transition-all cursor-pointer"
              >
                {warehouses.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.code} ({w.city || "Hub"})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block font-bold text-slate-700 uppercase tracking-wider text-[10px]">
              Carrier Tracking # (Optional)
            </label>
            <input
              type="text"
              placeholder="e.g. 1Z999AA10123456784"
              value={form.inbound_tracking_number}
              onChange={(e) => setForm({ ...form, inbound_tracking_number: e.target.value })}
              className="mt-1.5 w-full rounded-xl border border-input bg-white px-3.5 py-2 text-xs font-bold text-foreground shadow-xs outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 transition-all"
            />
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="unidentified"
              checked={form.is_unidentified}
              onChange={(e) => setForm({ ...form, is_unidentified: e.target.checked })}
              className="rounded border-slate-300"
            />
            <label htmlFor="unidentified" className="text-xs font-semibold text-slate-700">
              Unidentified return package (no prior RMA paperwork)
            </label>
          </div>

          {/* Return Lines */}
          <div className="border-t border-slate-100 pt-3">
            <div className="flex items-center justify-between mb-2">
              <span className="font-bold text-slate-700 uppercase text-[10px]">
                Expected Return Items
              </span>
              <button
                type="button"
                onClick={addLine}
                className="text-xs font-semibold text-primary hover:text-primary-dark cursor-pointer"
              >
                + Add Another SKU
              </button>
            </div>

            <div className="space-y-2.5">
              {form.lines.map((line, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-2 rounded-xl bg-slate-50 p-2.5 border border-slate-200"
                >
                  <select
                    value={line.product_id}
                    onChange={(e) => updateLine(idx, { product_id: e.target.value })}
                    className="flex-1 rounded-xl border border-input bg-white px-3 py-1.5 font-mono text-xs font-bold text-foreground shadow-xs outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 transition-all cursor-pointer"
                  >
                    <option value="">-- Choose Product SKU --</option>
                    {products.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.sku} — {p.name}
                      </option>
                    ))}
                  </select>
                  <input
                    type="number"
                    min="1"
                    value={line.expected_quantity}
                    onChange={(e) => updateLine(idx, { expected_quantity: e.target.value })}
                    placeholder="Qty"
                    className="w-16 rounded-xl border border-input bg-white px-2.5 py-1.5 font-mono text-xs font-bold text-right text-foreground focus:border-primary focus:ring-2 focus:ring-primary/15 outline-none shadow-xs"
                  />
                  <button
                    type="button"
                    onClick={() => removeLine(idx)}
                    className="text-rose-600 hover:text-rose-800 p-1"
                  >
                    <Trash2 className="size-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:items-center sm:justify-end border-t border-slate-100 pt-4">
            <Button
              type="button"
              variant="secondary"
              size="md"
              disabled={createReturnMutation.isPending}
              onClick={() => setOpen(false)}
              className="w-full sm:w-auto"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="md"
              disabled={createReturnMutation.isPending}
              className="w-full sm:w-auto"
            >
              {createReturnMutation.isPending ? "Logging..." : "Log Inbound Return"}
            </Button>
          </div>
        </form>
      </AppDialog>
    </AppShell>
  );
}
