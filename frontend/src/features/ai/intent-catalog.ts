import {
  askAiInventoryAvailability,
  askAiLedgerExplanation,
  askAiOrderStatus,
  askAiReceiptStatus,
  askAiReturnStatus,
  askAiShipmentStatus,
  askAiTransferStatus,
  createAiDraftRecommendationApi,
  summarizeAiExceptionsApi,
} from "@/lib/api-services";
import type {
  AiDraftRecommendationRequest,
  AiExceptionSummaryRequest,
  AiInventoryAvailabilityRequest,
  AiInventoryAvailabilityResponse,
  AiLedgerExplanationRequest,
  AiLedgerExplanationResponse,
  AiOperationalStatusResponse,
  AiExceptionSummaryResponse,
  AiDraftRecommendationResponse,
  Role,
} from "@/lib/types";

export type AiCategory = "inventory" | "tracking" | "exceptions" | "rebalance";

export interface ScopeOptions {
  warehouseCode?: string;
  sellerCode?: string;
}

export type AiResult =
  | AiInventoryAvailabilityResponse
  | AiLedgerExplanationResponse
  | AiOperationalStatusResponse
  | AiExceptionSummaryResponse
  | AiDraftRecommendationResponse;

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

export const AI_INTENTS: IntentConfig[] = [
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

export function detectIntentFromText(text: string): string | null {
  const clean = text.trim().toUpperCase();
  if (clean.startsWith("ORD-")) return "order-status";
  if (clean.startsWith("REC-") || clean.startsWith("RCV-")) return "receipt-status";
  if (clean.startsWith("TRK-") || clean.startsWith("SHP-")) return "shipment-status";
  if (clean.startsWith("TRF-")) return "transfer-status";
  if (clean.startsWith("RMA-") || clean.startsWith("RET-")) return "return-status";
  if (clean.startsWith("SKU-") || clean.startsWith("PROD-")) return "inventory-availability";
  if (clean.includes("EXCEPTION") || clean.includes("FLAGGED") || clean.includes("BOTTLENECK"))
    return "exceptions-summary";
  if (clean.includes("REBALANCE") || clean.includes("TRANSFER RECOMMENDATION"))
    return "rebalance-recommendation";
  if (clean.includes("LEDGER") || clean.includes("AUDIT") || clean.includes("VARIANCE"))
    return "ledger-explanation";
  return null;
}
