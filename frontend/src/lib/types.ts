export type Role = "ADMINISTRATOR" | "WAREHOUSE_MANAGER" | "RECEIVER" | "PICKER_PACKER" | "SELLER";

export type Quantity = number | string;

export interface User {
  id: string;
  user_id?: string;
  email: string;
  name: string;
  role: Role;
  status?: string;
  token_version?: number;
  created_by_user_id?: string | null;
  created_by_name?: string | null;
  seller_ids: string[];
  warehouse_ids: string[];
  created_at?: string;
  updated_at?: string;
}

export interface Seller {
  id: string;
  code: string;
  name: string;
  contact_email?: string | null;
  contact_phone?: string | null;
  status: string;
  created_at?: string;
  updated_at?: string;
}

export interface Warehouse {
  id: string;
  code: string;
  name: string;
  address_line1?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
  timezone?: string;
  status?: string;
  utilization?: number;
  created_at?: string;
  updated_at?: string;
}

export interface Product {
  id: string;
  seller_id: string;
  sku: string;
  name: string;
  description?: string | null;
  unit_of_measure: string;
  weight?: Quantity | null;
  length?: Quantity | null;
  width?: Quantity | null;
  height?: Quantity | null;
  status: string;
  created_at?: string;
  updated_at?: string;
}

export interface Balance {
  id: string;
  seller_id: string;
  product_id: string;
  warehouse_id: string;
  location_id?: string | null;
  inventory_state: string;
  quantity: Quantity;
  version?: number;
  updated_at?: string;
}

export interface Movement {
  id: string;
  seller_id: string;
  product_id: string;
  warehouse_id: string;
  location_id?: string | null;
  inventory_state: string;
  quantity_delta: Quantity;
  movement_type: string;
  source_type: string;
  source_id: string;
  source_line_id?: string | null;
  idempotency_key?: string;
  reason_code?: string | null;
  reason_text?: string | null;
  actor_user_id?: string | null;
  correlation_id?: string | null;
  occurred_at: string;
  recorded_at?: string;
}

export interface EventLogEntry {
  id: string;
  at: string;
  label: string;
  detail: string;
}

export interface LineItem {
  id: string;
  sku: string;
  product_name: string;
  quantity: Quantity;
  note?: string | null | undefined;
}

export interface ReceiptLine {
  id: string;
  receipt_id: string;
  product_id: string;
  expected_quantity: Quantity;
  sellable_quantity: Quantity;
  damaged_quantity: Quantity;
  quarantined_quantity: Quantity;
  shortage_quantity: Quantity;
  overage_quantity: Quantity;
  notes?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface ReceiptEvent {
  id: string;
  receipt_id: string;
  event_type: string;
  actor_user_id?: string | null;
  details?: string | null;
  created_at: string;
}

export interface Receipt {
  id: string;
  receipt_number: string;
  seller_id: string;
  warehouse_id: string;
  source_type: string;
  source_reference: string;
  client_draft_id?: string | null;
  status: string;
  expected_arrival_at?: string | null;
  actual_arrival_at?: string | null;
  started_by_user_id?: string | null;
  completed_by_user_id?: string | null;
  completed_at?: string | null;
  is_duplicate_override?: boolean;
  original_receipt_id?: string | null;
  override_reason?: string | null;
  lines: ReceiptLine[];
  events: ReceiptEvent[];
  created_at: string;
  updated_at?: string;
}

export interface OrderLine {
  id: string;
  order_id: string;
  product_id: string;
  ordered_quantity: Quantity;
  reserved_quantity: Quantity;
  picked_quantity: Quantity;
  shipped_quantity: Quantity;
  backordered_quantity: Quantity;
  cancelled_quantity: Quantity;
}

export interface Order {
  id: string;
  seller_id: string;
  seller_order_number: string;
  warehouse_id: string;
  channel: string;
  status: string;
  policy_snapshot?: Record<string, unknown> | null;
  customer_name?: string | null;
  shipping_address_line1?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
  created_at: string;
  updated_at?: string;
  lines: OrderLine[];
}

export interface PickTaskLine {
  id: string;
  pick_task_id: string;
  order_line_id: string;
  product_id: string;
  location_id?: string | null;
  requested_quantity: Quantity;
  picked_quantity: Quantity;
  short_quantity: Quantity;
}

export interface PickTask {
  id: string;
  order_id: string;
  warehouse_id: string;
  assigned_user_id?: string | null;
  status: string;
  priority: number;
  completed_at?: string | null;
  created_at: string;
  updated_at?: string;
  lines: PickTaskLine[];
}

export interface Shipment {
  id: string;
  order_id: string;
  warehouse_id: string;
  carrier: string;
  service_level: string;
  tracking_number: string;
  status: string;
  shipped_at: string;
  created_at: string;
  updated_at?: string;
}

export interface TransferLine {
  id: string;
  transfer_id: string;
  product_id: string;
  requested_quantity: Quantity;
  approved_quantity: Quantity;
  dispatched_quantity: Quantity;
  received_good_quantity: Quantity;
  received_damaged_quantity: Quantity;
  missing_quantity: Quantity;
  overage_quantity: Quantity;
  notes?: string | null;
}

export interface Transfer {
  id: string;
  transfer_number: string;
  seller_id: string;
  origin_warehouse_id: string;
  destination_warehouse_id: string;
  status: string;
  created_by_user_id: string;
  approved_by_user_id?: string | null;
  dispatched_at?: string | null;
  received_at?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at?: string;
  lines: TransferLine[];
}

export interface ReturnDisposition {
  id: string;
  return_line_id: string;
  disposition_state: string;
  quantity: Quantity;
  destination_location_id?: string | null;
  notes?: string | null;
  created_at: string;
}

export interface ReturnLine {
  id: string;
  return_id: string;
  product_id?: string | null;
  expected_quantity: Quantity;
  received_quantity: Quantity;
  reason_code?: string | null;
  inspection_notes?: string | null;
  dispositions: ReturnDisposition[];
}

export interface ReturnOrder {
  id: string;
  return_number: string;
  seller_id: string;
  warehouse_id: string;
  order_id?: string | null;
  rma_number?: string | null;
  inbound_tracking_number?: string | null;
  status: string;
  received_at?: string | null;
  completed_at?: string | null;
  notes?: string | null;
  created_at: string;
  updated_at?: string;
  lines: ReturnLine[];
}

export interface ImportBatch {
  id: string;
  batch_number: string;
  status: string;
  source_notes?: string | null;
  created_by_user_id: string;
  approved_by_user_id?: string | null;
  approved_at?: string | null;
  applied_at?: string | null;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  created_at: string;
  updated_at: string;
}

export interface MigrationUploadSummary {
  batch_id: string;
  file_name: string;
  parsed_rows: number;
  staged_rows: number;
}

export interface ValidationSummary {
  batch_id: string;
  batch_number: string;
  status: string;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
}

export interface MigrationReconciliationRow {
  seller_code?: string | null;
  sku?: string | null;
  warehouse_code?: string | null;
  location_code?: string | null;
  inventory_state: string;
  staged_approved_quantity: Quantity;
  ledger_movement_quantity: Quantity;
  balance_projection_quantity: Quantity;
  variance_quantity: Quantity;
  status: string;
}

export interface MigrationReconciliationReport {
  batch_id: string;
  batch_number: string;
  batch_status: string;
  total_staged_rows: number;
  applied_movements_count: number;
  reconciliation_status: string;
  details: MigrationReconciliationRow[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

// ---------------------------------------------------------------------------
// AI Assistant types (AI Release A)
// ---------------------------------------------------------------------------

export type AiStatus = "COMPLETED" | "REFUSED" | "FAILED";

export type AiSafetyDecision = "ALLOW_READ_ONLY" | "REFUSE_MUTATION" | string;

export interface AiReference {
  record_type: string;
  record_id: string;
  label: string;
  metadata: Record<string, unknown>;
}

/** One row in inventory availability response. Quantities are strings from backend. */
export interface AiAvailabilityRow {
  seller_id: string;
  seller_code: string;
  product_id: string;
  sku: string;
  product_name: string;
  warehouse_id: string;
  warehouse_code: string;
  available_quantity: Quantity;
}

/** One row in ledger explanation response. Quantities are strings from backend. */
export interface AiLedgerMovementRow {
  movement_id: string;
  seller_id: string;
  seller_code: string;
  product_id: string;
  sku: string;
  product_name: string;
  warehouse_id: string;
  warehouse_code: string;
  inventory_state: string;
  quantity_delta: Quantity;
  movement_type: string;
  source_type: string;
  source_id: string;
  reason_code: string | null;
  reason_text: string | null;
  recorded_at: string;
}

export interface AiOperationalRecord {
  record_type: string;
  record_id: string;
  reference_number: string;
  status: string;
  seller_id: string;
  seller_code: string;
  warehouse_ids: string[];
  warehouse_codes: string[];
  summary: Record<string, unknown>;
  details: unknown[];
}

// Request shapes

export interface AiInventoryAvailabilityRequest {
  sku: string;
  seller_id?: string | null;
  seller_code?: string | null;
  warehouse_id?: string | null;
  warehouse_code?: string | null;
  prompt?: string | null;
}

export interface AiLedgerExplanationRequest {
  sku: string;
  seller_id?: string | null;
  seller_code?: string | null;
  warehouse_id?: string | null;
  warehouse_code?: string | null;
  limit?: number;
  prompt?: string | null;
}

export interface AiOperationalStatusRequest {
  record_id?: string | null;
  reference_number?: string | null;
  seller_id?: string | null;
  seller_code?: string | null;
  warehouse_id?: string | null;
  warehouse_code?: string | null;
  prompt?: string | null;
}

// Response shapes

interface AiBaseResponse {
  interaction_id: string;
  status: AiStatus;
  safety_decision: AiSafetyDecision;
  provider_name: string;
  model_name: string;
  answer: string;
  references: AiReference[];
}

export interface AiInventoryAvailabilityResponse extends AiBaseResponse {
  rows: AiAvailabilityRow[];
}

export interface AiLedgerExplanationResponse extends AiBaseResponse {
  movements: AiLedgerMovementRow[];
}

export interface AiOperationalStatusResponse extends AiBaseResponse {
  record: AiOperationalRecord | null;
}

// ---------------------------------------------------------------------------
// AI Release B Types (Audit, Feedback, Provider Health, Exceptions, Drafts)
// ---------------------------------------------------------------------------

export interface AiProviderHealth {
  enabled: boolean;
  provider_name: string;
  model_name: string;
  configured: boolean;
  status: "HEALTHY" | "KEY_MISSING" | "DISABLED";
  tested_at: string;
}

export interface AiFeedbackRequest {
  is_helpful: boolean;
  comment?: string | null | undefined;
}

export interface AiDraftRejectRequest {
  rejection_reason?: string | null | undefined;
}

export interface AiFeedbackResponse {
  feedback_id: string;
  interaction_id: string;
  actor_user_id: string;
  is_helpful: boolean;
  comment?: string | null;
  created_at: string;
}

export interface AiInteractionSummaryItem {
  id: string;
  actor_user_id: string;
  correlation_id: string;
  request_category: string;
  status: string;
  provider_name: string;
  model_name: string;
  prompt_excerpt: string;
  response_excerpt: string;
  safety_decision: string;
  refusal_reason?: string | null;
  tool_call_count: number;
  draft_action_count: number;
  feedback_count: number;
  helpful_count: number;
  unhelpful_count: number;
  created_at: string;
  completed_at?: string | null;
}

export interface AiInteractionListResponse {
  items: AiInteractionSummaryItem[];
  total_count: number;
  limit: number;
  offset: number;
}

export interface AiToolCallDetail {
  id: string;
  tool_name: string;
  status: string;
  permission_scope?: Record<string, unknown> | null;
  input_excerpt?: string | null;
  output_reference_count: number;
  error_message?: string | null;
  started_at: string;
  completed_at?: string | null;
}

export interface AiDraftActionDetail {
  id: string;
  action_type: string;
  status: string;
  target_record_type?: string | null;
  target_record_id?: string | null;
  draft_payload_excerpt?: string | null;
  requires_approval: boolean;
  approved_by_user_id?: string | null;
  approved_at?: string | null;
  rejected_at?: string | null;
  rejection_reason?: string | null;
  metadata_json?: Record<string, unknown> | null;
  created_at: string;
}

export interface AiInteractionDetailResponse {
  id: string;
  actor_user_id: string;
  correlation_id: string;
  request_category: string;
  status: string;
  provider_name: string;
  model_name: string;
  prompt_hash: string;
  prompt_excerpt: string;
  response_excerpt: string;
  safety_decision: string;
  refusal_reason?: string | null;
  seller_scope?: Record<string, unknown> | null;
  warehouse_scope?: Record<string, unknown> | null;
  retrieved_references: AiReference[];
  metadata_json?: Record<string, unknown> | null;
  tool_calls: AiToolCallDetail[];
  draft_actions: AiDraftActionDetail[];
  feedbacks: AiFeedbackResponse[];
  created_at: string;
  completed_at?: string | null;
}

export interface AiExceptionCategorySummary {
  category: string;
  label: string;
  count: number;
  severity: "HIGH" | "MEDIUM" | "LOW";
  items: Record<string, unknown>[];
}

export interface AiExceptionSummaryRequest {
  seller_id?: string | null;
  seller_code?: string | null;
  warehouse_id?: string | null;
  warehouse_code?: string | null;
  prompt?: string | null;
}

export interface AiExceptionSummaryResponse {
  interaction_id: string;
  status: string;
  safety_decision: string;
  provider_name: string;
  model_name: string;
  narrative_summary: string;
  total_exceptions: number;
  categories: AiExceptionCategorySummary[];
  references: AiReference[];
}

export interface AiDraftRecommendationRequest {
  recommendation_type: string;
  target_record_type?: string | null;
  target_record_id?: string | null;
  seller_id?: string | null;
  seller_code?: string | null;
  warehouse_id?: string | null;
  warehouse_code?: string | null;
  prompt?: string | null;
  details?: Record<string, unknown>;
}

export interface AiDraftRecommendationResponse {
  interaction_id: string;
  draft_id: string;
  action_type: string;
  status: string;
  recommendation_summary: string;
  draft_payload: Record<string, unknown>;
  references: AiReference[];
}

export interface AiDraftActionListResponse {
  items: AiDraftActionDetail[];
  total_count: number;
  limit: number;
  offset: number;
}

export interface OperationalStatusReport {
  status: "HEALTHY" | "DEGRADED" | "UNHEALTHY";
  timestamp: string;
  service: string;
  version: string;
  app_env: string;
  database: {
    status: string;
    latency_ms: number | null;
  };
  alembic_head: string;
  ai: {
    enabled: boolean;
    provider: string;
    model: string;
    status: string;
  };
  voice?: {
    stt_provider: string;
    tts_provider: string;
    stt_configured: boolean;
    tts_configured: boolean;
    default_language: string;
  };
  warnings: string[];
}

export interface VoiceParsedLine {
  quantity: string;
  inventory_state: "AVAILABLE" | "DAMAGED" | "QUARANTINED" | string;
  condition_note?: string | null;
}

export interface VoiceReceivingDraft {
  draft_id: string;
  interaction_id: string;
  transcript: string;
  confidence?: number | null;
  lines: VoiceParsedLine[];
  general_notes?: string | null;
  needs_manual_review: boolean;
  warnings: string[];
  product_id?: string | null;
  warehouse_id?: string | null;
  receipt_id?: string | null;
  status: "DRAFTED" | "APPLIED_TO_RECEIPT_DRAFT" | "DISCARDED" | string;
  safety_decision: string;
  created_at: string;
}

export interface VoiceSynthesisResponse {
  audio_base64: string;
  mime_type: string;
  provider_name: string;
  language_code: string;
}

export interface VoiceInteractionItem {
  id: string;
  actor_user_id: string;
  warehouse_id?: string | null;
  receipt_id?: string | null;
  provider_name: string;
  stt_provider: string;
  tts_provider?: string | null;
  language_code: string;
  transcript_text?: string | null;
  transcript_confidence?: number | null;
  status: string;
  created_at: string;
}

export interface VoiceInteractionListResponse {
  total: number;
  items: VoiceInteractionItem[];
}
