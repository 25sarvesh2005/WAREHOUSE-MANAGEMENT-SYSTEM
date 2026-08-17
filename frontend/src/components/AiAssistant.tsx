import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Bot,
  Box,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Copy,
  Database,
  Filter,
  History,
  Info,
  Layers,
  Loader2,
  Mic,
  Package,
  PackageCheck,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  Truck,
  X,
} from "lucide-react";
import React, { useState } from "react";
import { ReceivingVoiceDraftPanel } from "@/components/ReceivingVoiceDraftPanel";
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
  AiDraftRecommendationRequest,
  AiDraftRecommendationResponse,
  AiExceptionCategorySummary,
  AiExceptionSummaryRequest,
  AiExceptionSummaryResponse,
  AiInventoryAvailabilityRequest,
  AiInventoryAvailabilityResponse,
  AiLedgerExplanationRequest,
  AiLedgerExplanationResponse,
  AiLedgerMovementRow,
  AiOperationalStatusResponse,
  Role,
} from "@/lib/types";

// ---------------------------------------------------------------------------
// Intent & Mode Configuration
// ---------------------------------------------------------------------------

export type AiCategory = "inventory" | "tracking" | "exceptions" | "rebalance";

export interface ScopeOptions {
  warehouseCode?: string;
  sellerCode?: string;
}

export interface IntentConfig {
  id: string;
  category: AiCategory;
  title: string;
  shortLabel: string;
  placeholder: string;
  example: string;
  description: string;
  allowedRoles: Role[];
  execute: (query: string, scope: ScopeOptions) => Promise<AiResult>;
}

export type AiResult =
  | AiInventoryAvailabilityResponse
  | AiLedgerExplanationResponse
  | AiOperationalStatusResponse
  | AiExceptionSummaryResponse
  | AiDraftRecommendationResponse;

interface RecentQuery {
  id: string;
  timestamp: string;
  intentId: string;
  query: string;
  result: AiResult;
}

// ---------------------------------------------------------------------------
// Predefined Supported Query Intents
// ---------------------------------------------------------------------------

const INTENTS: IntentConfig[] = [
  {
    id: "inventory-availability",
    category: "inventory",
    title: "AI Warehouse Copilot & Stock Inquiry",
    shortLabel: "Stock & Quantities",
    placeholder:
      "Ask any stock question (e.g., 'product with 0 quantity', 'which headphones are in stock?', 'lowest stock items', 'SKU-AURA-ANC100')...",
    example: "product with 0 quantity",
    description:
      "Natural language query of live warehouse stock, zero/low inventory levels, and facility distributions.",
    allowedRoles: [],
    execute: (query, scope) => {
      const payload: AiInventoryAvailabilityRequest = { sku: query.trim() };
      if (scope.warehouseCode) payload.warehouse_code = scope.warehouseCode;
      if (scope.sellerCode) payload.seller_code = scope.sellerCode;
      return askAiInventoryAvailability(payload);
    },
  },
  {
    id: "ledger-explanation",
    category: "inventory",
    title: "Audit Ledger & Movement History",
    shortLabel: "Ledger Audit",
    placeholder: "Enter Product SKU to explain stock variance & ledger journal",
    example: "SKU-AURA-ANC100",
    description:
      "Natural language analysis of balance shifts, adjustments, receipts, and order reserves.",
    allowedRoles: ["ADMINISTRATOR", "WAREHOUSE_MANAGER", "RECEIVER"],
    execute: (query, scope) => {
      const payload: AiLedgerExplanationRequest = { sku: query.trim() };
      if (scope.warehouseCode) payload.warehouse_code = scope.warehouseCode;
      if (scope.sellerCode) payload.seller_code = scope.sellerCode;
      return askAiLedgerExplanation(payload);
    },
  },
  {
    id: "order-status",
    category: "tracking",
    title: "Track Order & Fulfillment",
    shortLabel: "Order Status",
    placeholder: "Enter Order Reference Number (e.g., ORD-2026-1001)",
    example: "ORD-2026-1001",
    description: "Detailed status check on allocation, pick task assignment, and shipment stage.",
    allowedRoles: ["ADMINISTRATOR", "WAREHOUSE_MANAGER", "PICKER_PACKER", "SELLER"],
    execute: (query) => askAiOrderStatus({ reference_number: query.trim() }),
  },
  {
    id: "receipt-status",
    category: "tracking",
    title: "Inspect Inbound Receipt",
    shortLabel: "Receipt Inspection",
    placeholder: "Enter Receipt Number (e.g., REC-2026-001)",
    example: "REC-2026-001",
    description: "Inspect arriving lines, received quantities, and location putaway status.",
    allowedRoles: ["ADMINISTRATOR", "WAREHOUSE_MANAGER", "RECEIVER"],
    execute: (query) => askAiReceiptStatus({ reference_number: query.trim() }),
  },
  {
    id: "shipment-status",
    category: "tracking",
    title: "Trace Outbound Shipment",
    shortLabel: "Shipment Tracking",
    placeholder: "Enter Tracking Number or Shipment Ref (e.g., 1Z999AA10123456784)",
    example: "1Z999AA10123456784",
    description: "Carrier dispatch confirmation, label status, and delivery milestones.",
    allowedRoles: ["ADMINISTRATOR", "WAREHOUSE_MANAGER", "PICKER_PACKER", "SELLER"],
    execute: (query) => askAiShipmentStatus({ reference_number: query.trim() }),
  },
  {
    id: "transfer-status",
    category: "tracking",
    title: "Track Warehouse Transfer",
    shortLabel: "Inter-facility Transfer",
    placeholder: "Enter Transfer Reference (e.g., TRF-2026-101)",
    example: "TRF-2026-101",
    description: "Monitor bicoastal transfer movement between Reno and Columbus warehouses.",
    allowedRoles: ["ADMINISTRATOR", "WAREHOUSE_MANAGER"],
    execute: (query) => askAiTransferStatus({ reference_number: query.trim() }),
  },
  {
    id: "return-status",
    category: "tracking",
    title: "Track Customer Return (RMA)",
    shortLabel: "RMA Returns",
    placeholder: "Enter Return or RMA Reference (e.g., RMA-2026-501)",
    example: "RMA-2026-501",
    description: "Disposition, customer restock status, and inspection findings.",
    allowedRoles: ["ADMINISTRATOR", "WAREHOUSE_MANAGER", "RECEIVER", "SELLER"],
    execute: (query) => askAiReturnStatus({ reference_number: query.trim() }),
  },
  {
    id: "exceptions-summary",
    category: "exceptions",
    title: "Summarize Operational Exceptions",
    shortLabel: "Exceptions Report",
    placeholder: "Leave blank or describe scope (e.g., 'Reno facility exceptions')",
    example: "Summarize active facility hold reasons and unfulfilled reserves",
    description:
      "Aggregates quarantined stock, flagged receipts, and delayed pick tasks across warehouses.",
    allowedRoles: ["ADMINISTRATOR", "WAREHOUSE_MANAGER", "RECEIVER"],
    execute: (_query, scope) => {
      const payload: AiExceptionSummaryRequest = {};
      if (scope.warehouseCode) payload.warehouse_code = scope.warehouseCode;
      if (scope.sellerCode) payload.seller_code = scope.sellerCode;
      return summarizeAiExceptionsApi(payload);
    },
  },
  {
    id: "rebalance-recommendation",
    category: "rebalance",
    title: "Generate Bicoastal Rebalance Draft",
    shortLabel: "Stock Rebalancing",
    placeholder: "Enter target SKU or leave blank to evaluate bicoastal fulfillment velocity",
    example: "Evaluate bicoastal stock velocity and draft transfer",
    description:
      "AI-suggested stock transfer from Reno (surplus) to Columbus (deficit) to optimize shipping zone transit.",
    allowedRoles: ["ADMINISTRATOR", "WAREHOUSE_MANAGER"],
    execute: (_query, scope) => {
      const payload: AiDraftRecommendationRequest = { recommendation_type: "REBALANCE" };
      if (scope.warehouseCode) payload.warehouse_code = scope.warehouseCode;
      if (scope.sellerCode) payload.seller_code = scope.sellerCode;
      return createAiDraftRecommendationApi(payload);
    },
  },
];

// Helper to auto-detect intent from query string
function detectIntentFromText(text: string): string | null {
  const clean = text.trim().toUpperCase();
  if (clean.startsWith("ORD-")) return "order-status";
  if (clean.startsWith("RCV-")) return "receipt-status";
  if (clean.startsWith("TRK-") || clean.startsWith("SHP-")) return "shipment-status";
  if (clean.startsWith("TRF-")) return "transfer-status";
  if (clean.startsWith("RMA-") || clean.startsWith("RET-")) return "return-status";
  if (clean.startsWith("SKU-") || clean.startsWith("PROD-")) return "inventory-availability";
  if (clean.includes("EXCEPTION") || clean.includes("FLAGGED") || clean.includes("BOTTLENECK"))
    return "exceptions-summary";
  if (clean.includes("REBALANCE") || clean.includes("TRANSFER RECOMMENDATION"))
    return "draft-recommendation";
  if (clean.includes("LEDGER") || clean.includes("AUDIT") || clean.includes("VARIANCE"))
    return "ledger-explanation";
  return null;
}

// ---------------------------------------------------------------------------
// Sub-Components
// ---------------------------------------------------------------------------

function ProviderBadge({ providerName }: { providerName?: string }) {
  const isGemini = providerName === "google_genai";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
        isGemini
          ? "bg-indigo-50 text-indigo-700 border border-indigo-200"
          : "bg-slate-100 text-slate-700 border border-slate-200"
      }`}
    >
      {isGemini ? (
        <Sparkles className="size-3 text-indigo-600" />
      ) : (
        <Bot className="size-3 text-slate-500" />
      )}
      {isGemini ? "Gemini 2.0 Flash" : "Rule Engine"}
    </span>
  );
}

function SafetyBadge({ safetyDecision }: { safetyDecision?: string }) {
  const isAllow = !safetyDecision || safetyDecision === "ALLOW_READ_ONLY";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
        isAllow
          ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
          : "bg-rose-50 text-rose-700 border border-rose-200"
      }`}
    >
      <ShieldCheck className="size-3 text-emerald-600" />
      {isAllow ? "Read-Only Verified" : safetyDecision?.replaceAll("_", " ")}
    </span>
  );
}

function FeedbackWidget({ interactionId }: { interactionId: string }) {
  const [rated, setRated] = useState<"HELPFUL" | "UNHELPFUL" | null>(null);
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  async function handleRate(value: "HELPFUL" | "UNHELPFUL") {
    setRated(value);
    setLoading(true);
    try {
      await submitAiFeedbackApi(interactionId, {
        is_helpful: value === "HELPFUL",
      });
      setSubmitted(true);
    } catch {
      // Non-blocking UI feedback error
    } finally {
      setLoading(false);
    }
  }

  if (submitted) {
    return (
      <div className="flex items-center gap-1.5 text-xs font-medium text-emerald-700 bg-emerald-50 px-3 py-1 rounded-md border border-emerald-200">
        <CheckCircle2 className="size-3.5" />
        Feedback recorded. Thank you!
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground">
      <span>Was this accurate?</span>
      <button
        type="button"
        disabled={loading}
        onClick={() => handleRate("HELPFUL")}
        className={`flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium transition-colors border cursor-pointer ${
          rated === "HELPFUL"
            ? "bg-emerald-600 text-white border-emerald-700"
            : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
        }`}
      >
        <ThumbsUp className="size-3" /> Yes
      </button>
      <button
        type="button"
        disabled={loading}
        onClick={() => handleRate("UNHELPFUL")}
        className={`flex items-center gap-1 rounded px-2 py-0.5 text-xs font-medium transition-colors border cursor-pointer ${
          rated === "UNHELPFUL"
            ? "bg-rose-600 text-white border-rose-700"
            : "bg-white text-slate-700 border-slate-200 hover:bg-slate-50"
        }`}
      >
        <ThumbsDown className="size-3" /> No
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export function AiAssistant({ userRole }: { userRole: Role }) {
  const availableIntents = INTENTS.filter(
    (i) => i.allowedRoles.length === 0 || i.allowedRoles.includes(userRole),
  );

  const [activeCategory, setActiveCategory] = useState<AiCategory>("inventory");
  const [selectedIntentId, setSelectedIntentId] = useState<string>(
    availableIntents[0]?.id ?? "inventory-availability",
  );

  const [queryInput, setQueryInput] = useState("");
  const [warehouseCode, setWarehouseCode] = useState("");
  const [sellerCode, setSellerCode] = useState("");
  const [showFilters, setShowFilters] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState(false);
  const [feedbackGiven, setFeedbackGiven] = useState<"up" | "down" | null>(null);
  const [showVoiceDock, setShowVoiceDock] = useState(false);
  const [activeResult, setActiveResult] = useState<AiResult | null>(null);
  const [recentQueries, setRecentQueries] = useState<RecentQuery[]>([]);
  const [showAuditDetails, setShowAuditDetails] = useState(false);

  const activeIntent =
    availableIntents.find((i) => i.id === selectedIntentId) ?? availableIntents[0]!;

  // Handle Intent Selection
  function handleSelectIntent(intent: IntentConfig) {
    setSelectedIntentId(intent.id);
    setActiveCategory(intent.category);
    setError(null);
  }

  // Quick Action Starter click
  function handleQuickStarter(intentId: string, prefill: string) {
    const target = availableIntents.find((i) => i.id === intentId);
    if (target) {
      setSelectedIntentId(target.id);
      setActiveCategory(target.category);
      setQueryInput(prefill);
      void executeSearch(target, prefill);
    }
  }

  // Core Search Execution
  async function executeSearch(intent = activeIntent, query = queryInput) {
    // If user typed an ID that belongs to another domain, switch automatically
    const detected = detectIntentFromText(query);
    let resolvedIntent = intent;
    if (detected && detected !== intent.id) {
      const match = availableIntents.find((i) => i.id === detected);
      if (match) {
        resolvedIntent = match;
        setSelectedIntentId(match.id);
        setActiveCategory(match.category);
      }
    }

    if (
      resolvedIntent.id !== "exceptions-summary" &&
      resolvedIntent.id !== "draft-recommendation" &&
      !query.trim()
    ) {
      setError(`Please enter a valid ${resolvedIntent.title.toLowerCase()} identifier.`);
      return;
    }

    setLoading(true);
    setError(null);
    setActiveResult(null);

    try {
      const scopePayload: ScopeOptions = {};
      if (warehouseCode.trim()) scopePayload.warehouseCode = warehouseCode.trim();
      if (sellerCode.trim()) scopePayload.sellerCode = sellerCode.trim();

      const result = await resolvedIntent.execute(query, scopePayload);

      setActiveResult(result);

      // Record in recent session history
      const newHistoryItem: RecentQuery = {
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        intentId: resolvedIntent.id,
        query: query.trim() || resolvedIntent.title,
        result,
      };
      setRecentQueries((prev) => [newHistoryItem, ...prev.slice(0, 4)]);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Unable to process AI inquiry. Please verify your query and try again.");
      }
    } finally {
      setLoading(false);
    }
  }

  function handleFormSubmit(e: React.FormEvent) {
    e.preventDefault();
    void executeSearch();
  }

  function handleCopyAuditId(id: string) {
    void navigator.clipboard.writeText(id);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  }

  // Extract structured properties from result
  const answerText =
    activeResult && "answer" in activeResult
      ? activeResult.answer
      : activeResult && "narrative_summary" in activeResult
        ? activeResult.narrative_summary
        : activeResult && "recommendation_summary" in activeResult
          ? activeResult.recommendation_summary
          : "";

  const auditId =
    activeResult && "interaction_id" in activeResult ? activeResult.interaction_id : "";

  const provider =
    activeResult && "provider_name" in activeResult ? activeResult.provider_name : "google_genai";

  const safety =
    activeResult && "safety_decision" in activeResult
      ? activeResult.safety_decision
      : "ALLOW_READ_ONLY";

  // Category counts
  const categoryIntents = availableIntents.filter((i) => i.category === activeCategory);

  return (
    <div className="space-y-6">
      {/* ─────────────────────────────────────────────────────────────────
          1. Hero Header & Safety Banner
          ───────────────────────────────────────────────────────────────── */}
      <div className="relative overflow-hidden rounded-2xl border border-border bg-gradient-to-br from-white via-slate-50/50 to-primary-tint/30 p-6 shadow-card">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-primary text-white shadow-md">
              <Sparkles className="size-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-bold text-foreground">Operations AI Assistant</h2>
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 border border-emerald-200">
                  <ShieldCheck className="size-3 text-emerald-600" />
                  Read-Only Safe
                </span>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                Ask questions about real-time inventory balances, trace order lifecycles, audit
                ledger shifts, or review facility bottlenecks.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0 text-xs text-muted-foreground bg-white/80 backdrop-blur-xs px-3 py-1.5 rounded-xl border border-border">
            <Info className="size-3.5 text-primary" />
            <span>AI cannot mutate stock or finalize shipments</span>
          </div>
        </div>

        {/* ───────────────────────────────────────────────────────────────
            2. Category Selector Pills
            ─────────────────────────────────────────────────────────────── */}
        <div className="mt-6 flex flex-wrap items-center gap-2 border-t border-border/70 pt-4">
          <span className="text-xs font-semibold text-muted-foreground mr-1">Inquiry Domain:</span>
          <button
            type="button"
            onClick={() => {
              setActiveCategory("inventory");
              const first = availableIntents.find((i) => i.category === "inventory");
              if (first) setSelectedIntentId(first.id);
            }}
            className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all cursor-pointer ${
              activeCategory === "inventory"
                ? "bg-primary text-white shadow-xs"
                : "bg-white text-slate-700 hover:bg-slate-100 border border-border"
            }`}
          >
            <Box className="size-3.5" />
            Inventory & Stock
          </button>

          <button
            type="button"
            onClick={() => {
              setActiveCategory("tracking");
              const first = availableIntents.find((i) => i.category === "tracking");
              if (first) setSelectedIntentId(first.id);
            }}
            className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all cursor-pointer ${
              activeCategory === "tracking"
                ? "bg-primary text-white shadow-xs"
                : "bg-white text-slate-700 hover:bg-slate-100 border border-border"
            }`}
          >
            <Truck className="size-3.5" />
            Track & Trace
          </button>

          <button
            type="button"
            onClick={() => {
              setActiveCategory("exceptions");
              const first = availableIntents.find((i) => i.category === "exceptions");
              if (first) setSelectedIntentId(first.id);
            }}
            className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all cursor-pointer ${
              activeCategory === "exceptions"
                ? "bg-primary text-white shadow-xs"
                : "bg-white text-slate-700 hover:bg-slate-100 border border-border"
            }`}
          >
            <AlertTriangle className="size-3.5" />
            Facility Exceptions
          </button>

          <button
            type="button"
            onClick={() => {
              setShowVoiceDock(false);
              setActiveCategory("rebalance");
              const first = availableIntents.find((i) => i.category === "rebalance");
              if (first) setSelectedIntentId(first.id);
            }}
            className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all cursor-pointer ${
              !showVoiceDock && activeCategory === "rebalance"
                ? "bg-primary text-white shadow-xs"
                : "bg-white text-slate-700 hover:bg-slate-100 border border-border"
            }`}
          >
            <RefreshCw className="size-3.5" />
            Smart Rebalance
          </button>

          <button
            type="button"
            onClick={() => setShowVoiceDock(!showVoiceDock)}
            className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold transition-all cursor-pointer ${
              showVoiceDock
                ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md"
                : "bg-primary-tint text-primary hover:bg-primary hover:text-white border border-primary/30"
            }`}
          >
            <Mic className="size-3.5" />
            🎙️ Voice Dock Intake
          </button>
        </div>

        {/* Sub-intent options within category */}
        {!showVoiceDock && categoryIntents.length > 1 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {categoryIntents.map((intent) => (
              <button
                key={intent.id}
                type="button"
                onClick={() => handleSelectIntent(intent)}
                className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors cursor-pointer ${
                  selectedIntentId === intent.id
                    ? "bg-primary/10 text-primary font-bold border border-primary/30"
                    : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                {intent.shortLabel}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Voice Receiving Dock Station (When Activated) */}
      {showVoiceDock && (
        <div className="animate-rise">
          <ReceivingVoiceDraftPanel />
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────────
          3. Smart Search / Query Input Bar
          ───────────────────────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-border bg-white p-5 shadow-card">
        <form onSubmit={handleFormSubmit} className="space-y-3">
          <div className="flex items-center justify-between">
            <label
              htmlFor="ai-query-input"
              className="text-xs font-bold uppercase tracking-wider text-slate-500"
            >
              {activeIntent.title}
            </label>
            <button
              type="button"
              onClick={() => setShowFilters(!showFilters)}
              className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline cursor-pointer"
            >
              <Filter className="size-3" />
              {showFilters ? "Hide Scope Filters" : "Facility / Seller Filters"}
            </button>
          </div>

          <div className="relative flex items-center">
            <div className="pointer-events-none absolute left-3.5 text-slate-400">
              <Search className="size-5" />
            </div>
            <input
              id="ai-query-input"
              type="text"
              value={queryInput}
              onChange={(e) => setQueryInput(e.target.value)}
              placeholder={activeIntent.placeholder}
              className="w-full rounded-xl border border-border bg-slate-50/50 py-3.5 pl-11 pr-32 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all"
            />
            {queryInput && (
              <button
                type="button"
                onClick={() => setQueryInput("")}
                className="absolute right-28 p-1 text-slate-400 hover:text-slate-600 cursor-pointer"
              >
                <X className="size-4" />
              </button>
            )}
            <button
              type="submit"
              disabled={loading}
              className="absolute right-2 inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-xs font-bold text-white shadow-xs transition-all hover:bg-primary-dark cursor-pointer disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="size-3.5 animate-spin" />
                  <span>Thinking...</span>
                </>
              ) : (
                <>
                  <span>Ask AI</span>
                  <ArrowRight className="size-3.5" />
                </>
              )}
            </button>
          </div>

          {/* Optional Filter Drawer */}
          {showFilters && (
            <div className="flex flex-wrap gap-3 rounded-xl border border-slate-200/80 bg-slate-50/80 p-3 pt-2 text-xs">
              <div className="flex-1 min-w-[180px]">
                <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                  Target Warehouse:
                </label>
                <select
                  value={warehouseCode}
                  onChange={(e) => setWarehouseCode(e.target.value)}
                  className="w-full rounded-lg border border-border bg-white px-2.5 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="">All Facilities (Bicoastal)</option>
                  <option value="RNO">Reno, NV Hub (RNO)</option>
                  <option value="CMH">Columbus, OH Hub (CMH)</option>
                </select>
              </div>

              <div className="flex-1 min-w-[180px]">
                <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                  Filter by Seller Code (Optional):
                </label>
                <input
                  type="text"
                  value={sellerCode}
                  onChange={(e) => setSellerCode(e.target.value)}
                  placeholder="e.g. SL-DEMO"
                  className="w-full rounded-lg border border-border bg-white px-2.5 py-1.5 text-xs text-foreground placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
            </div>
          )}

          {error && (
            <div className="flex items-start gap-2 rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">
              <AlertCircle className="size-4 shrink-0 mt-0.5 text-rose-600" />
              <span>{error}</span>
            </div>
          )}
        </form>
      </div>

      {/* ─────────────────────────────────────────────────────────────────
          4. Quick Prompt Starter Chips (Shown when no search has run)
          ───────────────────────────────────────────────────────────────── */}
      {!activeResult && !loading && (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
            <span className="font-semibold uppercase tracking-wider text-slate-500">
              Suggested Operations Inquiries
            </span>
            <span>Click any prompt to launch</span>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            <button
              type="button"
              onClick={() =>
                handleQuickStarter("inventory-availability", "product with 0 quantity")
              }
              className="group flex flex-col items-start rounded-xl border border-border bg-white p-4 text-left shadow-xs transition-all hover:border-primary/50 hover:shadow-md cursor-pointer"
            >
              <div className="flex size-8 items-center justify-center rounded-lg bg-primary-tint text-primary group-hover:bg-primary group-hover:text-white transition-colors">
                <Box className="size-4" />
              </div>
              <h4 className="mt-2.5 text-xs font-bold text-foreground group-hover:text-primary transition-colors">
                Zero Stock & Shortage Check
              </h4>
              <p className="mt-1 text-[11px] text-muted-foreground">
                Inquire on any products with 0 quantity or stock shortages across facilities.
              </p>
            </button>

            <button
              type="button"
              onClick={() =>
                handleQuickStarter(
                  "inventory-availability",
                  "which headphones do we have in stock?",
                )
              }
              className="group flex flex-col items-start rounded-xl border border-border bg-white p-4 text-left shadow-xs transition-all hover:border-primary/50 hover:shadow-md cursor-pointer"
            >
              <div className="flex size-8 items-center justify-center rounded-lg bg-emerald-50 text-emerald-600 group-hover:bg-emerald-600 group-hover:text-white transition-colors">
                <Sparkles className="size-4" />
              </div>
              <h4 className="mt-2.5 text-xs font-bold text-foreground group-hover:text-primary transition-colors">
                Natural Language Category Search
              </h4>
              <p className="mt-1 text-[11px] text-muted-foreground">
                "Which headphones do we have in stock?" — Multi-warehouse category balance audit.
              </p>
            </button>

            <button
              type="button"
              onClick={() => handleQuickStarter("order-status", "ORD-2026-1001")}
              className="group flex flex-col items-start rounded-xl border border-border bg-white p-4 text-left shadow-xs transition-all hover:border-primary/50 hover:shadow-md cursor-pointer"
            >
              <div className="flex size-8 items-center justify-center rounded-lg bg-blue-50 text-blue-600 group-hover:bg-blue-600 group-hover:text-white transition-colors">
                <Truck className="size-4" />
              </div>
              <h4 className="mt-2.5 text-xs font-bold text-foreground group-hover:text-primary transition-colors">
                Track Customer Order
              </h4>
              <p className="mt-1 text-[11px] text-muted-foreground">
                Trace order allocation, picking progress, and shipment tracking for ORD-2026-1001.
              </p>
            </button>

            <button
              type="button"
              onClick={() => handleQuickStarter("ledger-explanation", "SKU-AURA-ANC100")}
              className="group flex flex-col items-start rounded-xl border border-border bg-white p-4 text-left shadow-xs transition-all hover:border-primary/50 hover:shadow-md cursor-pointer"
            >
              <div className="flex size-8 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
                <Layers className="size-4" />
              </div>
              <h4 className="mt-2.5 text-xs font-bold text-foreground group-hover:text-primary transition-colors">
                Audit Ledger Shifts
              </h4>
              <p className="mt-1 text-[11px] text-muted-foreground">
                Review immutable journal entries and explain variances for SKU-AURA-ANC100.
              </p>
            </button>

            <button
              type="button"
              onClick={() => handleQuickStarter("receipt-status", "REC-2026-001")}
              className="group flex flex-col items-start rounded-xl border border-border bg-white p-4 text-left shadow-xs transition-all hover:border-primary/50 hover:shadow-md cursor-pointer"
            >
              <div className="flex size-8 items-center justify-center rounded-lg bg-teal-50 text-teal-600 group-hover:bg-teal-600 group-hover:text-white transition-colors">
                <PackageCheck className="size-4" />
              </div>
              <h4 className="mt-2.5 text-xs font-bold text-foreground group-hover:text-primary transition-colors">
                Inspect Inbound Receipt
              </h4>
              <p className="mt-1 text-[11px] text-muted-foreground">
                Audit 40ft container intake lines and putaway status for REC-2026-001.
              </p>
            </button>

            <button
              type="button"
              onClick={() =>
                handleQuickStarter("exceptions-summary", "Summarize facility hold reasons")
              }
              className="group flex flex-col items-start rounded-xl border border-border bg-white p-4 text-left shadow-xs transition-all hover:border-primary/50 hover:shadow-md cursor-pointer"
            >
              <div className="flex size-8 items-center justify-center rounded-lg bg-amber-50 text-amber-600 group-hover:bg-amber-600 group-hover:text-white transition-colors">
                <AlertTriangle className="size-4" />
              </div>
              <h4 className="mt-2.5 text-xs font-bold text-foreground group-hover:text-primary transition-colors">
                Warehouse Exceptions
              </h4>
              <p className="mt-1 text-[11px] text-muted-foreground">
                Review bottlenecks, unfulfilled orders, and quarantined inventory across hubs.
              </p>
            </button>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────────
          5. Response Presentation Card (When Result Is Ready)
          ───────────────────────────────────────────────────────────────── */}
      {activeResult && (
        <div className="space-y-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
          <div className="rounded-2xl border border-border bg-white p-6 shadow-card space-y-6">
            {/* Header / Meta bar */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
              <div className="flex items-center gap-3">
                <div className="flex size-10 items-center justify-center rounded-xl bg-primary-tint text-primary">
                  <Bot className="size-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-foreground">
                    {activeIntent.title} Response
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    Inquiry:{" "}
                    <span className="font-semibold text-foreground">
                      {queryInput || activeIntent.title}
                    </span>
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <ProviderBadge providerName={provider} />
                <SafetyBadge safetyDecision={safety} />
              </div>
            </div>

            {/* AI Narrative Bubble */}
            <div className="rounded-xl border border-primary/20 bg-primary-tint/30 p-4 text-sm leading-relaxed text-foreground shadow-2xs">
              <p className="font-medium whitespace-pre-wrap">{answerText}</p>
            </div>

            {/* ── Domain-Specific Structured Details ── */}

            {/* A. Inventory Availability Breakdown */}
            {"rows" in activeResult &&
              Array.isArray(activeResult.rows) &&
              activeResult.rows.length > 0 && (
                <div className="space-y-3">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    Facility Stock Breakdown
                  </h4>
                  <div className="overflow-x-auto rounded-xl border border-border">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-50 border-b border-border text-slate-600 font-semibold">
                        <tr>
                          <th className="py-2.5 px-3.5">Facility</th>
                          <th className="py-2.5 px-3.5">Product SKU</th>
                          <th className="py-2.5 px-3.5">Product Name</th>
                          <th className="py-2.5 px-3.5">Seller</th>
                          <th className="py-2.5 px-3.5 text-right font-bold">Available Quantity</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border text-slate-800">
                        {activeResult.rows.map((row: AiAvailabilityRow, idx: number) => (
                          <tr key={`${row.warehouse_code}-${idx}`} className="hover:bg-slate-50/70">
                            <td className="py-2.5 px-3.5 font-semibold text-foreground">
                              {row.warehouse_code}
                            </td>
                            <td className="py-2.5 px-3.5 font-mono text-slate-600">{row.sku}</td>
                            <td className="py-2.5 px-3.5 text-slate-700">{row.product_name}</td>
                            <td className="py-2.5 px-3.5 text-slate-500">{row.seller_code}</td>
                            <td className="py-2.5 px-3.5 text-right text-emerald-700 font-bold">
                              {Number(row.available_quantity).toLocaleString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

            {/* B. Ledger Movements Breakdown */}
            {"movements" in activeResult && Array.isArray(activeResult.movements) && (
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Ledger Movement History
                </h4>
                <div className="overflow-x-auto rounded-xl border border-border">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 border-b border-border text-slate-600 font-semibold">
                      <tr>
                        <th className="py-2.5 px-3.5">Facility</th>
                        <th className="py-2.5 px-3.5">Movement Type</th>
                        <th className="py-2.5 px-3.5">State</th>
                        <th className="py-2.5 px-3.5 text-right font-bold">Quantity Delta</th>
                        <th className="py-2.5 px-3.5">Reason / Note</th>
                        <th className="py-2.5 px-3.5 text-right">Timestamp</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border text-slate-800">
                      {activeResult.movements.map((mov: AiLedgerMovementRow) => (
                        <tr key={mov.movement_id} className="hover:bg-slate-50/70">
                          <td className="py-2.5 px-3.5 font-semibold text-foreground">
                            {mov.warehouse_code}
                          </td>
                          <td className="py-2.5 px-3.5 font-medium">{mov.movement_type}</td>
                          <td className="py-2.5 px-3.5 font-mono text-[11px] text-slate-600">
                            {mov.inventory_state}
                          </td>
                          <td
                            className={`py-2.5 px-3.5 text-right font-bold ${
                              Number(mov.quantity_delta) >= 0 ? "text-emerald-700" : "text-rose-700"
                            }`}
                          >
                            {Number(mov.quantity_delta) >= 0
                              ? `+${mov.quantity_delta}`
                              : mov.quantity_delta}
                          </td>
                          <td className="py-2.5 px-3.5 text-slate-500">
                            {mov.reason_text || "Standard Movement"}
                          </td>
                          <td className="py-2.5 px-3.5 text-right text-slate-400 font-mono text-[10px]">
                            {new Date(mov.recorded_at).toLocaleDateString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* C. Operational Status (Order / Receipt / Shipment / Transfer / Return) */}
            {"record" in activeResult && activeResult.record && (
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Operational Record Attributes
                </h4>
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <div className="rounded-xl border border-border bg-slate-50/50 p-3">
                    <span className="block text-[10px] font-bold uppercase text-slate-400">
                      Reference #
                    </span>
                    <span className="mt-0.5 block text-xs font-bold font-mono text-foreground">
                      {activeResult.record.reference_number}
                    </span>
                  </div>

                  <div className="rounded-xl border border-border bg-slate-50/50 p-3">
                    <span className="block text-[10px] font-bold uppercase text-slate-400">
                      Status
                    </span>
                    <span className="mt-0.5 inline-block rounded bg-primary-tint px-2 py-0.5 text-xs font-bold text-primary">
                      {activeResult.record.status}
                    </span>
                  </div>

                  <div className="rounded-xl border border-border bg-slate-50/50 p-3">
                    <span className="block text-[10px] font-bold uppercase text-slate-400">
                      Seller
                    </span>
                    <span className="mt-0.5 block text-xs font-semibold text-foreground">
                      {activeResult.record.seller_code}
                    </span>
                  </div>

                  <div className="rounded-xl border border-border bg-slate-50/50 p-3">
                    <span className="block text-[10px] font-bold uppercase text-slate-400">
                      Facilities
                    </span>
                    <span className="mt-0.5 block text-xs font-semibold text-foreground">
                      {activeResult.record.warehouse_codes?.join(", ") || "All"}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* D. Exceptions Categories Breakdown */}
            {"categories" in activeResult && Array.isArray(activeResult.categories) && (
              <div className="space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Exception Categories
                </h4>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  {activeResult.categories.map((cat: AiExceptionCategorySummary) => (
                    <div
                      key={cat.category}
                      className="rounded-xl border border-amber-200 bg-amber-50/50 p-3.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-amber-900">
                          {cat.label || cat.category}
                        </span>
                        <span className="rounded-full bg-amber-200 px-2 py-0.5 text-xs font-bold text-amber-800">
                          {cat.count}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-amber-800">
                        Severity: <span className="font-semibold">{cat.severity}</span>
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* E. Draft Recommendation Details */}
            {"draft_id" in activeResult && activeResult.draft_id && (
              <div className="rounded-xl border border-purple-200 bg-purple-50/40 p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <RefreshCw className="size-4 text-purple-700" />
                    <h4 className="text-xs font-bold text-purple-900">
                      Draft Transfer Generated ({activeResult.draft_id})
                    </h4>
                  </div>
                  <span className="rounded bg-purple-200 px-2 py-0.5 text-xs font-bold text-purple-800">
                    PENDING APPROVAL
                  </span>
                </div>
                <p className="text-xs text-purple-900">
                  This draft is saved in staging and ready for manager review. No records or
                  balances have been mutated.
                </p>
              </div>
            )}

            {/* Footer with Feedback and Audit Disclosure */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4">
              {auditId ? (
                <FeedbackWidget interactionId={auditId} />
              ) : (
                <span className="text-xs text-muted-foreground">Read-only operational inquiry</span>
              )}

              {auditId && (
                <button
                  type="button"
                  onClick={() => setShowAuditDetails(!showAuditDetails)}
                  className="inline-flex items-center gap-1 text-xs font-medium text-slate-500 hover:text-slate-800 cursor-pointer"
                >
                  <Database className="size-3.5 text-slate-400" />
                  {showAuditDetails ? "Hide Audit Evidence" : "View Audit Trace"}
                </button>
              )}
            </div>

            {/* Audit Details Panel */}
            {showAuditDetails && auditId && (
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5 text-xs text-slate-700 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-800">Audit Trail Record:</span>
                  <button
                    type="button"
                    onClick={() => handleCopyAuditId(auditId)}
                    className="inline-flex items-center gap-1 rounded bg-white px-2 py-1 text-[11px] font-semibold text-slate-600 border border-slate-200 hover:bg-slate-100 cursor-pointer"
                  >
                    <Copy className="size-3" />
                    {copiedId ? "Copied!" : "Copy Audit ID"}
                  </button>
                </div>
                <p className="font-mono text-[11px] text-slate-500 break-all">{auditId}</p>
                <div className="text-[11px] text-slate-500 pt-1">
                  Every query executed against the read-only AI engine produces an immutable audit
                  record in PostgreSQL.
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────────
          6. Session History Drawer (Recent Queries)
          ───────────────────────────────────────────────────────────────── */}
      {recentQueries.length > 0 && (
        <div className="rounded-2xl border border-border bg-white p-4 shadow-card">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
            <History className="size-3.5 text-slate-400" />
            <span>Recent Session Inquiries</span>
          </div>

          <div className="divide-y divide-border">
            {recentQueries.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => {
                  const matched = availableIntents.find((i) => i.id === item.intentId);
                  if (matched) {
                    setSelectedIntentId(matched.id);
                    setActiveCategory(matched.category);
                    setQueryInput(item.query);
                    setActiveResult(item.result);
                  }
                }}
                className="flex w-full items-center justify-between py-2 text-left text-xs transition-colors hover:bg-slate-50 px-2 rounded-lg cursor-pointer"
              >
                <div className="flex items-center gap-2">
                  <span className="font-medium text-foreground">{item.query}</span>
                  <span className="text-[11px] text-muted-foreground">({item.intentId})</span>
                </div>
                <span className="text-[11px] text-slate-400">{item.timestamp}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
