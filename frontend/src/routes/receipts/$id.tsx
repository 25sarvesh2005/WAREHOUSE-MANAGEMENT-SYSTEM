import { createFileRoute, Link } from "@tanstack/react-router";
import {
  AlertTriangle,
  ArrowLeft,
  Barcode,
  CalendarDays,
  CheckCircle2,
  Database,
  Hash,
  Layers,
  Mic,
  PackageCheck,
  Plus,
  ShieldAlert,
  ShieldCheck,
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
  DuplicateProtectionBanner,
  EmptyState,
  ErrorState,
  LedgerNoticeBanner,
  LoadingState,
  PageHeader,
  ScannerInputField,
  TableShell,
  Td,
  Th,
} from "@/components/ui-kit";
import { useAuth } from "@/lib/auth";
import { productName, productSku, toReceiptEvent, toReceiptLineItem } from "@/lib/display";
import { formatDate, formatQty } from "@/lib/format";
import {
  useCancelReceiptMutation,
  useCompleteReceiptMutation,
  useOverrideDuplicateReceiptMutation,
  useProductsQuery,
  useReceiptQuery,
  useSaveReceiptLineMutation,
  useWarehousesQuery,
} from "@/hooks/use-api";
import { ReceivingVoiceDraftPanel } from "@/components/ReceivingVoiceDraftPanel";
import type { Product, VoiceParsedLine } from "@/lib/types";

const EMPTY_PRODUCTS: Product[] = [];

export const Route = createFileRoute("/receipts/$id")({
  head: () => ({
    meta: [
      { title: "Inbound Receipt Dock Station | Whitfield Ops" },
      {
        name: "description",
        content:
          "Dock barcode scanning, physical condition separation, and voice-assisted receiving draft intake.",
      },
      { property: "og:title", content: "Inbound Receipt Dock Station | Whitfield Ops" },
      {
        property: "og:description",
        content: "Dock-to-stock physical receiving with ledger verification.",
      },
    ],
  }),
  component: ReceiptDetail,
});

function ReceiptDetail() {
  const { id } = Route.useParams();
  const receiptQuery = useReceiptQuery(id);
  const productsQuery = useProductsQuery();
  const warehousesQuery = useWarehousesQuery();
  const { user } = useAuth();
  const completeReceiptMutation = useCompleteReceiptMutation();
  const saveReceiptLineMutation = useSaveReceiptLineMutation();
  const overrideDuplicateMutation = useOverrideDuplicateReceiptMutation();
  const cancelReceiptMutation = useCancelReceiptMutation();

  const receipt = receiptQuery.data;
  const products = productsQuery.data ?? EMPTY_PRODUCTS;
  const warehouses = warehousesQuery.data ?? [];

  const [lineForm, setLineForm] = useState({
    product_id: "",
    expected_quantity: "0",
    sellable_quantity: "1",
    damaged_quantity: "0",
    quarantined_quantity: "0",
    notes: "",
  });
  const [lineError, setLineError] = useState<string | null>(null);
  const [overrideForm, setOverrideForm] = useState({
    original_receipt_id: "",
    override_reason: "",
  });
  const [overrideError, setOverrideError] = useState<string | null>(null);
  const [skuSearch, setSkuSearch] = useState("");
  const [cancelError, setCancelError] = useState<string | null>(null);

  const productOptions = useMemo(
    () => products.filter((product) => !receipt || product.seller_id === receipt.seller_id),
    [products, receipt],
  );

  const filteredLines = useMemo(() => {
    if (!receipt?.lines) return [];
    if (!skuSearch.trim()) return receipt.lines;
    const term = skuSearch.toLowerCase().trim();
    return receipt.lines.filter((line) => {
      const sku = productSku(products, line.product_id).toLowerCase();
      return sku.includes(term);
    });
  }, [receipt?.lines, products, skuSearch]);

  if (receiptQuery.isLoading) {
    return (
      <AppShell>
        <LoadingState message="Loading inbound receipt dock station..." />
      </AppShell>
    );
  }

  if (receiptQuery.isError || !receipt) {
    return (
      <AppShell>
        <ErrorState
          message="Inbound receipt not found or inaccessible."
          onRetry={() => receiptQuery.refetch()}
        />
        <Link
          to="/receipts"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-blue-600 hover:text-blue-800"
        >
          <ArrowLeft className="size-3.5" /> Back to Receiving Queue
        </Link>
      </AppShell>
    );
  }

  const isDraft = receipt.status === "DRAFT";
  const isCompleted = receipt.status === "COMPLETED";
  const isManager = user?.role === "WAREHOUSE_MANAGER" || user?.role === "ADMINISTRATOR";
  const whCode = warehouses.find((w) => w.id === receipt.warehouse_id)?.code || "WH";

  const totalSellable =
    receipt.lines?.reduce((sum, l) => sum + Number(l.sellable_quantity || 0), 0) || 0;
  const totalDamaged =
    receipt.lines?.reduce((sum, l) => sum + Number(l.damaged_quantity || 0), 0) || 0;
  const totalQuarantined =
    receipt.lines?.reduce((sum, l) => sum + Number(l.quarantined_quantity || 0), 0) || 0;

  async function handleSaveLine(e?: React.FormEvent) {
    if (e) e.preventDefault();
    if (!lineForm.product_id) {
      return setLineError("Please scan or select a product SKU.");
    }
    const sellable = Number(lineForm.sellable_quantity) || 0;
    const damaged = Number(lineForm.damaged_quantity) || 0;
    const quarantined = Number(lineForm.quarantined_quantity) || 0;

    if (sellable <= 0 && damaged <= 0 && quarantined <= 0) {
      return setLineError(
        "Total received units (sellable, damaged, or quarantined) must be greater than 0.",
      );
    }

    setLineError(null);
    try {
      await saveReceiptLineMutation.mutateAsync({
        receiptId: receipt!.id,
        line: {
          product_id: lineForm.product_id,
          expected_quantity: Number(lineForm.expected_quantity) || 0,
          sellable_quantity: sellable,
          damaged_quantity: damaged,
          quarantined_quantity: quarantined,
          ...(lineForm.notes.trim() ? { notes: lineForm.notes.trim() } : {}),
        },
      });

      // Reset form for next scanned SKU
      setLineForm({
        product_id: "",
        expected_quantity: "0",
        sellable_quantity: "1",
        damaged_quantity: "0",
        quarantined_quantity: "0",
        notes: "",
      });
      receiptQuery.refetch();
    } catch (err: unknown) {
      setLineError(err instanceof Error ? err.message : "Failed to save receipt line.");
    }
  }

  async function handleVoiceApply(parsedLines: VoiceParsedLine[]) {
    // Map parsed quantities into line items
    let sellable = 0;
    let damaged = 0;
    let quarantined = 0;
    const notes: string[] = [];

    parsedLines.forEach((line) => {
      const q = Number(line.quantity) || 0;
      if (line.inventory_state === "AVAILABLE") sellable += q;
      else if (line.inventory_state === "DAMAGED") damaged += q;
      else if (line.inventory_state === "QUARANTINED") quarantined += q;
      if (line.condition_note) notes.push(line.condition_note);
    });

    setLineForm((prev) => ({
      ...prev,
      sellable_quantity: sellable.toString(),
      damaged_quantity: damaged.toString(),
      quarantined_quantity: quarantined.toString(),
      notes: notes.join("; "),
    }));
  }

  async function handleCompleteReceipt() {
    if (!receipt?.lines || receipt.lines.length === 0) {
      return alert("Please scan and log at least one receipt line before completing.");
    }
    const confirmed = window.confirm(
      `Post ${totalSellable} sellable, ${totalDamaged} damaged, and ${totalQuarantined} quarantined units to the immutable inventory ledger? This action cannot be reversed.`,
    );
    if (!confirmed) return;

    try {
      await completeReceiptMutation.mutateAsync(receipt.id);
      receiptQuery.refetch();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Could not complete receipt.");
    }
  }

  async function handleOverrideDuplicate() {
    if (!overrideForm.override_reason.trim()) {
      return setOverrideError("Manager override justification is required.");
    }
    setOverrideError(null);
    try {
      await overrideDuplicateMutation.mutateAsync({
        receiptId: receipt!.id,
        override: {
          original_receipt_id: overrideForm.original_receipt_id.trim() || "",
          override_reason: overrideForm.override_reason.trim(),
        },
      });
      receiptQuery.refetch();
    } catch (err: unknown) {
      setOverrideError(err instanceof Error ? err.message : "Failed to override duplicate.");
    }
  }

  async function handleCancelReceipt() {
    const confirmed = window.confirm(
      "Cancel this draft receipt? No inventory movements will be posted.",
    );
    if (!confirmed) return;

    try {
      await cancelReceiptMutation.mutateAsync(receipt!.id);
      receiptQuery.refetch();
    } catch (err: unknown) {
      setCancelError(err instanceof Error ? err.message : "Failed to cancel receipt.");
    }
  }

  return (
    <AppShell>
      {/* Top Breadcrumb & Actions Bar */}
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 pb-3">
        <Link
          to="/receipts"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-blue-600 transition-colors"
        >
          <ArrowLeft className="size-3.5" /> Back to Inbound Dock Queue
        </Link>

        {/* Complete Receipt Mutation Action */}
        {isDraft ? (
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleCancelReceipt}
              disabled={cancelReceiptMutation.isPending}
              className="text-rose-700 hover:bg-rose-50 border-rose-300"
            >
              Cancel Draft
            </Button>
            <Button
              variant="primary"
              size="md"
              onClick={handleCompleteReceipt}
              disabled={
                completeReceiptMutation.isPending || !receipt.lines || receipt.lines.length === 0
              }
              className="bg-emerald-600 hover:bg-emerald-700 font-bold gap-2"
            >
              <CheckCircle2 className="size-4" />
              <span>
                {completeReceiptMutation.isPending
                  ? "Posting to Ledger..."
                  : "Complete Receipt (Post to Ledger)"}
              </span>
            </Button>
          </div>
        ) : null}
      </div>

      {/* Header Info Panel */}
      <Card className="mb-6 border-t-4 border-t-blue-600 p-5 shadow-xs">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-lg font-bold text-slate-900">
                {receipt.source_reference || `REC-${receipt.id.slice(0, 8)}`}
              </span>
              <StatusBadge value={receipt.status} />
              <FacilityBadge code={whCode} />
            </div>
            <p className="mt-1 text-xs text-slate-500 font-medium">
              Delivery Type:{" "}
              <strong className="text-slate-700">
                {receipt.source_type === "CARRIER_TRACKING"
                  ? "Carrier Delivery Tracking"
                  : "Seller Drop-Off Ticket"}
              </strong>{" "}
              · Created {formatDate(receipt.created_at)}
            </p>
          </div>

          {/* Running Staged Counts */}
          <div className="flex flex-wrap gap-2 text-xs">
            <div className="rounded-lg bg-emerald-50 px-3 py-1.5 border border-emerald-200">
              <span className="text-[10px] font-bold text-emerald-800 uppercase">
                Sellable (Good)
              </span>
              <p className="font-mono text-base font-extrabold text-emerald-900">{totalSellable}</p>
            </div>
            <div className="rounded-lg bg-rose-50 px-3 py-1.5 border border-rose-200">
              <span className="text-[10px] font-bold text-rose-800 uppercase">
                Damaged (Crushed)
              </span>
              <p className="font-mono text-base font-extrabold text-rose-900">{totalDamaged}</p>
            </div>
            <div className="rounded-lg bg-purple-50 px-3 py-1.5 border border-purple-200">
              <span className="text-[10px] font-bold text-purple-800 uppercase">Quarantined</span>
              <p className="font-mono text-base font-extrabold text-purple-900">
                {totalQuarantined}
              </p>
            </div>
          </div>
        </div>
      </Card>

      {/* Duplicate Override Workflow (for Managers) */}
      {(receipt.status === "DUPLICATE_OVERRIDE" || receipt.is_duplicate_override) &&
      isManager &&
      isDraft ? (
        <Card className="mb-6 border-l-4 border-l-amber-500 bg-amber-50/60 p-5">
          <div className="flex items-center gap-2">
            <ShieldAlert className="size-5 text-amber-600" />
            <h3 className="font-bold text-amber-900 text-sm">
              Manager Duplicate Override Protocol
            </h3>
          </div>
          <p className="mt-1 text-xs text-amber-800">
            This shipment tracking number matches an earlier completed receipt. If this is a
            distinct physical re-shipment, provide justification:
          </p>
          {overrideError ? (
            <div className="mt-2">
              <ErrorState message={overrideError} />
            </div>
          ) : null}
          <div className="mt-3 flex flex-wrap gap-2">
            <input
              type="text"
              value={overrideForm.override_reason}
              onChange={(e) =>
                setOverrideForm({ ...overrideForm, override_reason: e.target.value })
              }
              placeholder="e.g. Carrier re-delivered second box on same tracking number..."
              className="flex-1 rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-xs text-slate-800 focus:outline-none"
            />
            <Button
              variant="secondary"
              size="sm"
              onClick={handleOverrideDuplicate}
              disabled={overrideDuplicateMutation.isPending}
              className="bg-amber-600 text-white hover:bg-amber-700 font-semibold"
            >
              Authorize Duplicate Override
            </Button>
          </div>
        </Card>
      ) : null}

      {/* Main Receiving Layout: Voice Draft Assistant & Manual Line Item Entry */}
      {isDraft ? (
        <div className="mb-6 grid gap-6 lg:grid-cols-12">
          {/* Left Column: Integrated Voice Assistant */}
          <div className="lg:col-span-5">
            <ReceivingVoiceDraftPanel
              receiptId={receipt.id}
              warehouseId={receipt.warehouse_id}
              sellerId={receipt.seller_id}
              onApplyToReceiptDraft={handleVoiceApply}
            />
          </div>

          {/* Right Column: Fast UPC Scanning & Physical Condition Entry */}
          <div className="lg:col-span-7">
            <Card className="p-5 h-full flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                  <div className="flex items-center gap-2">
                    <Barcode className="size-5 text-blue-600" />
                    <h3 className="font-bold text-slate-900 text-sm">
                      Dock Barcode Scan & Line Entry
                    </h3>
                  </div>
                  <span className="text-[11px] font-mono text-slate-500">Scan or Select SKU</span>
                </div>

                {lineError ? (
                  <div className="mt-3">
                    <ErrorState message={lineError} />
                  </div>
                ) : null}

                <form onSubmit={handleSaveLine} className="mt-4 space-y-3.5 text-xs">
                  {/* Product SKU Selector */}
                  <div>
                    <label className="block font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                      Product SKU / Barcode Identifier
                    </label>
                    <select
                      value={lineForm.product_id}
                      onChange={(e) => setLineForm({ ...lineForm, product_id: e.target.value })}
                      className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-mono font-semibold text-slate-900 focus:border-blue-600 focus:outline-none"
                      autoFocus
                    >
                      <option value="">-- Scan Barcode or Select Product SKU --</option>
                      {productOptions.map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.sku} — {p.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Quantities Breakdown: Sellable vs Damaged vs Quarantined */}
                  <div className="grid grid-cols-3 gap-3">
                    <div className="rounded-lg bg-emerald-50/70 p-2.5 border border-emerald-200/80">
                      <label className="block font-bold text-emerald-800 uppercase text-[10px]">
                        Good (Sellable)
                      </label>
                      <input
                        type="number"
                        min="0"
                        value={lineForm.sellable_quantity}
                        onChange={(e) =>
                          setLineForm({ ...lineForm, sellable_quantity: e.target.value })
                        }
                        className="mt-1 w-full rounded-md border border-emerald-300 bg-white px-2.5 py-1.5 font-mono text-sm font-bold text-emerald-950 focus:outline-none"
                      />
                    </div>

                    <div className="rounded-lg bg-rose-50/70 p-2.5 border border-rose-200/80">
                      <label className="block font-bold text-rose-800 uppercase text-[10px]">
                        Damaged (Crushed)
                      </label>
                      <input
                        type="number"
                        min="0"
                        value={lineForm.damaged_quantity}
                        onChange={(e) =>
                          setLineForm({ ...lineForm, damaged_quantity: e.target.value })
                        }
                        className="mt-1 w-full rounded-md border border-rose-300 bg-white px-2.5 py-1.5 font-mono text-sm font-bold text-rose-950 focus:outline-none"
                      />
                    </div>

                    <div className="rounded-lg bg-purple-50/70 p-2.5 border border-purple-200/80">
                      <label className="block font-bold text-purple-800 uppercase text-[10px]">
                        Quarantined
                      </label>
                      <input
                        type="number"
                        min="0"
                        value={lineForm.quarantined_quantity}
                        onChange={(e) =>
                          setLineForm({ ...lineForm, quarantined_quantity: e.target.value })
                        }
                        className="mt-1 w-full rounded-md border border-purple-300 bg-white px-2.5 py-1.5 font-mono text-sm font-bold text-purple-950 focus:outline-none"
                      />
                    </div>
                  </div>

                  {/* Condition Notes */}
                  <div>
                    <label className="block font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                      Condition Notes / Damage Description
                    </label>
                    <input
                      type="text"
                      value={lineForm.notes}
                      onChange={(e) => setLineForm({ ...lineForm, notes: e.target.value })}
                      placeholder="e.g. Outer carton crushed, bottle unbroken; or missing seal"
                      className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-800 focus:border-blue-600 focus:outline-none"
                    />
                  </div>
                </form>
              </div>

              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between">
                <span className="text-[11px] text-slate-500">
                  Separate damaged goods immediately to prevent overstated sellable stock.
                </span>
                <Button
                  variant="primary"
                  size="md"
                  onClick={handleSaveLine}
                  disabled={saveReceiptLineMutation.isPending}
                  className="font-bold"
                >
                  <Plus className="size-4" />
                  <span>
                    {saveReceiptLineMutation.isPending ? "Logging..." : "Log Receipt Line"}
                  </span>
                </Button>
              </div>
            </Card>
          </div>
        </div>
      ) : null}

      {/* Logged Receipt Lines Table */}
      <section className="mb-8">
        <div className="mb-2.5 flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
            Receipt Line Items ({filteredLines.length} logged)
          </h3>
        </div>

        {filteredLines.length === 0 ? (
          <Card className="p-8">
            <EmptyState
              message="No line items logged on this receipt yet"
              hint="Scan product barcodes or speak receiving breakdown to log line items."
            />
          </Card>
        ) : (
          <TableShell>
            <thead>
              <tr>
                <Th>Product SKU</Th>
                <Th>Product Description</Th>
                <Th className="text-right text-emerald-800">Good (Sellable)</Th>
                <Th className="text-right text-rose-800">Damaged (Crushed)</Th>
                <Th className="text-right text-purple-800">Quarantined</Th>
                <Th>Condition Notes</Th>
              </tr>
            </thead>
            <tbody>
              {filteredLines.map((line) => {
                const sku = productSku(products, line.product_id);
                const name = productName(products, line.product_id);

                return (
                  <tr key={line.id} className="hover:bg-slate-50">
                    <Td className="font-mono font-bold text-slate-900">{sku}</Td>
                    <Td className="text-slate-800 font-medium">{name}</Td>
                    <Td className="text-right font-mono font-extrabold text-emerald-700">
                      {formatQty(line.sellable_quantity)}
                    </Td>
                    <Td className="text-right font-mono font-extrabold text-rose-700">
                      {formatQty(line.damaged_quantity)}
                    </Td>
                    <Td className="text-right font-mono font-extrabold text-purple-700">
                      {formatQty(line.quarantined_quantity)}
                    </Td>
                    <Td className="text-slate-600 italic">{line.notes || "—"}</Td>
                  </tr>
                );
              })}
            </tbody>
          </TableShell>
        )}
      </section>

      {/* Audit Event Timeline */}
      <section>
        <div className="mb-2.5 flex items-center justify-between border-b border-slate-200 pb-2">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700">
            Receipt Audit Trail & Event Timeline
          </h3>
          <span className="text-xs font-mono text-slate-400">Ledger Traceable</span>
        </div>

        <Card className="p-4">
          <div className="space-y-3 text-xs">
            <div className="flex items-start gap-3">
              <div className="flex size-7 items-center justify-center rounded-md bg-blue-50 text-blue-700 border border-blue-200">
                <PackageCheck className="size-4" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="font-bold text-slate-900">Inbound Receipt Created</p>
                <p className="text-slate-500">
                  Tracking / Reference: {receipt.source_reference} · Facility: {whCode}
                </p>
              </div>
              <span className="font-mono text-[11px] text-slate-400">
                {formatDate(receipt.created_at)}
              </span>
            </div>

            {isCompleted ? (
              <div className="flex items-start gap-3 border-t border-slate-100 pt-3">
                <div className="flex size-7 items-center justify-center rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200">
                  <CheckCircle2 className="size-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="font-bold text-emerald-900">
                    Receipt Completed & Posted to Movement Ledger
                  </p>
                  <p className="text-slate-600">
                    {totalSellable} units posted to AVAILABLE; {totalDamaged} units posted to
                    DAMAGED.
                  </p>
                </div>
                <span className="font-mono text-[11px] text-slate-400">
                  {formatDate(receipt.updated_at || receipt.created_at)}
                </span>
              </div>
            ) : null}
          </div>
        </Card>
      </section>
    </AppShell>
  );
}
