import { createFileRoute, Link } from "@tanstack/react-router";
import {
  AlertTriangle,
  ArrowRight,
  Boxes,
  CheckCircle2,
  PackageCheck,
  Plus,
  Repeat,
  ShieldAlert,
  Trash2,
  Truck,
} from "lucide-react";
import { useState } from "react";
import { AppShell } from "@/components/AppShell";
import { FacilityBadge, StatusBadge } from "@/components/StatusBadge";
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  ExceptionBanner,
  LoadingState,
  PageHeader,
  TableShell,
  Td,
  Th,
} from "@/components/ui-kit";
import { useAuth } from "@/lib/auth";
import { productName, productSku, sellerLabel, warehouseLabel } from "@/lib/display";
import { formatDate, formatQty } from "@/lib/format";
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
import type { Transfer } from "@/lib/types";

export const Route = createFileRoute("/transfers/")({
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
  const { user } = useAuth();
  const transfersQuery = useTransfersQuery();
  const sellersQuery = useSellersQuery();
  const warehousesQuery = useWarehousesQuery();
  const productsQuery = useProductsQuery();

  const transfers = transfersQuery.data ?? [];
  const sellers = sellersQuery.data ?? [];
  const warehouses = warehousesQuery.data ?? [];
  const products = productsQuery.data ?? [];

  const approveMutation = useApproveTransferMutation();
  const dispatchMutation = useDispatchTransferMutation();
  const receiveMutation = useReceiveTransferMutation();
  const resolveMutation = useResolveDiscrepancyMutation();
  const createMutation = useCreateTransferMutation();

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
      alert(err instanceof Error ? err.message : "Failed to approve transfer.");
    }
  }

  async function handleDispatch(id: string) {
    try {
      await dispatchMutation.mutateAsync(id);
      transfersQuery.refetch();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to dispatch transfer.");
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
      alert(err instanceof Error ? err.message : "Failed to receive transfer.");
    }
  }

  async function handleResolve(transfer: Transfer) {
    if (!resolveNotes.trim()) {
      return alert("Manager resolution notes are required.");
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
      alert(err instanceof Error ? err.message : "Failed to resolve discrepancy.");
    }
  }

  return (
    <AppShell>
      <PageHeader
        title="Inter-Facility Transfers (RNO ⇄ CMH)"
        subtitle="Orchestrate stock balancing between Reno and Columbus with in-transit ledger accounting and discrepancy reconciliation."
        actions={
          <Button onClick={() => setOpen(true)} className="gap-2">
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

      {transfers.length === 0 ? (
        <Card className="p-8">
          <EmptyState
            message="No inter-facility transfers recorded"
            hint="Create a stock transfer above to balance inventory between Reno and Columbus."
          />
        </Card>
      ) : (
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
            {transfers.map((t: Transfer) => {
              const originCode =
                warehouses.find((w) => w.id === t.origin_warehouse_id)?.code || "ORIGIN";
              const destCode =
                warehouses.find((w) => w.id === t.destination_warehouse_id)?.code || "DEST";

              return (
                <tr key={t.id} className="hover:bg-slate-50">
                  <Td className="font-mono font-bold text-slate-900">TRF-{t.id.slice(0, 8)}</Td>
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
                          onClick={() => {
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
                        <Button variant="danger" size="sm" onClick={() => setResolving(t)}>
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
      )}

      {/* Create Transfer Modal */}
      {open ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-xs">
          <div className="w-full max-w-xl rounded-xl border border-slate-200 bg-white p-6 shadow-2xl animate-rise max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900 text-base">
                New Inter-Facility Stock Transfer
              </h3>
              <button
                onClick={() => setOpen(false)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 cursor-pointer"
              >
                ✕
              </button>
            </div>

            {error ? (
              <div className="mt-3">
                <ErrorState message={error} />
              </div>
            ) : null}

            <div className="mt-4 space-y-4 text-xs">
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

            <div className="mt-6 flex items-center justify-end gap-2 border-t border-slate-100 pt-4">
              <Button variant="secondary" size="md" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="md"
                onClick={createTransfer}
                disabled={createMutation.isPending}
              >
                {createMutation.isPending ? "Creating..." : "Submit Transfer for Approval"}
              </Button>
            </div>
          </div>
        </div>
      ) : null}

      {/* Receive Transfer Modal */}
      {receiving ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-xs">
          <div className="w-full max-w-lg rounded-xl border border-slate-200 bg-white p-6 shadow-2xl animate-rise">
            <h3 className="font-bold text-slate-900 text-base border-b border-slate-100 pb-3">
              Receive Inter-Facility Transfer (TRF-{receiving.id.slice(0, 8)})
            </h3>
            <p className="mt-2 text-xs text-slate-600">
              Verify incoming quantities at destination dock. Note damaged or missing items
              separately:
            </p>

            <div className="mt-4 space-y-3">
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

            <div className="mt-6 flex items-center justify-end gap-2 border-t border-slate-100 pt-4">
              <Button variant="secondary" size="md" onClick={() => setReceiving(null)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="md"
                onClick={() => handleReceive(receiving)}
                disabled={receiveMutation.isPending}
                className="bg-emerald-600 hover:bg-emerald-700 font-bold"
              >
                {receiveMutation.isPending ? "Posting..." : "Confirm Inbound Receipt"}
              </Button>
            </div>
          </div>
        </div>
      ) : null}

      {/* Resolve Discrepancy Modal */}
      {resolving ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-6 shadow-2xl animate-rise">
            <h3 className="font-bold text-slate-900 text-base border-b border-slate-100 pb-3">
              Manager Transfer Discrepancy Resolution
            </h3>
            <p className="mt-2 text-xs text-slate-600">
              Provide formal operational notes explaining the variance before closing this
              discrepancy:
            </p>
            <textarea
              rows={3}
              value={resolveNotes}
              onChange={(e) => setResolveNotes(e.target.value)}
              placeholder="e.g. Carrier investigation confirmed 2 units lost in transit, insurance claim filed."
              className="mt-3 w-full rounded-lg border border-slate-300 p-2.5 text-xs text-slate-800 focus:outline-none"
            />
            <div className="mt-4 flex items-center justify-end gap-2">
              <Button variant="secondary" size="md" onClick={() => setResolving(null)}>
                Cancel
              </Button>
              <Button
                variant="danger"
                size="md"
                onClick={() => handleResolve(resolving)}
                disabled={resolveMutation.isPending}
              >
                {resolveMutation.isPending ? "Resolving..." : "Close Discrepancy"}
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </AppShell>
  );
}
