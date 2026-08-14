import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import {
  Barcode,
  Boxes,
  FileCheck2,
  PackageCheck,
  PackagePlus,
  Plus,
  RefreshCw,
  ShieldCheck,
  Truck,
  WifiOff,
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { FacilityBadge, StatusBadge } from "@/components/StatusBadge";
import {
  Button,
  Card,
  DuplicateProtectionBanner,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  ScannerInputField,
  TableShell,
  Td,
  Th,
} from "@/components/ui-kit";
import { sellerLabel, warehouseLabel } from "@/lib/display";
import { formatDate } from "@/lib/format";
import {
  useCreateReceiptMutation,
  useReceiptsQuery,
  useSellersQuery,
  useWarehousesQuery,
} from "@/hooks/use-api";
import {
  getOfflineDrafts,
  saveOfflineDraft,
  syncOfflineDrafts,
  type OfflineDraftReceipt,
} from "@/lib/offline-receipt-store";
import type { Receipt } from "@/lib/types";

export const Route = createFileRoute("/receipts/")({
  head: () => ({
    meta: [
      { title: "Inbound Receiving Dock | Whitfield Ops" },
      {
        name: "description",
        content:
          "Carrier tracking intake, seller drop-off tickets, UPC barcode scanning, and duplicate-safe receiving.",
      },
      { property: "og:title", content: "Inbound Receiving Dock | Whitfield Ops" },
      {
        property: "og:description",
        content: "Dock-to-stock inbound receipts with physical condition separation.",
      },
    ],
  }),
  component: ReceiptsPage,
});

function ReceiptsPage() {
  const receiptsQuery = useReceiptsQuery();
  const sellersQuery = useSellersQuery();
  const warehousesQuery = useWarehousesQuery();
  const receipts = receiptsQuery.data ?? [];
  const sellers = sellersQuery.data ?? [];
  const warehouses = warehousesQuery.data ?? [];
  const createReceiptMutation = useCreateReceiptMutation();

  const [open, setOpen] = useState(false);
  const [sourceType, setSourceType] = useState<"CARRIER_TRACKING" | "SELLER_DROP_OFF">(
    "CARRIER_TRACKING",
  );
  const [form, setForm] = useState({
    seller_id: sellers[0]?.id || "",
    warehouse_id: warehouses[0]?.id || "",
    source_reference: "",
  });
  const [filterSearch, setFilterSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [offlineDrafts, setOfflineDrafts] = useState<OfflineDraftReceipt[]>([]);
  const [isSyncing, setIsSyncing] = useState(false);

  useEffect(() => {
    getOfflineDrafts()
      .then(setOfflineDrafts)
      .catch((err: unknown) => {
        const errMsg = err instanceof Error ? err.message : "Could not load offline drafts.";
        setError(errMsg);
      });
  }, []);

  async function handleSync() {
    setIsSyncing(true);
    try {
      await syncOfflineDrafts();
      setOfflineDrafts(await getOfflineDrafts());
      receiptsQuery.refetch();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not sync offline drafts.");
    } finally {
      setIsSyncing(false);
    }
  }

  async function create() {
    if (!form.source_reference.trim()) {
      return setError(
        sourceType === "CARRIER_TRACKING"
          ? "Carrier tracking number is required."
          : "Seller drop-off ticket number is required.",
      );
    }
    setError(null);
    const sellerId = form.seller_id || sellers[0]?.id || "";
    const warehouseId = form.warehouse_id || warehouses[0]?.id || "";

    try {
      await createReceiptMutation.mutateAsync({
        seller_id: sellerId,
        warehouse_id: warehouseId,
        source_type: sourceType,
        source_reference: form.source_reference.trim(),
      });
      setForm({
        seller_id: sellerId,
        warehouse_id: warehouseId,
        source_reference: "",
      });
      setOpen(false);
      receiptsQuery.refetch();
    } catch (err: unknown) {
      // If network fails, offer offline draft creation
      const errMsg = err instanceof Error ? err.message : "Network error creating receipt.";
      if (
        errMsg.toLowerCase().includes("network") ||
        errMsg.toLowerCase().includes("failed to fetch")
      ) {
        const draft: OfflineDraftReceipt = {
          id: `offline-${Date.now()}`,
          client_draft_id: `draft-${Date.now()}`,
          seller_id: sellerId,
          warehouse_id: warehouseId,
          source_type: sourceType,
          source_reference: form.source_reference.trim(),
          created_at: new Date().toISOString(),
          lines: [],
          syncStatus: "DRAFT",
        };
        await saveOfflineDraft(draft);
        setOfflineDrafts(await getOfflineDrafts());
        setOpen(false);
        setError("Saved as an offline draft. Click 'Sync Staged Drafts' once network restores.");
      } else {
        setError(errMsg);
      }
    }
  }

  const filteredReceipts = receipts.filter((r) => {
    if (!filterSearch.trim()) return true;
    const q = filterSearch.toLowerCase().trim();
    const ref = (r.source_reference || "").toLowerCase();
    const seller = sellerLabel(sellers, r.seller_id).toLowerCase();
    const id = r.id.toLowerCase();
    return ref.includes(q) || seller.includes(q) || id.includes(q);
  });

  return (
    <AppShell>
      <PageHeader
        title="Inbound Receiving Dock"
        subtitle="Log carrier deliveries and seller drop-off shipments with UPC barcode scanning and physical condition separation."
        actions={
          <div className="flex items-center gap-2">
            {offlineDrafts.length > 0 ? (
              <Button
                variant="outline"
                size="sm"
                onClick={handleSync}
                disabled={isSyncing}
                className="border-amber-300 text-amber-800 hover:bg-amber-50"
              >
                <RefreshCw className={`size-3.5 ${isSyncing ? "animate-spin" : ""}`} />
                <span>Sync {offlineDrafts.length} Offline Drafts</span>
              </Button>
            ) : null}
            <Button variant="primary" size="md" onClick={() => setOpen(true)} className="gap-2">
              <PackagePlus className="size-4" />
              <span>New Inbound Receipt</span>
            </Button>
          </div>
        }
      />

      <DuplicateProtectionBanner message="Receipts require unique carrier tracking numbers or seller drop-off tickets per seller. Duplicate submissions are safely intercepted to prevent doubled inventory balances." />

      {receiptsQuery.isLoading ? <LoadingState message="Loading receiving queue..." /> : null}
      {receiptsQuery.isError ? (
        <ErrorState
          message="Could not load inbound receipts from backend."
          onRetry={() => receiptsQuery.refetch()}
        />
      ) : null}

      {/* Offline Drafts Alert if any exist */}
      {offlineDrafts.length > 0 ? (
        <div className="mb-5 flex items-center justify-between rounded-xl border border-amber-300 bg-amber-50 p-4 text-xs text-amber-900 shadow-xs">
          <div className="flex items-center gap-2.5">
            <WifiOff className="size-5 text-amber-600 shrink-0" />
            <div>
              <p className="font-bold">
                {offlineDrafts.length} Offline Receipt Draft(s) Stored Locally
              </p>
              <p className="text-amber-800">
                Created while dock network was offline. These do not affect inventory ledger
                balances until synchronized.
              </p>
            </div>
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={handleSync}
            disabled={isSyncing}
            className="bg-white border-amber-300 text-amber-900"
          >
            {isSyncing ? "Syncing..." : "Sync to Server Now"}
          </Button>
        </div>
      ) : null}

      {/* Filter & Barcode Search Bar */}
      <Card className="mb-5 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="w-full sm:w-80">
            <ScannerInputField
              value={filterSearch}
              onChange={(e) => setFilterSearch(e.target.value)}
              placeholder="Scan tracking # or search receipt..."
            />
          </div>
          <div className="flex items-center gap-3 text-xs text-slate-500 font-medium">
            <span className="flex items-center gap-1.5">
              <span className="size-2 rounded-full bg-amber-500" />
              <span>DRAFT: Line entry open</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="size-2 rounded-full bg-emerald-500" />
              <span>COMPLETED: Ledger posted</span>
            </span>
          </div>
        </div>
      </Card>

      {/* Create Inbound Receipt Modal */}
      {open ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-xs">
          <div className="w-full max-w-lg rounded-xl border border-slate-200 bg-white p-6 shadow-2xl animate-rise">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2">
                <PackagePlus className="size-5 text-blue-600" />
                <h3 className="font-bold text-slate-900 text-base">New Inbound Receipt Intake</h3>
              </div>
              <button
                onClick={() => {
                  setOpen(false);
                  setError(null);
                }}
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
              {/* Source Type Selector */}
              <div>
                <label className="block font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  Intake Delivery Type
                </label>
                <div className="mt-1.5 grid grid-cols-2 gap-2.5">
                  <button
                    type="button"
                    onClick={() => setSourceType("CARRIER_TRACKING")}
                    className={`flex items-center justify-center gap-2 rounded-lg border p-2.5 font-semibold transition-all cursor-pointer ${
                      sourceType === "CARRIER_TRACKING"
                        ? "border-blue-600 bg-blue-50 text-blue-800 ring-1 ring-blue-600"
                        : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    <Truck className="size-4" />
                    <span>Carrier Delivery (UPS/FedEx)</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setSourceType("SELLER_DROP_OFF")}
                    className={`flex items-center justify-center gap-2 rounded-lg border p-2.5 font-semibold transition-all cursor-pointer ${
                      sourceType === "SELLER_DROP_OFF"
                        ? "border-blue-600 bg-blue-50 text-blue-800 ring-1 ring-blue-600"
                        : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                    }`}
                  >
                    <FileCheck2 className="size-4" />
                    <span>Seller In-Person Drop-Off</span>
                  </button>
                </div>
              </div>

              {/* Source Reference Input */}
              <div>
                <label className="block font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                  {sourceType === "CARRIER_TRACKING"
                    ? "Carrier Tracking Number (Barcode Scan)"
                    : "Seller Drop-Off Ticket #"}
                </label>
                <div className="mt-1">
                  <ScannerInputField
                    value={form.source_reference}
                    onChange={(e) => setForm({ ...form, source_reference: e.target.value })}
                    placeholder={
                      sourceType === "CARRIER_TRACKING"
                        ? "e.g. 1Z9999999999999999 or scan shipping label"
                        : "e.g. TICKET-2026-0814"
                    }
                    autoFocus
                  />
                </div>
                <p className="mt-1 text-[11px] text-slate-500">
                  Used for duplicate detection to prevent double-logging if laptops freeze or
                  network resets.
                </p>
              </div>

              {/* Warehouse Selection */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                    Receiving Warehouse
                  </label>
                  <select
                    value={form.warehouse_id}
                    onChange={(e) => setForm({ ...form, warehouse_id: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-800 focus:border-blue-600 focus:outline-none"
                  >
                    {warehouses.map((w) => (
                      <option key={w.id} value={w.id}>
                        {w.code} ({w.city || "Hub"}, {w.state || ""})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Seller Tenant Selection */}
                <div>
                  <label className="block font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                    Seller Account
                  </label>
                  <select
                    value={form.seller_id}
                    onChange={(e) => setForm({ ...form, seller_id: e.target.value })}
                    className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-800 focus:border-blue-600 focus:outline-none"
                  >
                    {sellers.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name} ({s.code})
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            <div className="mt-6 flex items-center justify-end gap-2.5 border-t border-slate-100 pt-4">
              <Button
                variant="secondary"
                size="md"
                onClick={() => {
                  setOpen(false);
                  setError(null);
                }}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="md"
                onClick={create}
                disabled={createReceiptMutation.isPending}
              >
                {createReceiptMutation.isPending ? "Creating Draft..." : "Create Inbound Draft"}
              </Button>
            </div>
          </div>
        </div>
      ) : null}

      {/* Main Receipts Table */}
      {filteredReceipts.length === 0 ? (
        <Card className="p-8">
          <EmptyState
            message="No inbound receipts found"
            hint="Create a new receipt above when a delivery truck arrives at the Reno or Columbus dock."
          />
        </Card>
      ) : (
        <TableShell>
          <thead>
            <tr>
              <Th>Receipt Reference</Th>
              <Th>Delivery Type</Th>
              <Th>Seller Tenant</Th>
              <Th>Warehouse Dock</Th>
              <Th>Created Date</Th>
              <Th>Status</Th>
              <Th className="text-right">Action</Th>
            </tr>
          </thead>
          <tbody>
            {filteredReceipts.map((r: Receipt) => {
              const whCode = warehouses.find((w) => w.id === r.warehouse_id)?.code || "WH";

              return (
                <tr key={r.id} className="hover:bg-slate-50/80 transition-colors">
                  <Td className="font-mono font-bold text-slate-900">
                    <Link
                      to="/receipts/$id"
                      params={{ id: r.id }}
                      className="text-blue-600 hover:text-blue-800 hover:underline"
                    >
                      {r.source_reference || `REC-${r.id.slice(0, 8)}`}
                    </Link>
                  </Td>
                  <Td className="text-slate-600 font-medium">
                    {r.source_type === "CARRIER_TRACKING" ? "Carrier Tracking" : "Seller Drop-Off"}
                  </Td>
                  <Td className="text-slate-800 font-medium">
                    {sellerLabel(sellers, r.seller_id)}
                  </Td>
                  <Td>
                    <FacilityBadge code={whCode} />
                  </Td>
                  <Td className="font-mono text-xs text-slate-500">{formatDate(r.created_at)}</Td>
                  <Td>
                    <StatusBadge value={r.status} />
                  </Td>
                  <Td className="text-right">
                    <Link
                      to="/receipts/$id"
                      params={{ id: r.id }}
                      className="inline-flex items-center gap-1 rounded-lg bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-800 hover:bg-blue-50 hover:text-blue-700 transition-colors"
                    >
                      {r.status === "DRAFT" ? "Scan Line Items" : "View Details"}
                    </Link>
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </TableShell>
      )}
    </AppShell>
  );
}
