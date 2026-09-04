import { createFileRoute, Link } from "@tanstack/react-router";
import {
  AlertTriangle,
  ArrowRight,
  Boxes,
  CheckCircle2,
  PackageCheck,
  Plus,
  Repeat,
  Search,
  ShieldAlert,
  Trash2,
  Truck,
} from "lucide-react";
import { useMemo, useRef, useState } from "react";
import { toast } from "sonner";
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
import { useAuth } from "@/lib/auth";
import { productName, productSku, sellerLabel, warehouseLabel } from "@/lib/display";
import { formatDate, formatQty } from "@/lib/format";
import { normalizeSearchQuery } from "@/lib/global-search";
import {
  useApproveTransferMutation,
  useCreateTransferMutation,
  useDispatchTransferMutation,
  useProductsQuery,
  useReceiveTransferMutation,
  useResolveDiscrepancyMutation,
  useSellersQuery,
  useTransfersQuery,
  useWarehousesQuery,
} from "@/hooks/use-api";
import type { Product, Seller, Transfer, Warehouse } from "@/lib/types";

interface TransfersSearchParams {
  q?: string;
}

export const Route = createFileRoute("/transfers/")({
  validateSearch: (search: Record<string, unknown>): TransfersSearchParams => {
    const q = normalizeSearchQuery(search["q"]);
    return q ? { q } : {};
  },
  head: () => ({
    meta: [
      { title: "Inter-Facility Transfers | Whitfield Ops" },
      {
        name: "description",
        content:
          "Stock balancing and transfer pipelines between Reno (RNO) and Columbus (CMH) warehouses.",
      },
      { property: "og:title", content: "Inter-Facility Transfers | Whitfield Ops" },
      {
        property: "og:description",
        content: "Multi-facility stock transfer with in-transit tracking and discrepancy review.",
      },
    ],
  }),
  component: TransfersPage,
});

const EMPTY_TRANSFERS: Transfer[] = [];
const EMPTY_SELLERS: Seller[] = [];
const EMPTY_WAREHOUSES: Warehouse[] = [];
const EMPTY_PRODUCTS: Product[] = [];

interface TransferLineDraft {
  product_id: string;
  quantity: string;
  notes: string;
}

function newLineDraft(): TransferLineDraft {
  return {
    product_id: "",
    quantity: "10",
    notes: "",
  };
}

function TransfersPage() {
  const { q } = Route.useSearch();
  const navigate = Route.useNavigate();
  const { user } = useAuth();
  const transfersQuery = useTransfersQuery();
  const sellersQuery = useSellersQuery();
  const warehousesQuery = useWarehousesQuery();
  const productsQuery = useProductsQuery();

  const transfers = transfersQuery.data ?? EMPTY_TRANSFERS;
  const sellers = sellersQuery.data ?? EMPTY_SELLERS;
  const warehouses = warehousesQuery.data ?? EMPTY_WAREHOUSES;
  const products = productsQuery.data ?? EMPTY_PRODUCTS;

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

  const approveMutation = useApproveTransferMutation();
  const dispatchMutation = useDispatchTransferMutation();
  const receiveMutation = useReceiveTransferMutation();
  const resolveMutation = useResolveDiscrepancyMutation();
  const createMutation = useCreateTransferMutation();

  const createTransferTriggerRef = useRef<HTMLButtonElement | null>(null);
  const receiveTransferTriggerRef = useRef<HTMLButtonElement | null>(null);
  const resolveDiscrepancyTriggerRef = useRef<HTMLButtonElement | null>(null);
  const [open, setOpen] = useState(false);
  const [receiving, setReceiving] = useState<Transfer | null>(null);
  const [resolving, setResolving] = useState<Transfer | null>(null);
  const [resolveNotes, setResolveNotes] = useState("");
  const [receiveLines, setReceiveLines] = useState<
    Record<string, { good: string; damaged: string }>
  >({});
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    seller_id: "",
    origin_warehouse_id: "",
    destination_warehouse_id: "",
    notes: "",
    lines: [newLineDraft()],
  });

  const discrepancies = transfers.filter((t) => t.status === "DISCREPANCY_REVIEW").length;
  const pendingApprovals = transfers.filter((t) => t.status === "PENDING_APPROVAL").length;
  const inTransitCount = transfers.filter((t) => t.status === "DISPATCHED").length;
  const isManager = user?.role === "WAREHOUSE_MANAGER" || user?.role === "ADMINISTRATOR";

  function addLine() {
    setForm({ ...form, lines: [...form.lines, newLineDraft()] });
  }

  function updateLine(index: number, patch: Partial<TransferLineDraft>) {
    setForm({
      ...form,
      lines: form.lines.map((line, lineIndex) =>
        lineIndex === index ? { ...line, ...patch } : line,
      ),
    });
  }

  function removeLine(index: number) {
    if (form.lines.length === 1) return;
    setForm({
      ...form,
      lines: form.lines.filter((_, lineIndex) => lineIndex !== index),
    });
  }

  async function createTransfer() {
    setError(null);
    const sellerId = form.seller_id || sellers[0]?.id;
    const originWarehouseId = form.origin_warehouse_id || warehouses[0]?.id;
    const destinationWarehouseId = form.destination_warehouse_id || warehouses[1]?.id;

    if (!sellerId) return setError("Seller is required.");
    if (!originWarehouseId || !destinationWarehouseId)
      return setError("Both origin and destination facilities are required.");
    if (originWarehouseId === destinationWarehouseId) {
      return setError("Origin and destination facilities must be different.");
    }
    if (form.lines.some((l) => !l.product_id || Number(l.quantity) <= 0)) {
      return setError("All lines must specify a valid product and quantity greater than 0.");
    }

    try {
      await createMutation.mutateAsync({
        seller_id: sellerId,
        origin_warehouse_id: originWarehouseId,
        destination_warehouse_id: destinationWarehouseId,
        ...(form.notes.trim() ? { notes: form.notes.trim() } : {}),
        lines: form.lines.map((l) => ({
          product_id: l.product_id,
          requested_quantity: Number(l.quantity),
          ...(l.notes.trim() ? { notes: l.notes.trim() } : {}),
        })),
      });
      setOpen(false);
      setForm({
        seller_id: "",
        origin_warehouse_id: "",
        destination_warehouse_id: "",
        notes: "",
        lines: [newLineDraft()],
      });
      transfersQuery.refetch();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not create transfer.");
    }
  }

  async function handleApprove(id: string) {
    try {
      await approveMutation.mutateAsync(id);
      transfersQuery.refetch();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to approve transfer.");
    }
  }

  async function handleDispatch(id: string) {
    try {
      await dispatchMutation.mutateAsync(id);
      transfersQuery.refetch();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to dispatch transfer.");
    }
  }

  async function handleReceive(transfer: Transfer) {
    try {
      await receiveMutation.mutateAsync({
        id: transfer.id,
        lines: transfer.lines.map((l) => ({
          line_id: l.id,
          received_good_quantity: Number(receiveLines[l.id]?.good ?? l.requested_quantity),
          received_damaged_quantity: Number(receiveLines[l.id]?.damaged ?? 0),
        })),
      });
      setReceiving(null);
      setReceiveLines({});
      transfersQuery.refetch();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to receive transfer.");
    }
  }

  async function handleResolve(transfer: Transfer) {
    if (!resolveNotes.trim()) {
      toast.error("Manager resolution notes are required.");
      return;
    }
    try {
      await resolveMutation.mutateAsync({
        id: transfer.id,
        notes: resolveNotes.trim(),
      });
      setResolving(null);
      setResolveNotes("");
      transfersQuery.refetch();
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to resolve discrepancy.");
    }
  }

  const filteredTransfers = useMemo(() => {
    if (!q) return transfers;
    const search = q.toLowerCase();
    return transfers.filter((t: Transfer) => {
      const num = (t.transfer_number || "").toLowerCase();
      const synthetic = `trf-${t.id.slice(0, 8)}`.toLowerCase();
      const id = (t.id || "").toLowerCase();
      const origin = (
        warehouses.find((w) => w.id === t.origin_warehouse_id)?.code || ""
      ).toLowerCase();
      const dest = (
        warehouses.find((w) => w.id === t.destination_warehouse_id)?.code || ""
      ).toLowerCase();
      const seller = sellerLabel(sellers, t.seller_id).toLowerCase();
      const status = (t.status || "").toLowerCase();
      return (
        num.includes(search) ||
        synthetic.includes(search) ||
        id.includes(search) ||
        origin.includes(search) ||
        dest.includes(search) ||
        seller.includes(search) ||
        status.includes(search)
      );
    });
  }, [transfers, q, warehouses, sellers]);

  return (
    <AppShell>
      <PageHeader
        title="Inter-Facility Transfers (RNO ⇄ CMH)"
        subtitle="Orchestrate stock balancing between Reno and Columbus with in-transit ledger accounting and discrepancy reconciliation."
        actions={
          <Button
            onClick={(event) => {
              createTransferTriggerRef.current = event.currentTarget;
              setOpen(true);
            }}
            className="gap-2"
          >
            <Plus className="size-4" /> Create Stock Transfer
          </Button>
        }
      />

      {discrepancies > 0 ? (
        <ExceptionBanner>
          <strong>{discrepancies} Transfer Discrepancy(ies) Active:</strong> Quantity received did
          not match dispatched count. Manager review required to adjust ledger variances.
        </ExceptionBanner>
      ) : null}

      {[transfersQuery, sellersQuery, warehousesQuery, productsQuery].some((q) => q.isLoading) ? (
        <LoadingState message="Loading inter-facility transfers..." />
      ) : null}

      {/* Metric Cards */}
      <div className="mb-5 grid gap-3.5 sm:grid-cols-3">
        <Card className="border-l-4 border-l-amber-500 p-4">
          <span className="text-[10px] font-bold text-amber-800 uppercase tracking-wider">
            Pending Manager Approval
          </span>
          <p className="mt-1 font-mono text-2xl font-extrabold text-amber-900">
            {pendingApprovals}
          </p>
          <p className="mt-1 text-[11px] text-slate-500">Requires authorization</p>
        </Card>

        <Card className="border-l-4 border-l-blue-600 p-4">
          <span className="text-[10px] font-bold text-blue-800 uppercase tracking-wider">
            In-Transit (RNO ⇄ CMH)
          </span>
          <p className="mt-1 font-mono text-2xl font-extrabold text-blue-900">{inTransitCount}</p>
          <p className="mt-1 text-[11px] text-slate-500">Tracked on IN_TRANSIT ledger</p>
        </Card>

        <Card className="border-l-4 border-l-purple-600 p-4">
          <span className="text-[10px] font-bold text-purple-800 uppercase tracking-wider">
            Discrepancy Review Queue
          </span>
          <p className="mt-1 font-mono text-2xl font-extrabold text-purple-900">{discrepancies}</p>
          <p className="mt-1 text-[11px] text-slate-500">Variance investigation</p>
        </Card>
      </div>

      {/* Search Bar */}
      <Card className="mb-5 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="relative flex items-center w-full sm:w-80">
            <Search className="pointer-events-none absolute left-3.5 size-4 text-muted-foreground" />
            <label htmlFor="transfer-search" className="sr-only">
              Search transfers
            </label>
            <input
              id="transfer-search"
              type="search"
              maxLength={100}
              value={q ?? ""}
              onChange={(e) => handleSearchChange(e.target.value)}
              placeholder="Search transfer number, route, seller, or status…"
              className="w-full min-h-[44px] rounded-full border border-input bg-white py-2.5 pr-4 pl-10 font-mono text-sm font-semibold text-foreground outline-none placeholder:font-sans placeholder:font-normal placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/15"
            />
          </div>
        </div>
      </Card>

      {transfers.length === 0 ? (
        <Card className="p-8">
          <EmptyState
            message="No inter-facility transfers recorded"
            hint="Create a stock transfer above to balance inventory between Reno and Columbus."
          />
        </Card>
      ) : filteredTransfers.length === 0 ? (
        <Card className="p-8">
          <EmptyState
            message="No transfers match this search"
            hint="Clear or adjust the search query to see other transfers."
          />
        </Card>
      ) : (
        <>
          <div data-testid="transfers-desktop-table" className="hidden md:block">
            <TableShell>
              <thead>
                <tr>
                  <Th>Transfer ID</Th>
                  <Th>Route</Th>
                  <Th>Seller Tenant</Th>
                  <Th>Items</Th>
                  <Th>Status</Th>
                  <Th>Created Date</Th>
                  <Th className="text-right">Actions</Th>
                </tr>
              </thead>
              <tbody>
                {filteredTransfers.map((t: Transfer) => {
                  const originCode =
                    warehouses.find((w) => w.id === t.origin_warehouse_id)?.code || "ORIGIN";
                  const destCode =
                    warehouses.find((w) => w.id === t.destination_warehouse_id)?.code || "DEST";

                  return (
                    <tr key={t.id} className="hover:bg-slate-50">
                      <Td className="font-mono font-bold text-slate-900">
                        {t.transfer_number || `TRF-${t.id.slice(0, 8)}`}
                      </Td>
                      <Td>
                        <div className="flex items-center gap-1.5 font-mono text-xs font-semibold">
                          <span className="text-slate-800">{originCode}</span>
                          <ArrowRight className="size-3 text-slate-400" />
                          <span className="text-slate-800">{destCode}</span>
                        </div>
                      </Td>
                      <Td className="text-slate-700 font-medium">
                        {sellerLabel(sellers, t.seller_id)}
                      </Td>
                      <Td className="font-mono font-semibold text-slate-900">
                        {t.lines?.length || 0} SKUs
                      </Td>
                      <Td>
                        <StatusBadge value={t.status} />
                      </Td>
                      <Td className="font-mono text-xs text-slate-500">{formatDate(t.created_at)}</Td>
                      <Td className="text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {t.status === "PENDING_APPROVAL" && isManager ? (
                            <Button
                              variant="primary"
                              size="sm"
                              onClick={() => handleApprove(t.id)}
                              disabled={approveMutation.isPending}
                            >
                              Approve
                            </Button>
                          ) : null}

                          {t.status === "APPROVED" ? (
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => handleDispatch(t.id)}
                              disabled={dispatchMutation.isPending}
                            >
                              Dispatch
                            </Button>
                          ) : null}

                          {t.status === "DISPATCHED" ? (
                            <Button
                              variant="primary"
                              size="sm"
                              onClick={(event) => {
                                receiveTransferTriggerRef.current = event.currentTarget;
                                setReceiving(t);
                                const initial: Record<string, { good: string; damaged: string }> = {};
                                t.lines?.forEach((l) => {
                                  initial[l.id] = { good: String(l.requested_quantity), damaged: "0" };
                                });
                                setReceiveLines(initial);
                              }}
                            >
                              Receive Dock
                            </Button>
                          ) : null}

                          {t.status === "DISCREPANCY_REVIEW" && isManager ? (
                            <Button
                              variant="danger"
                              size="sm"
                              onClick={(event) => {
                                resolveDiscrepancyTriggerRef.current = event.currentTarget;
                                setResolving(t);
                              }}
                            >
                              Resolve Discrepancy
                            </Button>
                          ) : null}
                        </div>
                      </Td>
                    </tr>
                  );
                })}
              </tbody>
            </TableShell>
          </div>

          <MobileRecordList label="Inter-facility Transfers" testId="transfers-mobile-list">
            {filteredTransfers.map((t: Transfer) => {
              const originCode =
                warehouses.find((w) => w.id === t.origin_warehouse_id)?.code || "ORIGIN";
              const destCode =
                warehouses.find((w) => w.id === t.destination_warehouse_id)?.code || "DEST";
              const hasAction =
                (t.status === "PENDING_APPROVAL" && isManager) ||
                t.status === "APPROVED" ||
                t.status === "DISPATCHED" ||
                (t.status === "DISCREPANCY_REVIEW" && isManager);

              return (
                <MobileRecordCard key={t.id}>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="font-mono font-bold text-slate-900 break-all text-sm">
                        {t.transfer_number || `TRF-${t.id.slice(0, 8)}`}
                      </p>
                    </div>
                    <StatusBadge value={t.status} />
                  </div>

                  <dl className="mt-3 grid grid-cols-2 gap-2 text-xs pt-2 border-t border-border">
                    <div className="col-span-2">
                      <dt className="text-muted-foreground text-[11px]">Route</dt>
                      <dd className="mt-0.5 flex items-center gap-1.5 font-mono text-xs font-semibold">
                        <span className="text-slate-800">{originCode}</span>
                        <ArrowRight className="size-3 text-slate-400" />
                        <span className="text-slate-800">{destCode}</span>
                      </dd>
                    </div>
                    <div>
                      <dt className="text-muted-foreground text-[11px]">Seller</dt>
                      <dd className="font-medium text-slate-700">{sellerLabel(sellers, t.seller_id)}</dd>
                    </div>
                    <div>
                      <dt className="text-muted-foreground text-[11px]">Items</dt>
                      <dd className="font-mono font-semibold text-slate-900">{t.lines?.length || 0} SKUs</dd>
                    </div>
                    <div>
                      <dt className="text-muted-foreground text-[11px]">Created Date</dt>
                      <dd className="font-mono text-xs text-slate-500 mt-0.5">{formatDate(t.created_at)}</dd>
                    </div>
                  </dl>

                  {hasAction ? (
                    <div className="mt-4 flex flex-wrap items-center gap-2 pt-3 border-t border-border">
                      {t.status === "PENDING_APPROVAL" && isManager ? (
                        <Button
                          variant="primary"
                          size="sm"
                          className="min-h-[44px] flex-1"
                          onClick={() => handleApprove(t.id)}
                          disabled={approveMutation.isPending}
                        >
                          Approve
                        </Button>
                      ) : null}

                      {t.status === "APPROVED" ? (
                        <Button
                          variant="secondary"
                          size="sm"
                          className="min-h-[44px] flex-1"
                          onClick={() => handleDispatch(t.id)}
                          disabled={dispatchMutation.isPending}
                        >
                          Dispatch
                        </Button>
                      ) : null}

                      {t.status === "DISPATCHED" ? (
                        <Button
                          variant="primary"
                          size="sm"
                          className="min-h-[44px] flex-1"
                          onClick={(event) => {
                            receiveTransferTriggerRef.current = event.currentTarget;
                            setReceiving(t);
                            const initial: Record<string, { good: string; damaged: string }> = {};
                            t.lines?.forEach((l) => {
                              initial[l.id] = { good: String(l.requested_quantity), damaged: "0" };
                            });
                            setReceiveLines(initial);
                          }}
                        >
                          Receive Dock
                        </Button>
                      ) : null}

                      {t.status === "DISCREPANCY_REVIEW" && isManager ? (
                        <Button
                          variant="danger"
                          size="sm"
                          className="min-h-[44px] flex-1"
                          onClick={(event) => {
                            resolveDiscrepancyTriggerRef.current = event.currentTarget;
                            setResolving(t);
                          }}
                        >
                          Resolve Discrepancy
                        </Button>
                      ) : null}
                    </div>
                  ) : null}
                </MobileRecordCard>
              );
            })}
          </MobileRecordList>
        </>
      )}

      {/* Create Transfer Modal */}
      <AppDialog
        open={open}
        onOpenChange={setOpen}
        title="New Inter-Facility Stock Transfer"
        description="Define the origin, destination, seller, and stock lines for this transfer."
        className="max-w-xl"
        pending={createMutation.isPending}
        returnFocusRef={createTransferTriggerRef}
      >
        {error ? (
          <div className="mb-3">
            <ErrorState message={error} />
          </div>
        ) : null}

        <div className="space-y-4 text-xs">
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

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                Origin Facility
              </label>
              <select
                value={form.origin_warehouse_id}
                onChange={(e) => setForm({ ...form, origin_warehouse_id: e.target.value })}
                className="mt-1.5 w-full rounded-xl border border-input bg-white px-3.5 py-2 text-xs font-bold text-foreground shadow-xs outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 transition-all cursor-pointer"
              >
                {warehouses.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.code} ({w.city || "Hub"})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                Destination Facility
              </label>
              <select
                value={form.destination_warehouse_id}
                onChange={(e) => setForm({ ...form, destination_warehouse_id: e.target.value })}
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

          {/* Transfer Lines */}
          <div className="border-t border-slate-100 pt-3">
            <div className="flex items-center justify-between mb-2">
              <span className="font-bold text-slate-700 uppercase text-[10px]">
                Transfer Items
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
                    value={line.quantity}
                    onChange={(e) => updateLine(idx, { quantity: e.target.value })}
                    className="w-20 rounded-md border border-slate-300 bg-white px-2 py-1.5 font-mono text-xs font-bold text-right text-slate-900 focus:outline-none"
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
        </div>

        <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:items-center sm:justify-end border-t border-slate-100 pt-4">
          <Button
            type="button"
            variant="secondary"
            size="md"
            disabled={createMutation.isPending}
            onClick={() => setOpen(false)}
            className="w-full sm:w-auto"
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="primary"
            size="md"
            onClick={createTransfer}
            disabled={createMutation.isPending}
            className="w-full sm:w-auto"
          >
            {createMutation.isPending ? "Creating..." : "Submit Transfer for Approval"}
          </Button>
        </div>
      </AppDialog>

      {/* Receive Transfer Modal */}
      <AppDialog
        open={Boolean(receiving)}
        onOpenChange={(next) => {
          if (!next) setReceiving(null);
        }}
        title={`Receive Inter-Facility Transfer (TRF-${receiving ? receiving.id.slice(0, 8) : ""})`}
        description="Verify incoming quantities and record damaged or missing stock separately."
        className="max-w-lg"
        pending={receiveMutation.isPending}
        returnFocusRef={receiveTransferTriggerRef}
      >
        {receiving ? (
          <div>
            <div className="space-y-3">
              {receiving.lines?.map((line) => {
                const sku = productSku(products, line.product_id);
                const good = receiveLines[line.id]?.good ?? String(line.requested_quantity);
                const damaged = receiveLines[line.id]?.damaged ?? "0";

                return (
                  <div
                    key={line.id}
                    className="rounded-lg bg-slate-50 p-3 border border-slate-200 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-slate-900">{sku}</span>
                      <span className="font-mono text-slate-600">
                        Dispatched: {line.requested_quantity}
                      </span>
                    </div>

                    <div className="mt-2.5 grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-[10px] font-bold text-emerald-800 uppercase">
                          Good (Available)
                        </label>
                        <input
                          type="number"
                          min="0"
                          value={good}
                          onChange={(e) =>
                            setReceiveLines({
                              ...receiveLines,
                              [line.id]: { good: e.target.value, damaged },
                            })
                          }
                          className="mt-0.5 w-full rounded-md border border-emerald-300 bg-white px-2 py-1 font-mono text-xs font-bold text-right"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] font-bold text-rose-800 uppercase">
                          Damaged / Transit Loss
                        </label>
                        <input
                          type="number"
                          min="0"
                          value={damaged}
                          onChange={(e) =>
                            setReceiveLines({
                              ...receiveLines,
                              [line.id]: { good, damaged: e.target.value },
                            })
                          }
                          className="mt-0.5 w-full rounded-md border border-rose-300 bg-white px-2 py-1 font-mono text-xs font-bold text-right"
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:items-center sm:justify-end border-t border-slate-100 pt-4">
              <Button
                type="button"
                variant="secondary"
                size="md"
                disabled={receiveMutation.isPending}
                onClick={() => setReceiving(null)}
                className="w-full sm:w-auto"
              >
                Cancel
              </Button>
              <Button
                type="button"
                variant="primary"
                size="md"
                onClick={() => handleReceive(receiving)}
                disabled={receiveMutation.isPending}
                className="bg-emerald-600 hover:bg-emerald-700 font-bold w-full sm:w-auto"
              >
                {receiveMutation.isPending ? "Posting..." : "Confirm Inbound Receipt"}
              </Button>
            </div>
          </div>
        ) : null}
      </AppDialog>

      {/* Resolve Discrepancy Modal */}
      <AppDialog
        open={Boolean(resolving)}
        onOpenChange={(next) => {
          if (!next) {
            setResolving(null);
            setResolveNotes("");
          }
        }}
        title="Manager Transfer Discrepancy Resolution"
        description="Provide formal operational notes explaining the variance before closing this discrepancy."
        className="max-w-md"
        pending={resolveMutation.isPending}
        returnFocusRef={resolveDiscrepancyTriggerRef}
      >
        {resolving ? (
          <div>
            <textarea
              rows={3}
              value={resolveNotes}
              onChange={(e) => setResolveNotes(e.target.value)}
              placeholder="e.g. Carrier investigation confirmed 2 units lost in transit, insurance claim filed."
              className="w-full rounded-lg border border-slate-300 p-2.5 text-xs text-slate-800 focus:outline-none"
            />
            <div className="mt-4 flex flex-col-reverse gap-2 sm:flex-row sm:items-center sm:justify-end">
              <Button
                type="button"
                variant="secondary"
                size="md"
                disabled={resolveMutation.isPending}
                onClick={() => {
                  setResolving(null);
                  setResolveNotes("");
                }}
                className="w-full sm:w-auto"
              >
                Cancel
              </Button>
              <Button
                type="button"
                variant="danger"
                size="md"
                onClick={() => handleResolve(resolving)}
                disabled={resolveMutation.isPending}
                className="w-full sm:w-auto"
              >
                {resolveMutation.isPending ? "Resolving..." : "Close Discrepancy"}
              </Button>
            </div>
          </div>
        ) : null}
      </AppDialog>
    </AppShell>
  );
}
