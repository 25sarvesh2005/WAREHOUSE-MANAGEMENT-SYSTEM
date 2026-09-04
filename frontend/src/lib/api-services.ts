import { apiRequest } from "./api-client";
import type {
  AiDraftActionDetail,
  AiDraftActionListResponse,
  AiDraftRecommendationRequest,
  AiDraftRecommendationResponse,
  AiDraftRejectRequest,
  AiExceptionSummaryRequest,
  AiExceptionSummaryResponse,
  AiFeedbackRequest,
  AiFeedbackResponse,
  AiInteractionDetailResponse,
  AiInteractionListResponse,
  AiInventoryAvailabilityRequest,
  AiInventoryAvailabilityResponse,
  AiLedgerExplanationRequest,
  AiLedgerExplanationResponse,
  AiOperationalStatusRequest,
  AiOperationalStatusResponse,
  AiProviderHealth,
  Balance,
  ImportBatch,
  MigrationReconciliationReport,
  MigrationUploadSummary,
  Movement,
  OperationalStatusReport,
  Order,
  PaginatedResponse,
  PickTask,
  Product,
  Receipt,
  ReturnOrder,
  Role,
  Seller,
  Shipment,
  Transfer,
  User,
  ValidationSummary,
  VoiceInteractionItem,
  VoiceInteractionListResponse,
  VoiceParsedLine,
  VoiceReceivingDraft,
  VoiceSynthesisResponse,
  Warehouse,
} from "./types";

export interface LoginPayload {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

interface AuthScopeResponse {
  user_id: string;
  email: string;
  name: string;
  role: Role;
  seller_ids: string[];
  warehouse_ids: string[];
  token_version?: number;
}

function normalizeUser(user: User | AuthScopeResponse): User {
  const id = "user_id" in user && user.user_id ? user.user_id : (user as User).id;
  return {
    ...user,
    id,
    user_id: id,
    seller_ids: user.seller_ids ?? [],
    warehouse_ids: user.warehouse_ids ?? [],
  };
}

export async function loginApi(payload: LoginPayload): Promise<TokenResponse> {
  return apiRequest<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function logoutApi(refreshToken: string): Promise<void> {
  await apiRequest<void>("/auth/logout", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export interface RegisterSellerPublicPayload {
  email: string;
  name: string;
  password: string;
  company_name: string;
  seller_code?: string;
}

export async function registerSellerPublicApi(payload: RegisterSellerPublicPayload): Promise<User> {
  const user = await apiRequest<User>("/auth/register-seller", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return normalizeUser(user);
}

export async function approveSellerApi(userId: string): Promise<User> {
  const user = await apiRequest<User>(`/users/${userId}/approve`, {
    method: "POST",
  });
  return normalizeUser(user);
}

export async function updateUserStatusApi(payload: {
  userId: string;
  status: string;
}): Promise<User> {
  const user = await apiRequest<User>(`/users/${payload.userId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status: payload.status }),
  });
  return normalizeUser(user);
}

export async function updateSellerStatusApi(payload: {
  sellerId: string;
  status: string;
}): Promise<Seller> {
  const seller = await apiRequest<Seller>(`/sellers/${payload.sellerId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status: payload.status }),
  });
  return seller;
}

export async function createUserApi(payload: {
  email: string;
  name: string;
  password: string;
  role: Role;
  warehouse_id?: string;
  seller_id?: string;
}): Promise<User> {
  const { warehouse_id, seller_id, ...userPayload } = payload;
  const user = normalizeUser(
    await apiRequest<User>("/users", {
      method: "POST",
      body: JSON.stringify({ ...userPayload, status: "ACTIVE" }),
    }),
  );

  if (warehouse_id) {
    await apiRequest("/assignments/warehouses", {
      method: "POST",
      body: JSON.stringify({
        user_id: user.id,
        warehouse_id,
        assignment_role: user.role,
      }),
    });
    user.warehouse_ids = [...new Set([...user.warehouse_ids, warehouse_id])];
  }

  if (seller_id) {
    await apiRequest("/assignments/sellers", {
      method: "POST",
      body: JSON.stringify({
        user_id: user.id,
        seller_id,
        assignment_role: user.role,
      }),
    });
    user.seller_ids = [...new Set([...user.seller_ids, seller_id])];
  }

  return user;
}

export async function getCurrentUserApi(): Promise<User> {
  const user = await apiRequest<AuthScopeResponse>("/auth/me");
  return normalizeUser(user);
}

export async function getUsersApi(): Promise<User[]> {
  const users = await apiRequest<User[]>("/users");
  return users.map(normalizeUser);
}

export async function getSellersApi(): Promise<Seller[]> {
  return apiRequest<Seller[]>("/sellers");
}

export async function getWarehousesApi(): Promise<Warehouse[]> {
  return apiRequest<Warehouse[]>("/warehouses");
}

export async function getProductsApi(sellerId?: string): Promise<Product[]> {
  const query = sellerId ? `?seller_id=${encodeURIComponent(sellerId)}` : "";
  return apiRequest<Product[]>(`/products${query}`);
}

export async function createProductApi(data: Partial<Product>): Promise<Product> {
  return apiRequest<Product>("/products", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getBalancesApi(params?: {
  seller_id?: string;
  warehouse_id?: string;
  product_id?: string;
}): Promise<Balance[]> {
  const queryParams = new URLSearchParams();
  if (params?.seller_id) queryParams.set("seller_id", params.seller_id);
  if (params?.warehouse_id) queryParams.set("warehouse_id", params.warehouse_id);
  if (params?.product_id) queryParams.set("product_id", params.product_id);
  const queryString = queryParams.toString() ? `?${queryParams.toString()}` : "";
  return apiRequest<Balance[]>(`/inventory/balances${queryString}`);
}

export async function getMovementsApi(limit = 100): Promise<Movement[]> {
  return apiRequest<Movement[]>(`/inventory/movements?limit=${limit}`);
}

export async function getReceiptsApi(params?: {
  seller_id?: string;
  warehouse_id?: string;
  status?: string;
}): Promise<Receipt[]> {
  const queryParams = new URLSearchParams();
  if (params?.seller_id) queryParams.set("seller_id", params.seller_id);
  if (params?.warehouse_id) queryParams.set("warehouse_id", params.warehouse_id);
  if (params?.status) queryParams.set("status", params.status);
  const queryString = queryParams.toString() ? `?${queryParams.toString()}` : "";
  return apiRequest<Receipt[]>(`/receipts${queryString}`);
}

export async function getReceiptByIdApi(id: string): Promise<Receipt> {
  return apiRequest<Receipt>(`/receipts/${id}`);
}

export async function createReceiptApi(payload: {
  seller_id: string;
  warehouse_id: string;
  source_type: string;
  source_reference: string;
  client_draft_id?: string;
  expected_arrival_at?: string;
}): Promise<Receipt> {
  return apiRequest<Receipt>("/receipts", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function saveReceiptLineApi(
  receiptId: string,
  payload: {
    product_id: string;
    expected_quantity: number;
    sellable_quantity: number;
    damaged_quantity: number;
    quarantined_quantity: number;
    notes?: string;
  },
): Promise<Receipt["lines"][number]> {
  return apiRequest<Receipt["lines"][number]>(`/receipts/${receiptId}/lines`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function completeReceiptApi(id: string): Promise<Receipt> {
  return apiRequest<Receipt>(`/receipts/${id}/complete`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function cancelReceiptApi(id: string): Promise<Receipt> {
  return apiRequest<Receipt>(`/receipts/${id}/cancel`, {
    method: "POST",
  });
}

export async function overrideDuplicateReceiptApi(
  id: string,
  payload: {
    original_receipt_id: string;
    override_reason: string;
  },
): Promise<Receipt> {
  return apiRequest<Receipt>(`/receipts/${id}/override-duplicate`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getOrdersApi(params?: {
  seller_id?: string;
  warehouse_id?: string;
  status?: string;
}): Promise<Order[]> {
  const queryParams = new URLSearchParams();
  if (params?.seller_id) queryParams.set("seller_id", params.seller_id);
  if (params?.warehouse_id) queryParams.set("warehouse_id", params.warehouse_id);
  if (params?.status) queryParams.set("status", params.status);
  const queryString = queryParams.toString() ? `?${queryParams.toString()}` : "";
  return apiRequest<Order[]>(`/orders${queryString}`);
}

export async function getOrderByIdApi(id: string): Promise<Order> {
  return apiRequest<Order>(`/orders/${id}`);
}

export async function createOrderApi(payload: {
  seller_id: string;
  seller_order_number: string;
  warehouse_id: string;
  channel?: string;
  customer_name?: string;
  shipping_address_line1?: string;
  city?: string;
  state?: string;
  postal_code?: string;
  lines: Array<{ product_id: string; ordered_quantity: number }>;
}): Promise<Order> {
  return apiRequest<Order>("/orders", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function reserveOrderApi(id: string): Promise<Order> {
  return apiRequest<Order>(`/orders/${id}/reserve`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export async function cancelOrderApi(id: string, reason?: string): Promise<Order> {
  return apiRequest<Order>(`/orders/${id}/cancel`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export async function getPickTasksApi(warehouseId?: string): Promise<PickTask[]> {
  const query = warehouseId ? `?warehouse_id=${encodeURIComponent(warehouseId)}` : "";
  return apiRequest<PickTask[]>(`/pick-tasks${query}`);
}

export async function createPickTaskApi(payload: {
  order_id: string;
  assigned_user_id?: string;
  priority?: number;
}): Promise<PickTask> {
  return apiRequest<PickTask>("/pick-tasks", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function completePickTaskApi(
  taskId: string,
  lines: Array<{ pick_task_line_id: string; picked_quantity: number; short_quantity: number }>,
): Promise<PickTask> {
  return apiRequest<PickTask>(`/pick-tasks/${taskId}/complete`, {
    method: "POST",
    body: JSON.stringify({ lines }),
  });
}

export async function getShipmentsApi(params?: {
  order_id?: string;
  status?: string;
}): Promise<Shipment[]> {
  const queryParams = new URLSearchParams();
  if (params?.order_id) queryParams.set("order_id", params.order_id);
  if (params?.status) queryParams.set("status", params.status);
  const queryString = queryParams.toString() ? `?${queryParams.toString()}` : "";
  return apiRequest<Shipment[]>(`/shipments${queryString}`);
}

export async function createShipmentApi(payload: {
  order_id: string;
  warehouse_id: string;
  carrier: string;
  service_level: string;
  tracking_number: string;
  packages: Array<{
    box_type: string;
    weight_lbs?: number;
    length_in?: number;
    width_in?: number;
    height_in?: number;
  }>;
}): Promise<Shipment> {
  return apiRequest<Shipment>("/shipments", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export interface ListTransfersParams {
  limit?: number | undefined;
  offset?: number | undefined;
  q?: string | undefined;
  seller_id?: string | undefined;
  origin_warehouse_id?: string | undefined;
  destination_warehouse_id?: string | undefined;
  status?: string | undefined;
}

export async function getTransfersApi(
  params?: ListTransfersParams,
): Promise<PaginatedResponse<Transfer>> {
  const searchParams = new URLSearchParams();
  if (params) {
    if (params.limit !== undefined && params.limit !== null) {
      searchParams.set("limit", String(params.limit));
    }
    if (params.offset !== undefined && params.offset !== null) {
      searchParams.set("offset", String(params.offset));
    }
    if (params.q?.trim()) {
      searchParams.set("q", params.q.trim());
    }
    if (params.seller_id?.trim()) {
      searchParams.set("seller_id", params.seller_id.trim());
    }
    if (params.origin_warehouse_id?.trim()) {
      searchParams.set("origin_warehouse_id", params.origin_warehouse_id.trim());
    }
    if (params.destination_warehouse_id?.trim()) {
      searchParams.set("destination_warehouse_id", params.destination_warehouse_id.trim());
    }
    if (params.status?.trim()) {
      searchParams.set("status", params.status.trim());
    }
  }
  const queryString = searchParams.toString();
  const endpoint = queryString ? `/transfers?${queryString}` : "/transfers";
  return apiRequest<PaginatedResponse<Transfer>>(endpoint);
}

export async function getTransferByIdApi(id: string): Promise<Transfer> {
  return apiRequest<Transfer>(`/transfers/${id}`);
}

export async function createTransferApi(payload: {
  seller_id: string;
  origin_warehouse_id: string;
  destination_warehouse_id: string;
  lines: Array<{ product_id: string; requested_quantity: number; notes?: string }>;
  notes?: string;
}): Promise<Transfer> {
  return apiRequest<Transfer>("/transfers", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function approveTransferApi(id: string): Promise<Transfer> {
  return apiRequest<Transfer>(`/transfers/${id}/approve`, {
    method: "POST",
  });
}

export async function dispatchTransferApi(id: string): Promise<Transfer> {
  return apiRequest<Transfer>(`/transfers/${id}/dispatch`, {
    method: "POST",
  });
}

export async function receiveTransferApi(
  id: string,
  lines: Array<{
    line_id: string;
    received_good_quantity: number;
    received_damaged_quantity?: number;
  }>,
): Promise<Transfer> {
  return apiRequest<Transfer>(`/transfers/${id}/receive`, {
    method: "POST",
    body: JSON.stringify({ lines }),
  });
}

export async function resolveDiscrepancyApi(id: string, notes: string): Promise<Transfer> {
  return apiRequest<Transfer>(`/transfers/${id}/resolve-discrepancy`, {
    method: "POST",
    body: JSON.stringify({ notes }),
  });
}

export interface ListReturnsParams {
  limit?: number | undefined;
  offset?: number | undefined;
  q?: string | undefined;
  seller_id?: string | undefined;
  warehouse_id?: string | undefined;
  status?: string | undefined;
}

export async function getReturnsApi(
  params?: ListReturnsParams,
): Promise<PaginatedResponse<ReturnOrder>> {
  const searchParams = new URLSearchParams();
  if (params) {
    if (params.limit !== undefined && params.limit !== null) {
      searchParams.set("limit", String(params.limit));
    }
    if (params.offset !== undefined && params.offset !== null) {
      searchParams.set("offset", String(params.offset));
    }
    if (params.q?.trim()) {
      searchParams.set("q", params.q.trim());
    }
    if (params.seller_id?.trim()) {
      searchParams.set("seller_id", params.seller_id.trim());
    }
    if (params.warehouse_id?.trim()) {
      searchParams.set("warehouse_id", params.warehouse_id.trim());
    }
    if (params.status?.trim()) {
      searchParams.set("status", params.status.trim());
    }
  }
  const queryString = searchParams.toString();
  const endpoint = queryString ? `/returns?${queryString}` : "/returns";
  return apiRequest<PaginatedResponse<ReturnOrder>>(endpoint);
}

export async function getReturnByIdApi(id: string): Promise<ReturnOrder> {
  return apiRequest<ReturnOrder>(`/returns/${id}`);
}

export async function createReturnApi(payload: {
  seller_id: string;
  warehouse_id: string;
  order_id?: string;
  rma_number?: string;
  inbound_tracking_number?: string;
  is_unidentified?: boolean;
  notes?: string;
  lines: Array<{
    product_id?: string;
    expected_quantity: number;
    received_quantity?: number;
    reason_code?: string;
    inspection_notes?: string;
  }>;
}): Promise<ReturnOrder> {
  return apiRequest<ReturnOrder>("/returns", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function receiveReturnApi(
  id: string,
  lines: Array<{ line_id: string; received_quantity: number }>,
): Promise<ReturnOrder> {
  return apiRequest<ReturnOrder>(`/returns/${id}/receive`, {
    method: "POST",
    body: JSON.stringify({ lines }),
  });
}

export async function inspectReturnApi(
  id: string,
  dispositions: Array<{
    return_line_id: string;
    disposition_state: string;
    quantity: number;
    destination_location_id?: string;
    notes?: string;
  }>,
): Promise<ReturnOrder> {
  return apiRequest<ReturnOrder>(`/returns/${id}/inspect`, {
    method: "POST",
    body: JSON.stringify({ dispositions }),
  });
}

export async function getManagerDashboardApi(warehouseId?: string): Promise<{
  balances_by_state: Record<string, number>;
  open_receipts_count: number;
  pending_pick_tasks_count: number;
  active_transfers_count: number;
  uninspected_returns_count: number;
}> {
  const query = warehouseId ? `?warehouse_id=${encodeURIComponent(warehouseId)}` : "";
  return apiRequest(`/manager/dashboard${query}`);
}

export async function getManagerExceptionsApi(warehouseId?: string): Promise<{
  short_pick_exceptions: Array<Record<string, unknown>>;
  transfer_discrepancies: Array<Record<string, unknown>>;
  unidentified_returns: Array<Record<string, unknown>>;
}> {
  const query = warehouseId ? `?warehouse_id=${encodeURIComponent(warehouseId)}` : "";
  return apiRequest(`/manager/exceptions${query}`);
}

export async function getReconciliationReportApi(warehouseId?: string): Promise<{
  total_balance_keys: number;
  matches: number;
  variances_count: number;
  is_clean: boolean;
  variances: Array<Record<string, unknown>>;
}> {
  const query = warehouseId ? `?warehouse_id=${encodeURIComponent(warehouseId)}` : "";
  return apiRequest(`/reports/inventory-reconciliation${query}`);
}

export async function getSellerInventoryApi(): Promise<Balance[]> {
  return apiRequest<Balance[]>("/seller/inventory");
}

export async function getSellerOrdersApi(): Promise<Order[]> {
  return apiRequest<Order[]>("/seller/orders");
}

export async function getMigrationBatchesApi(): Promise<ImportBatch[]> {
  return apiRequest<ImportBatch[]>("/migration/batches");
}

export async function createMigrationBatchApi(sourceNotes: string): Promise<ImportBatch> {
  return apiRequest<ImportBatch>("/migration/batches", {
    method: "POST",
    body: JSON.stringify({ source_notes: sourceNotes || null }),
  });
}

export async function uploadMigrationFileApi(args: {
  batchId: string;
  file: File;
}): Promise<MigrationUploadSummary> {
  const formData = new FormData();
  formData.append("file", args.file);
  return apiRequest<MigrationUploadSummary>(`/migration/batches/${args.batchId}/upload`, {
    method: "POST",
    body: formData,
  });
}

export async function validateMigrationBatchApi(batchId: string): Promise<ValidationSummary> {
  return apiRequest<ValidationSummary>(`/migration/batches/${batchId}/validate`, {
    method: "POST",
  });
}

export async function approveMigrationBatchApi(batchId: string): Promise<ImportBatch> {
  return apiRequest<ImportBatch>(`/migration/batches/${batchId}/approve`, {
    method: "POST",
  });
}

export async function applyMigrationBatchApi(batchId: string): Promise<ImportBatch> {
  return apiRequest<ImportBatch>(`/migration/batches/${batchId}/apply`, {
    method: "POST",
  });
}

export async function getMigrationReconciliationApi(
  batchId: string,
): Promise<MigrationReconciliationReport> {
  return apiRequest<MigrationReconciliationReport>(`/migration/batches/${batchId}/reconciliation`);
}

// ---------------------------------------------------------------------------
// AI Assistant service functions (AI Release A)
// All calls route through the FastAPI backend — never direct to Gemini.
// ---------------------------------------------------------------------------

export async function askAiInventoryAvailability(
  payload: AiInventoryAvailabilityRequest,
): Promise<AiInventoryAvailabilityResponse> {
  return apiRequest<AiInventoryAvailabilityResponse>("/ai/inventory/availability", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function askAiLedgerExplanation(
  payload: AiLedgerExplanationRequest,
): Promise<AiLedgerExplanationResponse> {
  return apiRequest<AiLedgerExplanationResponse>("/ai/inventory/ledger-explanation", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function askAiOrderStatus(
  payload: AiOperationalStatusRequest,
): Promise<AiOperationalStatusResponse> {
  return apiRequest<AiOperationalStatusResponse>("/ai/status/order", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function askAiReceiptStatus(
  payload: AiOperationalStatusRequest,
): Promise<AiOperationalStatusResponse> {
  return apiRequest<AiOperationalStatusResponse>("/ai/status/receipt", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function askAiTransferStatus(
  payload: AiOperationalStatusRequest,
): Promise<AiOperationalStatusResponse> {
  return apiRequest<AiOperationalStatusResponse>("/ai/status/transfer", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function askAiShipmentStatus(
  payload: AiOperationalStatusRequest,
): Promise<AiOperationalStatusResponse> {
  return apiRequest<AiOperationalStatusResponse>("/ai/status/shipment", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function askAiReturnStatus(
  payload: AiOperationalStatusRequest,
): Promise<AiOperationalStatusResponse> {
  return apiRequest<AiOperationalStatusResponse>("/ai/status/return", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// ---------------------------------------------------------------------------
// AI Release B service functions (Audit, Provider Health, Feedback, Drafts)
// ---------------------------------------------------------------------------

export async function getAiProviderHealthApi(): Promise<AiProviderHealth> {
  return apiRequest<AiProviderHealth>("/ai/admin/provider-health");
}

export interface ListAiInteractionsParams {
  status?: string | undefined;
  provider_name?: string | undefined;
  request_category?: string | undefined;
  actor_user_id?: string | undefined;
  start_date?: string | undefined;
  end_date?: string | undefined;
  limit?: number | undefined;
  offset?: number | undefined;
}

export async function listAiInteractionsApi(
  params: ListAiInteractionsParams = {},
): Promise<AiInteractionListResponse> {
  const query = new URLSearchParams();
  if (params.status) query.set("status", params.status);
  if (params.provider_name) query.set("provider_name", params.provider_name);
  if (params.request_category) query.set("request_category", params.request_category);
  if (params.actor_user_id) query.set("actor_user_id", params.actor_user_id);
  if (params.start_date) query.set("start_date", params.start_date);
  if (params.end_date) query.set("end_date", params.end_date);
  if (params.limit !== undefined) query.set("limit", String(params.limit));
  if (params.offset !== undefined) query.set("offset", String(params.offset));

  const qs = query.toString();
  return apiRequest<AiInteractionListResponse>(`/ai/admin/interactions${qs ? `?${qs}` : ""}`);
}

export async function getAiInteractionDetailApi(
  interactionId: string,
): Promise<AiInteractionDetailResponse> {
  return apiRequest<AiInteractionDetailResponse>(`/ai/admin/interactions/${interactionId}`);
}

export async function submitAiFeedbackApi(
  interactionId: string,
  payload: AiFeedbackRequest,
): Promise<AiFeedbackResponse> {
  return apiRequest<AiFeedbackResponse>(`/ai/interactions/${interactionId}/feedback`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function summarizeAiExceptionsApi(
  payload: AiExceptionSummaryRequest = {},
): Promise<AiExceptionSummaryResponse> {
  return apiRequest<AiExceptionSummaryResponse>("/ai/exceptions/summary", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function createAiDraftRecommendationApi(
  payload: AiDraftRecommendationRequest,
): Promise<AiDraftRecommendationResponse> {
  return apiRequest<AiDraftRecommendationResponse>("/ai/drafts/recommendation", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export interface ListAiDraftActionsParams {
  status?: string | undefined;
  action_type?: string | undefined;
  interaction_id?: string | undefined;
  limit?: number | undefined;
  offset?: number | undefined;
}

export async function listAiDraftActionsApi(
  params: ListAiDraftActionsParams = {},
): Promise<AiDraftActionListResponse> {
  const query = new URLSearchParams();
  if (params.status) query.set("status", params.status);
  if (params.action_type) query.set("action_type", params.action_type);
  if (params.interaction_id) query.set("interaction_id", params.interaction_id);
  if (params.limit !== undefined) query.set("limit", String(params.limit));
  if (params.offset !== undefined) query.set("offset", String(params.offset));

  const qs = query.toString();
  return apiRequest<AiDraftActionListResponse>(`/ai/drafts${qs ? `?${qs}` : ""}`);
}

export async function rejectAiDraftActionApi(
  draftId: string,
  payload: AiDraftRejectRequest = {},
): Promise<AiDraftActionDetail> {
  return apiRequest<AiDraftActionDetail>(`/ai/drafts/${draftId}/reject`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getOperationalStatusReportApi(): Promise<OperationalStatusReport> {
  // Directly hit /health/status relative to backend host
  const res = await fetch("/health/status", {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch operational status: ${res.statusText}`);
  }
  return res.json();
}

export async function transcribeReceivingAudioApi(
  formData: FormData,
): Promise<VoiceReceivingDraft> {
  return apiRequest<VoiceReceivingDraft>("/voice/receiving/transcribe", {
    method: "POST",
    body: formData,
  });
}

export async function parseReceivingTranscriptApi(payload: {
  transcript: string;
  warehouse_id?: string | null;
  product_id?: string | null;
  receipt_id?: string | null;
  language_code?: string;
}): Promise<VoiceReceivingDraft> {
  return apiRequest<VoiceReceivingDraft>("/voice/receiving/parse-transcript", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function synthesizeVoiceAudioApi(payload: {
  text: string;
  language_code?: string;
}): Promise<VoiceSynthesisResponse> {
  return apiRequest<VoiceSynthesisResponse>("/voice/speak", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function discardVoiceDraftApi(
  draftId: string,
  reason?: string,
): Promise<VoiceReceivingDraft> {
  return apiRequest<VoiceReceivingDraft>(`/voice/drafts/${draftId}/discard`, {
    method: "POST",
    body: JSON.stringify({ reason: reason || null }),
  });
}

export async function listVoiceInteractionsApi(
  params: {
    limit?: number;
    offset?: number;
    status?: string;
  } = {},
): Promise<VoiceInteractionListResponse> {
  const query = new URLSearchParams();
  if (params.limit !== undefined) query.set("limit", String(params.limit));
  if (params.offset !== undefined) query.set("offset", String(params.offset));
  if (params.status) query.set("status", params.status);

  const qs = query.toString();
  return apiRequest<VoiceInteractionListResponse>(`/voice/interactions${qs ? `?${qs}` : ""}`);
}
