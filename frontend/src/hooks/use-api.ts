import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  approveMigrationBatchApi,
  approveSellerApi,
  approveTransferApi,
  applyMigrationBatchApi,
  cancelOrderApi,
  cancelReceiptApi,
  completePickTaskApi,
  completeReceiptApi,
  createMigrationBatchApi,
  createOrderApi,
  createPickTaskApi,
  createProductApi,
  createReceiptApi,
  createReturnApi,
  createShipmentApi,
  createTransferApi,
  createUserApi,
  dispatchTransferApi,
  getBalancesApi,
  getMovementsApi,
  getOrdersApi,
  getPickTasksApi,
  getProductsApi,
  updateSellerStatusApi,
  updateUserStatusApi,
  getReceiptByIdApi,
  getReceiptsApi,
  getReturnByIdApi,
  getReturnsApi,
  getSellersApi,
  getShipmentsApi,
  getTransferByIdApi,
  getTransfersApi,
  type ListReturnsParams,
  type ListTransfersParams,
  getUsersApi,
  getWarehousesApi,
  inspectReturnApi,
  overrideDuplicateReceiptApi,
  receiveReturnApi,
  receiveTransferApi,
  registerSellerPublicApi,
  reserveOrderApi,
  resolveDiscrepancyApi,
  getManagerDashboardApi,
  getManagerExceptionsApi,
  getMigrationBatchesApi,
  getMigrationReconciliationApi,
  getSellerInventoryApi,
  uploadMigrationFileApi,
  validateMigrationBatchApi,
  saveReceiptLineApi,
  getAiProviderHealthApi,
  listAiInteractionsApi,
  getAiInteractionDetailApi,
  submitAiFeedbackApi,
  summarizeAiExceptionsApi,
  createAiDraftRecommendationApi,
  listAiDraftActionsApi,
  rejectAiDraftActionApi,
  getOperationalStatusReportApi,
  transcribeReceivingAudioApi,
  parseReceivingTranscriptApi,
  synthesizeVoiceAudioApi,
  discardVoiceDraftApi,
  listVoiceInteractionsApi,
  type ListAiInteractionsParams,
  type ListAiDraftActionsParams,
} from "@/lib/api-services";

export function useBalancesQuery(params?: { seller_id?: string; warehouse_id?: string }) {
  return useQuery({
    queryKey: ["balances", params],
    queryFn: () => getBalancesApi(params),
  });
}

export function useMovementsQuery(limit = 100) {
  return useQuery({
    queryKey: ["movements", limit],
    queryFn: () => getMovementsApi(limit),
  });
}

export function useSellersQuery(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["sellers"],
    queryFn: getSellersApi,
    enabled: options?.enabled ?? true,
  });
}

export function useWarehousesQuery(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["warehouses"],
    queryFn: getWarehousesApi,
    enabled: options?.enabled ?? true,
  });
}

export function useProductsQuery(sellerId?: string, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["products", sellerId],
    queryFn: () => getProductsApi(sellerId),
    enabled: options?.enabled ?? true,
  });
}

export function useReceiptsQuery(params?: {
  seller_id?: string;
  warehouse_id?: string;
  status?: string;
}) {
  return useQuery({
    queryKey: ["receipts", params],
    queryFn: () => getReceiptsApi(params),
  });
}

export function useReceiptQuery(id: string) {
  return useQuery({
    queryKey: ["receipts", id],
    queryFn: () => getReceiptByIdApi(id),
    enabled: Boolean(id),
  });
}

export function useCreateReceiptMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createReceiptApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["receipts"] });
      queryClient.invalidateQueries({ queryKey: ["balances"] });
    },
  });
}

export function useCompleteReceiptMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: completeReceiptApi,
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ["receipts"] });
      queryClient.invalidateQueries({ queryKey: ["receipts", id] });
      queryClient.invalidateQueries({ queryKey: ["balances"] });
      queryClient.invalidateQueries({ queryKey: ["movements"] });
    },
  });
}

export function useSaveReceiptLineMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (args: {
      receiptId: string;
      line: {
        product_id: string;
        expected_quantity: number;
        sellable_quantity: number;
        damaged_quantity: number;
        quarantined_quantity: number;
        notes?: string;
      };
    }) => saveReceiptLineApi(args.receiptId, args.line),
    onSuccess: (_data, args) => {
      queryClient.invalidateQueries({ queryKey: ["receipts"] });
      queryClient.invalidateQueries({ queryKey: ["receipts", args.receiptId] });
    },
  });
}

export function useCancelReceiptMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: cancelReceiptApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["receipts"] });
    },
  });
}

export function useOverrideDuplicateReceiptMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (args: {
      receiptId: string;
      override: {
        original_receipt_id: string;
        override_reason: string;
      };
    }) => overrideDuplicateReceiptApi(args.receiptId, args.override),
    onSuccess: (_data, args) => {
      queryClient.invalidateQueries({ queryKey: ["receipts"] });
      queryClient.invalidateQueries({ queryKey: ["receipts", args.receiptId] });
    },
  });
}

export function useOrdersQuery(params?: {
  seller_id?: string;
  warehouse_id?: string;
  status?: string;
}) {
  return useQuery({
    queryKey: ["orders", params],
    queryFn: () => getOrdersApi(params),
  });
}

export function useCreateOrderMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createOrderApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
    },
  });
}

export function useReserveOrderMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: reserveOrderApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      queryClient.invalidateQueries({ queryKey: ["balances"] });
    },
  });
}

export function useCancelOrderMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (args: { id: string; reason?: string }) => cancelOrderApi(args.id, args.reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      queryClient.invalidateQueries({ queryKey: ["balances"] });
    },
  });
}

export function usePickTasksQuery(warehouseId?: string) {
  return useQuery({
    queryKey: ["pickTasks", warehouseId],
    queryFn: () => getPickTasksApi(warehouseId),
  });
}

export function useCreatePickTaskMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createPickTaskApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pickTasks"] });
      queryClient.invalidateQueries({ queryKey: ["orders"] });
    },
  });
}

export function useCompletePickTaskMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (args: {
      id: string;
      lines: Array<{ pick_task_line_id: string; picked_quantity: number; short_quantity: number }>;
    }) => completePickTaskApi(args.id, args.lines),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pickTasks"] });
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      queryClient.invalidateQueries({ queryKey: ["balances"] });
      queryClient.invalidateQueries({ queryKey: ["movements"] });
    },
  });
}

export function useShipmentsQuery() {
  return useQuery({
    queryKey: ["shipments"],
    queryFn: () => getShipmentsApi(),
  });
}

export function useCreateShipmentMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createShipmentApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["shipments"] });
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      queryClient.invalidateQueries({ queryKey: ["balances"] });
      queryClient.invalidateQueries({ queryKey: ["movements"] });
    },
  });
}

export function useTransfersQuery(params?: ListTransfersParams) {
  return useQuery({
    queryKey: ["transfers", params],
    queryFn: () => getTransfersApi(params),
  });
}

export function useTransferQuery(id: string) {
  return useQuery({
    queryKey: ["transfers", id],
    queryFn: () => getTransferByIdApi(id),
    enabled: Boolean(id),
  });
}

export function useCreateTransferMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createTransferApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transfers"] });
    },
  });
}

export function useApproveTransferMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: approveTransferApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transfers"] });
    },
  });
}

export function useDispatchTransferMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: dispatchTransferApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transfers"] });
      queryClient.invalidateQueries({ queryKey: ["balances"] });
      queryClient.invalidateQueries({ queryKey: ["movements"] });
    },
  });
}

export function useReceiveTransferMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (args: {
      id: string;
      lines: Array<{
        line_id: string;
        received_good_quantity: number;
        received_damaged_quantity?: number;
      }>;
    }) => receiveTransferApi(args.id, args.lines),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transfers"] });
      queryClient.invalidateQueries({ queryKey: ["balances"] });
      queryClient.invalidateQueries({ queryKey: ["movements"] });
    },
  });
}

export function useResolveDiscrepancyMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (args: { id: string; notes: string }) => resolveDiscrepancyApi(args.id, args.notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transfers"] });
    },
  });
}

export function useReturnsQuery(params?: ListReturnsParams) {
  return useQuery({
    queryKey: ["returns", params],
    queryFn: () => getReturnsApi(params),
  });
}

export function useReturnQuery(id: string) {
  return useQuery({
    queryKey: ["returns", id],
    queryFn: () => getReturnByIdApi(id),
    enabled: Boolean(id),
  });
}

export function useCreateReturnMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createReturnApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["returns"] });
    },
  });
}

export function useReceiveReturnMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (args: {
      id: string;
      lines: Array<{ line_id: string; received_quantity: number }>;
    }) => receiveReturnApi(args.id, args.lines),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["returns"] });
      queryClient.invalidateQueries({ queryKey: ["balances"] });
      queryClient.invalidateQueries({ queryKey: ["movements"] });
    },
  });
}

export function useInspectReturnMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (args: {
      id: string;
      dispositions: Array<{
        return_line_id: string;
        disposition_state: string;
        quantity: number;
        destination_location_id?: string;
        notes?: string;
      }>;
    }) => inspectReturnApi(args.id, args.dispositions),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["returns"] });
      queryClient.invalidateQueries({ queryKey: ["balances"] });
      queryClient.invalidateQueries({ queryKey: ["movements"] });
    },
  });
}

export function useUsersQuery(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["users"],
    queryFn: getUsersApi,
    enabled: options?.enabled ?? true,
  });
}

export function useRegisterSellerMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: registerSellerPublicApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      queryClient.invalidateQueries({ queryKey: ["sellers"] });
    },
  });
}

export function useApproveSellerMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: approveSellerApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      queryClient.invalidateQueries({ queryKey: ["sellers"] });
    },
  });
}

export function useUpdateUserStatusMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateUserStatusApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      queryClient.invalidateQueries({ queryKey: ["sellers"] });
    },
  });
}

export function useUpdateSellerStatusMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateSellerStatusApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sellers"] });
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
  });
}

export function useCreateUserMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createUserApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
  });
}

export function useCreateProductMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createProductApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["products"] });
    },
  });
}

export function useManagerDashboardQuery(warehouseId?: string) {
  return useQuery({
    queryKey: ["manager-dashboard", warehouseId],
    queryFn: () => getManagerDashboardApi(warehouseId),
  });
}

export function useManagerExceptionsQuery(warehouseId?: string) {
  return useQuery({
    queryKey: ["manager-exceptions", warehouseId],
    queryFn: () => getManagerExceptionsApi(warehouseId),
  });
}

export function useSellerInventoryQuery() {
  return useQuery({
    queryKey: ["seller-inventory"],
    queryFn: getSellerInventoryApi,
  });
}

export function useMigrationBatchesQuery() {
  return useQuery({
    queryKey: ["migration-batches"],
    queryFn: getMigrationBatchesApi,
  });
}

export function useMigrationReconciliationQuery(batchId?: string) {
  return useQuery({
    queryKey: ["migration-reconciliation", batchId],
    queryFn: () => getMigrationReconciliationApi(batchId || ""),
    enabled: Boolean(batchId),
  });
}

export function useCreateMigrationBatchMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createMigrationBatchApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["migration-batches"] });
    },
  });
}

export function useUploadMigrationFileMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: uploadMigrationFileApi,
    onSuccess: (_data, args) => {
      queryClient.invalidateQueries({ queryKey: ["migration-batches"] });
      queryClient.invalidateQueries({ queryKey: ["migration-reconciliation", args.batchId] });
    },
  });
}

export function useValidateMigrationBatchMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: validateMigrationBatchApi,
    onSuccess: (_data, batchId) => {
      queryClient.invalidateQueries({ queryKey: ["migration-batches"] });
      queryClient.invalidateQueries({ queryKey: ["migration-reconciliation", batchId] });
    },
  });
}

export function useApproveMigrationBatchMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: approveMigrationBatchApi,
    onSuccess: (_data, batchId) => {
      queryClient.invalidateQueries({ queryKey: ["migration-batches"] });
      queryClient.invalidateQueries({ queryKey: ["migration-reconciliation", batchId] });
    },
  });
}

export function useApplyMigrationBatchMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: applyMigrationBatchApi,
    onSuccess: (_data, batchId) => {
      queryClient.invalidateQueries({ queryKey: ["migration-batches"] });
      queryClient.invalidateQueries({ queryKey: ["migration-reconciliation", batchId] });
      queryClient.invalidateQueries({ queryKey: ["balances"] });
      queryClient.invalidateQueries({ queryKey: ["movements"] });
    },
  });
}

// ---------------------------------------------------------------------------
// AI Release B Hooks
// ---------------------------------------------------------------------------

export function useAiProviderHealthQuery(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["ai-provider-health"],
    queryFn: getAiProviderHealthApi,
    enabled: options?.enabled ?? true,
    refetchInterval: 30000,
  });
}

export function useAiInteractionsQuery(
  params?: ListAiInteractionsParams,
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: ["ai-interactions", params],
    queryFn: () => listAiInteractionsApi(params),
    enabled: options?.enabled ?? true,
  });
}

export function useAiInteractionDetailQuery(
  interactionId: string | null,
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: ["ai-interaction-detail", interactionId],
    queryFn: () => getAiInteractionDetailApi(interactionId!),
    enabled: Boolean(interactionId && (options?.enabled ?? true)),
  });
}

export function useSubmitAiFeedbackMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      interactionId,
      is_helpful,
      comment,
    }: {
      interactionId: string;
      is_helpful: boolean;
      comment?: string | null | undefined;
    }) => submitAiFeedbackApi(interactionId, { is_helpful, comment: comment ?? undefined }),
    onSuccess: (_data, { interactionId }) => {
      queryClient.invalidateQueries({ queryKey: ["ai-interactions"] });
      queryClient.invalidateQueries({ queryKey: ["ai-interaction-detail", interactionId] });
    },
  });
}

export function useSummarizeAiExceptionsMutation() {
  return useMutation({
    mutationFn: summarizeAiExceptionsApi,
  });
}

export function useCreateAiDraftRecommendationMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createAiDraftRecommendationApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-draft-actions"] });
      queryClient.invalidateQueries({ queryKey: ["ai-interactions"] });
    },
  });
}

export function useAiDraftActionsQuery(
  params?: ListAiDraftActionsParams,
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: ["ai-draft-actions", params],
    queryFn: () => listAiDraftActionsApi(params),
    enabled: options?.enabled ?? true,
  });
}

export function useRejectAiDraftActionMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      draftId,
      rejection_reason,
    }: {
      draftId: string;
      rejection_reason?: string | null;
    }) => rejectAiDraftActionApi(draftId, { rejection_reason }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-draft-actions"] });
      queryClient.invalidateQueries({ queryKey: ["ai-interactions"] });
    },
  });
}

export function useOperationalStatusReportQuery(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ["operational-status-report"],
    queryFn: getOperationalStatusReportApi,
    enabled: options?.enabled ?? true,
    refetchInterval: 15000,
  });
}

export function useVoiceTranscribeMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: transcribeReceivingAudioApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["voice-interactions"] });
    },
  });
}

export function useVoiceParseTranscriptMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: parseReceivingTranscriptApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["voice-interactions"] });
    },
  });
}

export function useVoiceSpeakMutation() {
  return useMutation({
    mutationFn: synthesizeVoiceAudioApi,
  });
}

export function useVoiceDiscardDraftMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ draftId, reason }: { draftId: string; reason?: string }) =>
      discardVoiceDraftApi(draftId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["voice-interactions"] });
    },
  });
}

export function useVoiceInteractionsQuery(
  params?: { limit?: number; offset?: number; status?: string },
  options?: { enabled?: boolean },
) {
  return useQuery({
    queryKey: ["voice-interactions", params],
    queryFn: () => listVoiceInteractionsApi(params),
    enabled: options?.enabled ?? true,
  });
}
