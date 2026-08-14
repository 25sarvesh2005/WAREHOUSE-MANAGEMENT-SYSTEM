import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Database,
  ExternalLink,
  FileText,
  Fingerprint,
  Info,
  Layers,
  Loader2,
  Lock,
  Search,
  Send,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  XCircle,
} from "lucide-react";
import { useState } from "react";
import {
  askAiInventoryAvailability,
  askAiLedgerExplanation,
  askAiOrderStatus,
  askAiReceiptStatus,
  askAiReturnStatus,
  askAiShipmentStatus,
  askAiTransferStatus,
  createAiDraftRecommendationApi,
  submitAiFeedbackApi,
  summarizeAiExceptionsApi,
} from "@/lib/api-services";
import { ApiError } from "@/lib/api-client";
import type {
  AiAvailabilityRow,
  AiDraftRecommendationResponse,
  AiExceptionCategorySummary,
  AiExceptionSummaryResponse,
  AiInventoryAvailabilityResponse,
  AiLedgerExplanationResponse,
  AiLedgerMovementRow,
  AiOperationalRecord,
  AiOperationalStatusResponse,
  AiReference,
  Role,
} from "@/lib/types";
import { Card, ScannerInputField, TableShell, Td, Th } from "@/components/ui-kit";

// ---------------------------------------------------------------------------
// Mode definitions and role gating
// ---------------------------------------------------------------------------

type AiMode =
  | "inventory-availability"
  | "ledger-explanation"
  | "order"
  | "receipt"
  | "transfer"
  | "shipment"
  | "return"
  | "exceptions-summary"
  | "draft-recommendation";

interface ModeConfig {
  id: AiMode;
  label: string;
  inputKind: "sku" | "reference" | "none" | "draft";
  /** Roles allowed to use this mode. Empty array = all roles. */
  allowedRoles: Role[];
}

const MODES: ModeConfig[] = [
  {
    id: "inventory-availability",
    label: "Inventory Availability",
    inputKind: "sku",
    allowedRoles: [],
  },
  {
    id: "ledger-explanation",
    label: "Ledger Explanation",
    inputKind: "sku",
    allowedRoles: ["ADMINISTRATOR", "WAREHOUSE_MANAGER", "RECEIVER"],
  },
  {
    id: "exceptions-summary",
    label: "Exceptions Summary",
    inputKind: "none",
    allowedRoles: ["ADMINISTRATOR", "WAREHOUSE_MANAGER", "RECEIVER"],
  },
  {
    id: "draft-recommendation",
    label: "Draft Recommendation",
    inputKind: "draft",
    allowedRoles: ["ADMINISTRATOR", "WAREHOUSE_MANAGER"],
  },
  {
    id: "order",
    label: "Order Status",
    inputKind: "reference",
    allowedRoles: ["ADMINISTRATOR", "WAREHOUSE_MANAGER", "PICKER_PACKER", "SELLER"],
  },
  {
    id: "receipt",
    label: "Receipt Status",
    inputKind: "reference",
    allowedRoles: ["ADMINISTRATOR", "WAREHOUSE_MANAGER", "RECEIVER"],
  },
  {
    id: "transfer",
    label: "Transfer Status",
    inputKind: "reference",
    allowedRoles: ["ADMINISTRATOR", "WAREHOUSE_MANAGER"],
  },
  {
    id: "shipment",
    label: "Shipment Status",
    inputKind: "reference",
    allowedRoles: ["ADMINISTRATOR", "WAREHOUSE_MANAGER", "PICKER_PACKER", "SELLER"],
  },
  {
    id: "return",
    label: "Return Status",
    inputKind: "reference",
    allowedRoles: ["ADMINISTRATOR", "WAREHOUSE_MANAGER", "RECEIVER", "SELLER"],
  },
];

function allowedModes(role: Role): ModeConfig[] {
  return MODES.filter((m) => m.allowedRoles.length === 0 || m.allowedRoles.includes(role));
}

type AiResult =
  | AiInventoryAvailabilityResponse
  | AiLedgerExplanationResponse
  | AiOperationalStatusResponse
  | AiExceptionSummaryResponse
  | AiDraftRecommendationResponse;

function ProviderBadge({ providerName }: { providerName: string }) {
  const isGemini = providerName === "google_genai";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-semibold ${
        isGemini
          ? "bg-indigo-50 text-indigo-800 border border-indigo-200"
          : "bg-slate-100 text-slate-700 border border-slate-200"
      }`}
    >
      {isGemini ? <Sparkles className="size-3 text-indigo-600" /> : <Bot className="size-3" />}
      {isGemini ? "Gemini AI Model" : "Deterministic Rule Engine"}
    </span>
  );
}

function SafetyBadge({ safetyDecision }: { safetyDecision: string }) {
  const isAllow = safetyDecision === "ALLOW_READ_ONLY";
  const isRefusal = safetyDecision.startsWith("REFUSE");
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-semibold ${
        isAllow
          ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
          : isRefusal
            ? "bg-rose-50 text-rose-800 border border-rose-200"
            : "bg-amber-50 text-amber-800 border border-amber-200"
      }`}
    >
      <ShieldCheck className="size-3 text-emerald-600" />
      {isAllow ? "Read-Only Verified" : safetyDecision.replaceAll("_", " ")}
    </span>
  );
}

function CollapsibleSection({
  title,
  defaultOpen = false,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="mt-3 rounded-lg border border-slate-200 bg-white">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-3.5 py-2.5 text-xs font-bold text-slate-900 transition-colors hover:bg-slate-50 cursor-pointer"
        aria-expanded={open}
      >
        {title}
        {open ? (
          <ChevronDown className="size-4 text-slate-500" />
        ) : (
          <ChevronRight className="size-4 text-slate-500" />
        )}
      </button>
      {open ? <div className="border-t border-slate-100 p-3.5 text-xs">{children}</div> : null}
    </div>
  );
}

function FeedbackWidget({
  interactionId,
  onSubmitted,
}: {
  interactionId: string;
  onSubmitted?: () => void;
}) {
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [showComment, setShowComment] = useState(false);
  const [rating, setRating] = useState<"HELPFUL" | "UNHELPFUL" | null>(null);
  const [comment, setComment] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleRate(value: "HELPFUL" | "UNHELPFUL") {
    setRating(value);
    setShowComment(true);
  }

  async function handleSend() {
    if (!rating) return;
    setLoading(true);
    setError(null);
    try {
      await submitAiFeedbackApi(interactionId, {
        is_helpful: rating === "HELPFUL",
        comment: comment.trim() || undefined,
      });
      setSubmitted(true);
      onSubmitted?.();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to submit feedback.");
    } finally {
      setLoading(false);
    }
  }

  if (submitted) {
    return (
      <div className="mt-3 flex items-center gap-1.5 text-xs font-semibold text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-lg border border-emerald-200">
        <CheckCircle2 className="size-3.5" />
        Feedback recorded. Thank you!
      </div>
    );
  }

  return (
    <div className="mt-3 rounded-lg border border-slate-200 bg-slate-50/70 p-3 text-xs">
      <div className="flex items-center justify-between">
        <span className="font-semibold text-slate-700">Was this response accurate?</span>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => handleRate("HELPFUL")}
            className={`flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-semibold border transition-all cursor-pointer ${
              rating === "HELPFUL"
                ? "bg-emerald-600 text-white border-emerald-700"
                : "bg-white text-slate-700 border-slate-200 hover:bg-slate-100"
            }`}
          >
            <ThumbsUp className="size-3" /> Yes
          </button>
          <button
            type="button"
            onClick={() => handleRate("UNHELPFUL")}
            className={`flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-semibold border transition-all cursor-pointer ${
              rating === "UNHELPFUL"
                ? "bg-rose-600 text-white border-rose-700"
                : "bg-white text-slate-700 border-slate-200 hover:bg-slate-100"
            }`}
          >
            <ThumbsDown className="size-3" /> No
          </button>
        </div>
      </div>

      {showComment ? (
        <div className="mt-2.5 space-y-2">
          <input
            type="text"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Optional comment on ledger accuracy..."
            className="w-full rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs text-slate-800 focus:outline-none"
          />
          <div className="flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={handleSend}
              disabled={loading}
              className="rounded-md bg-blue-600 px-3 py-1 text-xs font-bold text-white hover:bg-blue-700 cursor-pointer disabled:opacity-50"
            >
              {loading ? "Submitting..." : "Submit Feedback"}
            </button>
          </div>
          {error ? <p className="text-xs text-rose-700">{error}</p> : null}
        </div>
      ) : null}
    </div>
  );
}

export function AiAssistant({ userRole }: { userRole: Role }) {
  const modes = allowedModes(userRole);
  const [selectedMode, setSelectedMode] = useState<AiMode>(
    modes[0]?.id ?? "inventory-availability",
  );
  const [skuInput, setSkuInput] = useState("");
  const [referenceInput, setReferenceInput] = useState("");
  const [warehouseCodeInput, setWarehouseCodeInput] = useState("");
  const [sellerCodeInput, setSellerCodeInput] = useState("");
  const [draftPromptInput, setDraftPromptInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AiResult | null>(null);

  const activeModeConfig = MODES.find((m) => m.id === selectedMode);

  async function handleQuery(e?: React.FormEvent) {
    if (e) e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      let res: AiResult;
      switch (selectedMode) {
        case "inventory-availability": {
          if (!skuInput.trim()) throw new Error("Product SKU is required.");
          res = await askAiInventoryAvailability({
            sku: skuInput.trim(),
            ...(warehouseCodeInput.trim() ? { warehouse_code: warehouseCodeInput.trim() } : {}),
            ...(sellerCodeInput.trim() ? { seller_code: sellerCodeInput.trim() } : {}),
          });
          break;
        }
        case "ledger-explanation": {
          if (!skuInput.trim()) throw new Error("Product SKU is required.");
          res = await askAiLedgerExplanation({
            sku: skuInput.trim(),
            ...(warehouseCodeInput.trim() ? { warehouse_code: warehouseCodeInput.trim() } : {}),
            ...(sellerCodeInput.trim() ? { seller_code: sellerCodeInput.trim() } : {}),
          });
          break;
        }
        case "exceptions-summary": {
          res = await summarizeAiExceptionsApi({
            ...(warehouseCodeInput.trim() ? { warehouse_code: warehouseCodeInput.trim() } : {}),
            ...(sellerCodeInput.trim() ? { seller_code: sellerCodeInput.trim() } : {}),
          });
          break;
        }
        case "draft-recommendation": {
          if (!draftPromptInput.trim()) throw new Error("Recommendation prompt is required.");
          res = await createAiDraftRecommendationApi({
            recommendation_type: "TRANSFER",
            prompt: draftPromptInput.trim(),
            ...(warehouseCodeInput.trim() ? { warehouse_code: warehouseCodeInput.trim() } : {}),
            ...(sellerCodeInput.trim() ? { seller_code: sellerCodeInput.trim() } : {}),
          });
          break;
        }
        case "order": {
          if (!referenceInput.trim()) throw new Error("Order reference is required.");
          res = await askAiOrderStatus({ reference_number: referenceInput.trim() });
          break;
        }
        case "receipt": {
          if (!referenceInput.trim()) throw new Error("Receipt reference is required.");
          res = await askAiReceiptStatus({ reference_number: referenceInput.trim() });
          break;
        }
        case "transfer": {
          if (!referenceInput.trim()) throw new Error("Transfer reference is required.");
          res = await askAiTransferStatus({ reference_number: referenceInput.trim() });
          break;
        }
        case "shipment": {
          if (!referenceInput.trim()) throw new Error("Shipment reference is required.");
          res = await askAiShipmentStatus({ reference_number: referenceInput.trim() });
          break;
        }
        case "return": {
          if (!referenceInput.trim()) throw new Error("Return reference is required.");
          res = await askAiReturnStatus({ reference_number: referenceInput.trim() });
          break;
        }
        default:
          throw new Error("Unsupported inquiry mode.");
      }
      setResult(res);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("An unexpected error occurred executing AI inquiry.");
      }
    } finally {
      setLoading(false);
    }
  }

  function handleChip(mode: AiMode, sku?: string, prompt?: string) {
    setSelectedMode(mode);
    if (sku) setSkuInput(sku);
    if (prompt) setDraftPromptInput(prompt);
  }

  const safetyDecision =
    result && "safety_decision" in result ? result.safety_decision : "ALLOW_READ_ONLY";
  const providerName = result && "provider_name" in result ? result.provider_name : "google_genai";
  const answerText =
    result && "answer" in result
      ? result.answer
      : result && "narrative_summary" in result
        ? result.narrative_summary
        : result && "recommendation_summary" in result
          ? result.recommendation_summary
          : "";

  return (
    <div className="space-y-6">
      {/* Non-Negotiable Safety Notice */}
      <div className="flex items-start gap-3 rounded-xl border border-indigo-200/90 bg-indigo-50/80 p-4 text-xs text-indigo-950 shadow-xs">
        <ShieldCheck className="size-5 text-indigo-700 shrink-0 mt-0.5" />
        <div>
          <h2 className="font-bold text-indigo-950 uppercase tracking-wider text-[11px]">
            Operations AI Safety Boundary (Read-Only & Draft-Only)
          </h2>
          <p className="mt-0.5 text-indigo-900 leading-relaxed font-medium">
            The AI assistant is strictly read-only and draft-only. It answers stock, ledger, and
            status inquiries and creates proposals for warehouse manager review. It cannot adjust
            stock balances, complete receipts, dispatch shipments, or message sellers.
          </p>
        </div>
      </div>

      {/* Mode Selector Tabs */}
      <div className="flex flex-wrap gap-1.5 border-b border-slate-200 pb-3">
        {modes.map((m) => (
          <button
            key={m.id}
            onClick={() => {
              setSelectedMode(m.id);
              setError(null);
              setResult(null);
            }}
            className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition-all cursor-pointer ${
              selectedMode === m.id
                ? "bg-blue-600 text-white shadow-xs"
                : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50"
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* Query Formulation Form */}
      <Card className="p-5">
        <form onSubmit={handleQuery} className="space-y-4 text-xs">
          {activeModeConfig?.inputKind === "sku" ? (
            <div>
              <label className="block font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                Product SKU Identifier (Monospace)
              </label>
              <div className="mt-1">
                <ScannerInputField
                  value={skuInput}
                  onChange={(e) => setSkuInput(e.target.value)}
                  placeholder="e.g. SKU-1001 or scan product barcode"
                  autoFocus
                />
              </div>
            </div>
          ) : null}

          {activeModeConfig?.inputKind === "reference" ? (
            <div>
              <label className="block font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                Record Reference # or UUID
              </label>
              <div className="mt-1">
                <ScannerInputField
                  value={referenceInput}
                  onChange={(e) => setReferenceInput(e.target.value)}
                  placeholder="e.g. SO-2026-8831, 1Z99999999, RMA-2026-991, TRF-001..."
                  autoFocus
                />
              </div>
            </div>
          ) : null}

          {activeModeConfig?.inputKind === "draft" ? (
            <div>
              <label className="block font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                Manager Recommendation Prompt
              </label>
              <textarea
                rows={3}
                value={draftPromptInput}
                onChange={(e) => setDraftPromptInput(e.target.value)}
                placeholder="e.g. Suggest rebalancing 50 units of SKU-1001 from Reno (RNO) to Columbus (CMH) to meet East Coast order volume."
                className="mt-1 w-full rounded-lg border border-slate-300 p-3 text-xs text-slate-800 focus:outline-none"
              />
            </div>
          ) : null}

          {/* Optional Facility & Seller Scope */}
          <div className="grid grid-cols-2 gap-3 pt-1 border-t border-slate-100">
            <div>
              <label className="block font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                Facility Scope (Optional)
              </label>
              <input
                type="text"
                value={warehouseCodeInput}
                onChange={(e) => setWarehouseCodeInput(e.target.value)}
                placeholder="e.g. RNO or CMH"
                className="mt-1 w-full rounded-md border border-slate-300 px-2.5 py-1.5 font-mono text-xs text-slate-800 focus:outline-none"
              />
            </div>
            <div>
              <label className="block font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                Seller Code Scope (Optional)
              </label>
              <input
                type="text"
                value={sellerCodeInput}
                onChange={(e) => setSellerCodeInput(e.target.value)}
                placeholder="e.g. ACME or WHITFIELD"
                className="mt-1 w-full rounded-md border border-slate-300 px-2.5 py-1.5 font-mono text-xs text-slate-800 focus:outline-none"
              />
            </div>
          </div>

          <div className="flex items-center justify-between pt-2">
            {/* Quick Inquiry Chips */}
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-[10px] font-bold text-slate-400 uppercase">
                Dan&apos;s Quick Audits:
              </span>
              <button
                type="button"
                onClick={() => handleChip("exceptions-summary")}
                className="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-700 hover:bg-slate-200"
              >
                Summarize Exceptions
              </button>
              <button
                type="button"
                onClick={() => handleChip("inventory-availability", "SKU-1001")}
                className="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-700 hover:bg-slate-200"
              >
                Check SKU-1001 Stock
              </button>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-bold text-white shadow-xs hover:bg-blue-700 transition-colors cursor-pointer disabled:opacity-50"
            >
              {loading ? <Loader2 className="size-4 animate-spin" /> : <Send className="size-4" />}
              <span>{loading ? "Querying..." : "Execute Inquiry"}</span>
            </button>
          </div>
        </form>
      </Card>

      {error ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-800 flex items-center gap-2">
          <AlertTriangle className="size-4 text-rose-600 shrink-0" />
          <span>{error}</span>
        </div>
      ) : null}

      {/* AI Answer & Verified Ledger Payload */}
      {result ? (
        <Card className="border-t-4 border-t-blue-600 p-5 shadow-sm space-y-4 animate-rise">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
            <div className="flex items-center gap-2">
              <SafetyBadge safetyDecision={safetyDecision} />
              <ProviderBadge providerName={providerName} />
            </div>
            <span className="font-mono text-[10px] text-slate-400">
              Interaction ID: {result.interaction_id?.slice(0, 8)}
            </span>
          </div>

          {/* Formatted Answer */}
          {answerText ? (
            <div className="rounded-lg bg-slate-50 p-4 border border-slate-200 text-xs text-slate-800 leading-relaxed font-medium">
              <p className="whitespace-pre-wrap">{answerText}</p>
            </div>
          ) : null}

          {/* Structured Availability Table */}
          {"rows" in result && Array.isArray(result.rows) && result.rows.length > 0 ? (
            <CollapsibleSection
              title={`Verified Stock Records (${result.rows.length})`}
              defaultOpen
            >
              <TableShell>
                <thead>
                  <tr>
                    <Th>Warehouse</Th>
                    <Th>Seller</Th>
                    <Th>Product SKU</Th>
                    <Th className="text-right">Available Quantity</Th>
                  </tr>
                </thead>
                <tbody>
                  {result.rows.map((row: AiAvailabilityRow, idx: number) => (
                    <tr key={idx} className="hover:bg-slate-50">
                      <Td className="font-mono font-bold text-slate-900">{row.warehouse_code}</Td>
                      <Td className="font-semibold text-slate-800">{row.seller_code}</Td>
                      <Td className="font-mono text-slate-700">{row.sku}</Td>
                      <Td className="text-right font-mono font-extrabold text-slate-900">
                        {row.available_quantity}
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </TableShell>
            </CollapsibleSection>
          ) : null}

          {/* Structured Ledger Movements Table */}
          {"movements" in result &&
          Array.isArray(result.movements) &&
          result.movements.length > 0 ? (
            <CollapsibleSection
              title={`Recent Ledger Movements (${result.movements.length})`}
              defaultOpen
            >
              <TableShell>
                <thead>
                  <tr>
                    <Th>Date</Th>
                    <Th>Warehouse</Th>
                    <Th>Movement Type</Th>
                    <Th className="text-right">Quantity Delta</Th>
                  </tr>
                </thead>
                <tbody>
                  {result.movements.map((m: AiLedgerMovementRow, idx: number) => (
                    <tr key={idx} className="hover:bg-slate-50">
                      <Td className="font-mono text-slate-500">{m.recorded_at}</Td>
                      <Td className="font-mono font-semibold text-slate-800">{m.warehouse_code}</Td>
                      <Td className="text-slate-700">{m.movement_type}</Td>
                      <Td className="text-right font-mono font-extrabold text-slate-900">
                        {m.quantity_delta}
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </TableShell>
            </CollapsibleSection>
          ) : null}

          {/* Exceptions Categories */}
          {"categories" in result &&
          Array.isArray(result.categories) &&
          result.categories.length > 0 ? (
            <CollapsibleSection title="Exception Queues Breakdown" defaultOpen>
              <div className="grid gap-3 sm:grid-cols-2">
                {result.categories.map((cat: AiExceptionCategorySummary, idx: number) => (
                  <div key={idx} className="rounded-lg bg-slate-50 p-3 border border-slate-200">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-800">
                        {cat.label || cat.category.replaceAll("_", " ")}
                      </span>
                      <span className="font-mono font-bold text-rose-700 text-sm">{cat.count}</span>
                    </div>
                    <p className="mt-1 text-[11px] text-slate-600 font-mono">
                      Severity: {cat.severity}
                    </p>
                  </div>
                ))}
              </div>
            </CollapsibleSection>
          ) : null}

          {/* Feedback Capture */}
          {result.interaction_id ? <FeedbackWidget interactionId={result.interaction_id} /> : null}
        </Card>
      ) : null}
    </div>
  );
}
