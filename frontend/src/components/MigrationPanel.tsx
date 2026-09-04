import { useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Database,
  FileSpreadsheet,
  FileText,
  Lock,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  UploadCloud,
} from "lucide-react";
import { FacilityBadge, StatusBadge } from "@/components/StatusBadge";
import { ConfirmActionDialog } from "@/components/ConfirmActionDialog";
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  LedgerNoticeBanner,
  LoadingState,
  TableShell,
  Td,
  Th,
} from "@/components/ui-kit";
import {
  useApplyMigrationBatchMutation,
  useApproveMigrationBatchMutation,
  useCreateMigrationBatchMutation,
  useMigrationBatchesQuery,
  useMigrationReconciliationQuery,
  useUploadMigrationFileMutation,
  useValidateMigrationBatchMutation,
} from "@/hooks/use-api";
import { useAuth } from "@/lib/auth";
import type { ImportBatch, MigrationReconciliationRow } from "@/lib/types";

function formatQuantity(value: number | string): string {
  return Number(value).toLocaleString(undefined, {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  });
}

function batchCanUpload(batch?: ImportBatch): boolean {
  return Boolean(batch && !["APPROVED", "APPLIED"].includes(batch.status));
}

function batchCanValidate(batch?: ImportBatch): boolean {
  return Boolean(batch && ["STAGED", "VALIDATION_FAILED"].includes(batch.status));
}

function batchCanApprove(batch?: ImportBatch): boolean {
  return batch?.status === "VALIDATED";
}

function batchCanApply(batch?: ImportBatch): boolean {
  return batch?.status === "APPROVED";
}

export function MigrationPanel() {
  const { user } = useAuth();
  const batchesQuery = useMigrationBatchesQuery();
  const batches = useMemo(() => batchesQuery.data ?? [], [batchesQuery.data]);
  const [selectedBatchId, setSelectedBatchId] = useState<string>("");
  const [sourceNotes, setSourceNotes] = useState("Opening inventory cutover batch");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmApply, setConfirmApply] = useState(false);

  const createBatch = useCreateMigrationBatchMutation();
  const uploadFile = useUploadMigrationFileMutation();
  const validateBatch = useValidateMigrationBatchMutation();
  const approveBatch = useApproveMigrationBatchMutation();
  const applyBatch = useApplyMigrationBatchMutation();

  const selectedBatch = useMemo(
    () => batches.find((batch) => batch.id === selectedBatchId) ?? batches[0],
    [batches, selectedBatchId],
  );
  const effectiveBatchId = selectedBatch?.id ?? "";
  const reconciliationQuery = useMigrationReconciliationQuery(effectiveBatchId);
  const reconciliation = reconciliationQuery.data;
  const canOperateMigration = user?.role === "ADMINISTRATOR" || user?.role === "WAREHOUSE_MANAGER";

  async function runAction(action: () => Promise<unknown>, successMessage: string): Promise<boolean> {
    setError(null);
    setMessage(null);
    try {
      await action();
      setMessage(successMessage);
      batchesQuery.refetch();
      return true;
    } catch (caught: unknown) {
      setError(caught instanceof Error ? caught.message : "Migration action failed.");
      return false;
    }
  }

  async function handleCreateBatch() {
    if (!canOperateMigration) return setError("Your role cannot create migration batches.");
    await runAction(async () => {
      const batch = await createBatch.mutateAsync(sourceNotes.trim());
      setSelectedBatchId(batch.id);
    }, "Created migration staging batch.");
  }

  async function handleUploadFile() {
    if (!canOperateMigration) return setError("Your role cannot stage migration rows.");
    if (!effectiveBatchId) return setError("Select or create a batch first.");
    if (!selectedFile) return setError("Choose a CSV or XLSX file first.");
    await runAction(async () => {
      await uploadFile.mutateAsync({ batchId: effectiveBatchId, file: selectedFile });
      setSelectedFile(null);
    }, "Uploaded file into staging sandbox only. Live inventory was not mutated.");
  }

  async function handleValidate() {
    if (!canOperateMigration) return setError("Your role cannot validate migration batches.");
    if (!effectiveBatchId) return;
    await runAction(
      async () => validateBatch.mutateAsync(effectiveBatchId),
      "Validated staged opening inventory rows against product catalog and warehouse master data.",
    );
  }

  async function handleApprove() {
    if (!canOperateMigration) return setError("Your role cannot approve migration batches.");
    if (!effectiveBatchId) return;
    await runAction(
      async () => approveBatch.mutateAsync(effectiveBatchId),
      "Approved migration batch for ledger application.",
    );
  }

  function handleApply() {
    if (!canOperateMigration) return setError("Your role cannot apply migration batches.");
    if (!effectiveBatchId) return;
    setConfirmApply(true);
  }

  async function performApply() {
    const success = await runAction(
      async () => applyBatch.mutateAsync(effectiveBatchId),
      "Successfully posted opening inventory balances to the immutable movement ledger.",
    );
    if (success) {
      setConfirmApply(false);
    }
  }

  const isBusy =
    createBatch.isPending ||
    uploadFile.isPending ||
    validateBatch.isPending ||
    approveBatch.isPending ||
    applyBatch.isPending;
  const controlsDisabled = isBusy || !canOperateMigration;

  return (
    <div className="space-y-6">
      {/* Cutover Strategy Banner */}
      <Card className="border-t-4 border-t-blue-600 p-5 shadow-xs">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <FileSpreadsheet className="size-5 text-blue-600" />
              <h2 className="text-base font-bold text-slate-900">
                Excel Spreadsheet Cutover & Opening Balance Staging
              </h2>
            </div>
            <p className="mt-1 max-w-3xl text-xs text-slate-600 font-medium">
              Stage legacy CSV/XLSX spreadsheets, perform automated validation (SKU existence,
              positive counts, seller matching), require manager approval, and commit balances
              strictly via movement ledger transactions.
            </p>
            <div className="mt-2.5 flex items-center gap-2 text-[11px] text-slate-500">
              <ShieldCheck className="size-4 text-emerald-600" />
              <span>
                Staged rows reside in an isolated sandbox and cannot mutate live stock until
                approved and applied.
              </span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <input
              value={sourceNotes}
              onChange={(event) => setSourceNotes(event.target.value)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs text-slate-800 focus:outline-none w-64"
              placeholder="e.g. Reno cutover opening stock"
            />
            <Button
              variant="primary"
              size="md"
              onClick={handleCreateBatch}
              disabled={controlsDisabled}
              className="font-bold"
            >
              + Create Staging Batch
            </Button>
          </div>
        </div>
      </Card>

      {/* 5-Stage Migration Pipeline Indicator */}
      <div className="grid grid-cols-5 gap-2 text-center text-xs">
        <div
          className={`rounded-lg p-2.5 border font-semibold ${selectedBatch?.status === "STAGED" ? "bg-blue-50 border-blue-300 text-blue-800" : "bg-slate-50 border-slate-200 text-slate-500"}`}
        >
          <span className="text-[10px] font-bold uppercase block text-slate-400">Step 1</span>
          1. Staged Sandbox
        </div>
        <div
          className={`rounded-lg p-2.5 border font-semibold ${selectedBatch?.status === "VALIDATING" ? "bg-blue-50 border-blue-300 text-blue-800" : "bg-slate-50 border-slate-200 text-slate-500"}`}
        >
          <span className="text-[10px] font-bold uppercase block text-slate-400">Step 2</span>
          2. Validating Rows
        </div>
        <div
          className={`rounded-lg p-2.5 border font-semibold ${selectedBatch?.status === "VALIDATED" ? "bg-emerald-50 border-emerald-300 text-emerald-800" : selectedBatch?.status === "VALIDATION_FAILED" ? "bg-rose-50 border-rose-300 text-rose-800" : "bg-slate-50 border-slate-200 text-slate-500"}`}
        >
          <span className="text-[10px] font-bold uppercase block text-slate-400">Step 3</span>
          3. Validated Clean
        </div>
        <div
          className={`rounded-lg p-2.5 border font-semibold ${selectedBatch?.status === "APPROVED" ? "bg-purple-50 border-purple-300 text-purple-800" : "bg-slate-50 border-slate-200 text-slate-500"}`}
        >
          <span className="text-[10px] font-bold uppercase block text-slate-400">Step 4</span>
          4. Manager Approved
        </div>
        <div
          className={`rounded-lg p-2.5 border font-semibold ${selectedBatch?.status === "APPLIED" ? "bg-emerald-600 text-white border-emerald-700" : "bg-slate-50 border-slate-200 text-slate-500"}`}
        >
          <span className="text-[10px] font-bold uppercase block text-slate-300">Step 5</span>
          5. Posted to Ledger
        </div>
      </div>

      {message ? (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-800 font-medium flex items-center gap-2">
          <CheckCircle2 className="size-4 text-emerald-600 shrink-0" />
          <span>{message}</span>
        </div>
      ) : null}

      {error ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800 font-medium flex items-center gap-2">
          <AlertTriangle className="size-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      ) : null}

      {/* Batch Selector & Actions Card */}
      <Card className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 pb-4">
          <div className="flex flex-wrap items-center gap-3">
            <label htmlFor="migration-active-batch" className="text-xs font-bold text-slate-700 uppercase tracking-wider text-[10px]">
              Active Batch:
            </label>
            <select
              id="migration-active-batch"
              value={effectiveBatchId}
              onChange={(event) => setSelectedBatchId(event.target.value)}
              className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 font-mono text-xs font-bold text-slate-900 focus:outline-none focus:border-primary focus:ring-2 focus:ring-primary/15"
            >
              {batches.map((batch) => (
                <option key={batch.id} value={batch.id}>
                  {batch.source_notes || "Batch"} ({batch.status}) — {batch.id.slice(0, 8)}
                </option>
              ))}
            </select>
            {selectedBatch ? <StatusBadge value={selectedBatch.status} /> : null}
          </div>

          {/* Action Buttons for current batch state */}
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleValidate}
              disabled={controlsDisabled || !batchCanValidate(selectedBatch)}
            >
              Validate Rows
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={handleApprove}
              disabled={controlsDisabled || !batchCanApprove(selectedBatch)}
            >
              Approve Batch
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleApply}
              disabled={controlsDisabled || !batchCanApply(selectedBatch)}
              className="bg-emerald-600 hover:bg-emerald-700 font-bold"
            >
              Apply to Movement Ledger
            </Button>
          </div>
        </div>

        {/* Upload File into Active Batch */}
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <label htmlFor="migration-upload-file" className="text-xs font-semibold text-slate-700">
            Upload Spreadsheet (CSV/XLSX):
          </label>
          <input
            id="migration-upload-file"
            type="file"
            accept=".csv,.xlsx,.xls"
            onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
            disabled={controlsDisabled || !batchCanUpload(selectedBatch)}
            className="text-xs text-slate-700 file:mr-2 file:rounded-md file:border-0 file:bg-slate-100 file:px-3 file:py-1 file:text-xs file:font-semibold file:text-slate-800 hover:file:bg-slate-200"
          />
          <Button
            variant="secondary"
            size="sm"
            onClick={handleUploadFile}
            disabled={controlsDisabled || !selectedFile || !batchCanUpload(selectedBatch)}
          >
            <UploadCloud className="size-3.5" /> Stage File
          </Button>
        </div>
      </Card>

      {/* Batch Statistics & Reconciliation Summary */}
      {selectedBatch ? (
        <div className="grid grid-cols-2 gap-3.5 sm:grid-cols-4">
          <Card className="p-4">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
              Total Staged Rows
            </span>
            <p className="mt-1 font-mono text-xl font-extrabold text-slate-900">
              {selectedBatch.total_rows || 0}
            </p>
          </Card>

          <Card className="p-4">
            <span className="text-[10px] font-bold text-emerald-800 uppercase tracking-wider">
              Valid Rows
            </span>
            <p className="mt-1 font-mono text-xl font-extrabold text-emerald-900">
              {selectedBatch.valid_rows || 0}
            </p>
          </Card>

          <Card className="p-4">
            <span className="text-[10px] font-bold text-rose-800 uppercase tracking-wider">
              Invalid Error Rows
            </span>
            <p className="mt-1 font-mono text-xl font-extrabold text-rose-900">
              {selectedBatch.invalid_rows || 0}
            </p>
          </Card>

          <Card className="p-4">
            <span className="text-[10px] font-bold text-blue-800 uppercase tracking-wider">
              10-Day Gate Status
            </span>
            <p className="mt-1 font-mono text-sm font-bold text-blue-900">
              {selectedBatch.status === "APPLIED" ? "Verified" : "Pending Application"}
            </p>
          </Card>
        </div>
      ) : null}

      {/* Reconciliation Comparison Table */}
      <Card className="p-5">
        <div className="mb-3 flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <Database className="size-4 text-blue-600" />
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-tight">
              Pre-Application Reconciliation Comparison
            </h3>
          </div>
          <span className="text-[11px] font-mono text-slate-500">Staged vs Computed Ledger</span>
        </div>

        {reconciliationQuery.isLoading ? (
          <LoadingState message="Computing reconciliation audit..." />
        ) : reconciliation && reconciliation.details?.length > 0 ? (
          <TableShell>
            <thead>
              <tr>
                <Th>Seller Code</Th>
                <Th>Warehouse</Th>
                <Th>Product SKU</Th>
                <Th className="text-right">Staged Quantity</Th>
                <Th className="text-right">Applied Movement Quantity</Th>
                <Th className="text-right">Variance</Th>
              </tr>
            </thead>
            <tbody>
              {reconciliation.details.map((row: MigrationReconciliationRow, idx: number) => {
                const staged = Number(row.staged_approved_quantity || 0);
                const applied = Number(row.ledger_movement_quantity || 0);
                const variance = Number(row.variance_quantity ?? staged - applied);

                return (
                  <tr key={idx} className="hover:bg-slate-50">
                    <Td className="font-semibold text-slate-800">{row.seller_code || "—"}</Td>
                    <Td className="font-mono text-slate-700">{row.warehouse_code || "—"}</Td>
                    <Td className="font-mono font-bold text-slate-900">{row.sku || "—"}</Td>
                    <Td className="text-right font-mono font-bold text-slate-900">
                      {formatQuantity(staged)}
                    </Td>
                    <Td className="text-right font-mono font-bold text-emerald-700">
                      {formatQuantity(applied)}
                    </Td>
                    <Td
                      className={`text-right font-mono font-extrabold ${
                        variance === 0 ? "text-emerald-700" : "text-rose-700"
                      }`}
                    >
                      {formatQuantity(variance)}
                    </Td>
                  </tr>
                );
              })}
            </tbody>
          </TableShell>
        ) : (
          <div className="py-6 text-center text-xs text-slate-500">
            No staged rows loaded for this batch. Upload a spreadsheet to view reconciliation
            comparisons.
          </div>
        )}
      </Card>

      <ConfirmActionDialog
        open={confirmApply}
        onOpenChange={setConfirmApply}
        title="Apply opening inventory batch?"
        description="Apply this opening inventory batch to the immutable movement ledger? This will create permanent balance records."
        recordIdentifier={effectiveBatchId}
        confirmLabel="Apply batch"
        cancelLabel="Review batch"
        destructive
        pending={applyBatch.isPending}
        onConfirm={performApply}
      />
    </div>
  );
}
