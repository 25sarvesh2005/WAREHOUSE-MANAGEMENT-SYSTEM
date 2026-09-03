import { useState } from "react";
import {
  Activity,
  AlertTriangle,
  Bot,
  CheckCircle2,
  ChevronRight,
  Download,
  Eye,
  FileCode,
  Loader2,
  RefreshCw,
  Search,
  Shield,
  Sparkles,
  ThumbsDown,
  ThumbsUp,
  XCircle,
} from "lucide-react";
import {
  useAiDraftActionsQuery,
  useAiInteractionDetailQuery,
  useAiInteractionsQuery,
  useAiProviderHealthQuery,
  useRejectAiDraftActionMutation,
} from "@/hooks/use-api";
import { AppDialog } from "@/components/AppDialog";
import { Button, Card, EmptyState, LoadingState, TableShell, Td, Th } from "@/components/ui-kit";
import type { AiDraftActionDetail, AiInteractionSummaryItem } from "@/lib/types";

export function AiAuditPanel() {
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [categoryFilter, setCategoryFilter] = useState<string>("");
  const [selectedInteractionId, setSelectedInteractionId] = useState<string | null>(null);
  const [rejectingDraftId, setRejectingDraftId] = useState<string | null>(null);
  const [rejectionReason, setRejectionReason] = useState("");

  const healthQuery = useAiProviderHealthQuery();
  const interactionsQuery = useAiInteractionsQuery({
    status: statusFilter || undefined,
    request_category: categoryFilter || undefined,
    limit: 50,
  });
  const detailQuery = useAiInteractionDetailQuery(selectedInteractionId, {
    enabled: Boolean(selectedInteractionId),
  });
  const draftsQuery = useAiDraftActionsQuery({ limit: 20 });
  const rejectDraftMutation = useRejectAiDraftActionMutation();

  const health = healthQuery.data;
  const interactions = interactionsQuery.data?.items ?? [];
  const drafts = draftsQuery.data?.items ?? [];
  const detail = detailQuery.data;

  async function handleRejectDraft(draftId: string) {
    try {
      await rejectDraftMutation.mutateAsync({
        draftId,
        rejection_reason: rejectionReason.trim() || "Rejected by manager via audit console.",
      });
      setRejectingDraftId(null);
      setRejectionReason("");
    } catch {
      // Handled by mutation
    }
  }

  return (
    <div className="space-y-6">
      {/* 1. Provider Health Card */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-4 flex flex-col justify-between border-l-4 border-l-primary">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Provider Engine
            </span>
            <Bot className="size-4 text-primary" />
          </div>
          <div className="mt-2">
            <div className="text-lg font-bold text-foreground">
              {health?.provider_name === "google_genai"
                ? "Google Gemini"
                : "Deterministic Fallback"}
            </div>
            <div className="text-xs text-muted-foreground font-mono mt-0.5">
              {health?.model_name || "rule-engine-v1"}
            </div>
          </div>
          <div className="mt-3 flex items-center gap-1.5 text-xs">
            <span
              className={`size-2 rounded-full ${
                health?.enabled ? "bg-status-green animate-pulse" : "bg-muted-foreground"
              }`}
            />
            <span className="font-medium text-foreground">
              {health?.enabled ? "AI Integration Enabled" : "Read-only Rules Only"}
            </span>
          </div>
        </Card>

        <Card className="p-4 flex flex-col justify-between border-l-4 border-l-status-green">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Provider Readiness
            </span>
            <Activity className="size-4 text-status-green" />
          </div>
          <div className="mt-2">
            <div className="text-lg font-bold text-foreground">
              {health?.status === "HEALTHY" ? (
                <span className="text-status-green">Operational & Healthy</span>
              ) : health?.status === "KEY_MISSING" ? (
                <span className="text-status-amber">API Key Not Configured</span>
              ) : (
                <span className="text-muted-foreground">Provider Disabled</span>
              )}
            </div>
            <div className="text-xs text-muted-foreground mt-0.5">
              {health?.configured ? "Backend API Key Validated" : "Using safe local fallback"}
            </div>
          </div>
          <div className="mt-3 text-[11px] text-muted-foreground">
            Checked: {health?.tested_at ? new Date(health.tested_at).toLocaleTimeString() : "—"}
          </div>
        </Card>

        <Card className="p-4 flex flex-col justify-between border-l-4 border-l-status-blue">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Safety Guardrails
            </span>
            <Shield className="size-4 text-primary" />
          </div>
          <div className="mt-2">
            <div className="text-lg font-bold text-foreground">Strict Read & Draft Only</div>
            <div className="text-xs text-muted-foreground mt-0.5">
              Direct DB mutations blocked by policy
            </div>
          </div>
          <div className="mt-3 flex items-center gap-1 text-[11px] text-primary font-semibold">
            <CheckCircle2 className="size-3.5" />
            <span>Tenant scope & RBAC verified</span>
          </div>
        </Card>
      </div>

      {/* 2. Pending AI Draft Recommendations (if any) */}
      {drafts.length > 0 ? (
        <Card className="p-5 space-y-3 border-status-blue/40 bg-status-blue/5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="size-4 text-primary" />
              <h3 className="font-semibold text-foreground text-sm">
                AI Draft Recommendations ({drafts.filter((d) => d.status === "DRAFTED").length}{" "}
                pending review)
              </h3>
            </div>
            <span className="text-xs text-muted-foreground">
              Requires human approval before execution
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-border/80 text-muted-foreground">
                  <th className="py-2 pr-3 font-semibold">Action Type</th>
                  <th className="py-2 pr-3 font-semibold">Target Record</th>
                  <th className="py-2 pr-3 font-semibold">Status</th>
                  <th className="py-2 pr-3 font-semibold">Created</th>
                  <th className="py-2 text-right font-semibold">Review</th>
                </tr>
              </thead>
              <tbody>
                {drafts.map((d: AiDraftActionDetail) => (
                  <tr
                    key={d.id}
                    className="border-b border-border/40 last:border-0 hover:bg-muted/30"
                  >
                    <td className="py-2 pr-3 font-medium text-foreground">{d.action_type}</td>
                    <td className="py-2 pr-3 text-muted-foreground font-mono">
                      {d.target_record_type
                        ? `${d.target_record_type.toUpperCase()} #${d.target_record_id?.slice(0, 8) || "—"}`
                        : "—"}
                    </td>
                    <td className="py-2 pr-3">
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                          d.status === "DRAFTED"
                            ? "bg-status-amber/20 text-status-amber"
                            : d.status === "APPROVED"
                              ? "bg-status-green/20 text-status-green"
                              : "bg-status-red/20 text-status-red"
                        }`}
                      >
                        {d.status}
                      </span>
                    </td>
                    <td className="py-2 pr-3 text-muted-foreground">
                      {new Date(d.created_at).toLocaleString()}
                    </td>
                    <td className="py-2 text-right">
                      {d.status === "DRAFTED" ? (
                        <div className="flex justify-end gap-1.5">
                          <button
                            type="button"
                            onClick={() => setRejectingDraftId(d.id)}
                            className="rounded px-2 py-1 text-[11px] font-semibold text-status-red hover:bg-status-red/10 border border-status-red/20"
                          >
                            Reject Draft
                          </button>
                        </div>
                      ) : (
                        <span className="text-[11px] text-muted-foreground">
                          {d.rejection_reason ? `Rejected: ${d.rejection_reason}` : d.status}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ) : null}

      {/* Reject Modal */}
      <AppDialog
        open={Boolean(rejectingDraftId)}
        onOpenChange={(next) => {
          if (!next) setRejectingDraftId(null);
        }}
        title="Reject AI Draft Action"
        description="Rejecting this recommendation marks it as rejected in the audit log without executing any mutation."
        className="max-w-md"
        pending={rejectDraftMutation.isPending}
      >
        <div className="space-y-3">
          <textarea
            placeholder="Reason for rejection (optional)…"
            value={rejectionReason}
            onChange={(e) => setRejectionReason(e.target.value)}
            rows={3}
            className="w-full rounded-lg border border-input bg-card p-2.5 text-xs text-foreground outline-none resize-none focus:border-primary"
          />
          <div className="flex flex-col-reverse gap-2 sm:flex-row sm:items-center sm:justify-end">
            <Button
              type="button"
              variant="ghost"
              disabled={rejectDraftMutation.isPending}
              onClick={() => setRejectingDraftId(null)}
              className="w-full sm:w-auto"
            >
              Cancel
            </Button>
            <Button
              type="button"
              variant="primary"
              className="bg-status-red text-white hover:bg-status-red/90 w-full sm:w-auto"
              disabled={rejectDraftMutation.isPending}
              onClick={() => rejectingDraftId && handleRejectDraft(rejectingDraftId)}
            >
              {rejectDraftMutation.isPending ? "Rejecting..." : "Confirm Rejection"}
            </Button>
          </div>
        </div>
      </AppDialog>

      {/* 3. AI Interaction Audit Log Table */}
      <Card className="p-5 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="font-semibold text-foreground text-sm">AI Interaction Audit Log</h3>
            <p className="text-xs text-muted-foreground">
              Complete chronological audit trail with tool calls, safety evaluations, and user
              feedback.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="rounded-lg border border-input bg-card px-2.5 py-1.5 text-xs text-foreground outline-none"
            >
              <option value="">All Categories</option>
              <option value="INVENTORY_AVAILABILITY">Inventory Availability</option>
              <option value="LEDGER_EXPLANATION">Ledger Explanation</option>
              <option value="OPERATIONAL_STATUS">Operational Status</option>
              <option value="EXCEPTION_SUMMARY">Exception Summary</option>
              <option value="DRAFT_RECOMMENDATION">Draft Recommendation</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-lg border border-input bg-card px-2.5 py-1.5 text-xs text-foreground outline-none"
            >
              <option value="">All Statuses</option>
              <option value="COMPLETED">Completed</option>
              <option value="REFUSED">Refused</option>
              <option value="FAILED">Failed</option>
            </select>

            <Button
              variant="outline"
              className="px-2.5 py-1 text-xs"
              onClick={() => interactionsQuery.refetch()}
              disabled={interactionsQuery.isFetching}
            >
              <RefreshCw
                className={`size-3.5 ${interactionsQuery.isFetching ? "animate-spin" : ""}`}
              />
            </Button>
          </div>
        </div>

        {interactionsQuery.isLoading ? (
          <LoadingState />
        ) : interactions.length === 0 ? (
          <EmptyState
            message="No AI interactions found"
            hint="Try changing the category or status filters."
          />
        ) : (
          <TableShell>
            <thead>
              <tr>
                <Th>Timestamp</Th>
                <Th>Category</Th>
                <Th>Status</Th>
                <Th>Provider</Th>
                <Th className="text-center">Tools / Drafts</Th>
                <Th className="text-center">Feedback</Th>
                <Th>Prompt Excerpt</Th>
                <Th className="text-right">Action</Th>
              </tr>
            </thead>
            <tbody>
              {interactions.map((item: AiInteractionSummaryItem) => {
                const isSuccess = item.status === "COMPLETED";
                const isRefusal = item.status === "REFUSED";
                return (
                  <tr
                    key={item.id}
                    onClick={() => setSelectedInteractionId(item.id)}
                    className="hover:bg-primary-tint/30 cursor-pointer transition-colors"
                  >
                    <Td className="text-xs text-muted-foreground whitespace-nowrap">
                      {new Date(item.created_at).toLocaleString()}
                    </Td>
                    <Td>
                      <span className="rounded bg-primary/10 px-2 py-0.5 text-[10px] font-semibold uppercase text-primary">
                        {item.request_category.replaceAll("_", " ")}
                      </span>
                    </Td>
                    <Td>
                      <span
                        className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                          isSuccess
                            ? "bg-status-green/20 text-status-green"
                            : isRefusal
                              ? "bg-status-amber/20 text-status-amber"
                              : "bg-status-red/20 text-status-red"
                        }`}
                      >
                        {item.status}
                      </span>
                    </Td>
                    <Td className="text-xs font-medium text-foreground">
                      {item.provider_name === "google_genai" ? "Gemini" : "Rule Engine"}
                    </Td>
                    <Td className="text-center text-xs text-muted-foreground">
                      {item.tool_call_count} / {item.draft_action_count}
                    </Td>
                    <Td className="text-center">
                      {item.feedback_count > 0 ? (
                        <span className="inline-flex items-center gap-1 text-xs">
                          <span className="text-status-green font-bold inline-flex items-center gap-0.5">
                            <ThumbsUp className="size-3" /> {item.helpful_count}
                          </span>
                          {item.unhelpful_count > 0 ? (
                            <span className="text-status-red font-bold inline-flex items-center gap-0.5 ml-1">
                              <ThumbsDown className="size-3" /> {item.unhelpful_count}
                            </span>
                          ) : null}
                        </span>
                      ) : (
                        <span className="text-muted-foreground text-xs">—</span>
                      )}
                    </Td>
                    <Td className="text-xs text-foreground max-w-xs truncate">
                      {item.prompt_excerpt || "—"}
                    </Td>
                    <Td className="text-right">
                      <Button
                        variant="ghost"
                        className="text-xs py-1 px-2.5"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedInteractionId(item.id);
                        }}
                      >
                        <Eye className="size-3.5 mr-1" /> View Detail
                      </Button>
                    </Td>
                  </tr>
                );
              })}
            </tbody>
          </TableShell>
        )}
      </Card>

      {/* 4. Detail Modal / Drawer */}
      <AppDialog
        open={Boolean(selectedInteractionId && detail)}
        onOpenChange={(next) => {
          if (!next) setSelectedInteractionId(null);
        }}
        title="AI Interaction Audit Detail"
        description={detail ? detail.id : ""}
        className="max-w-3xl"
        pending={false}
      >
        {detail ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="rounded-lg bg-muted/40 p-2.5">
                <span className="text-muted-foreground">Category</span>
                <p className="font-semibold text-foreground mt-0.5">{detail.request_category}</p>
              </div>
              <div className="rounded-lg bg-muted/40 p-2.5">
                <span className="text-muted-foreground">Safety Decision</span>
                <p className="font-semibold text-foreground mt-0.5">{detail.safety_decision}</p>
              </div>
              <div className="rounded-lg bg-muted/40 p-2.5">
                <span className="text-muted-foreground">Provider / Model</span>
                <p className="font-semibold text-foreground mt-0.5">
                  {detail.provider_name} ({detail.model_name})
                </p>
              </div>
              <div className="rounded-lg bg-muted/40 p-2.5">
                <span className="text-muted-foreground">Completed At</span>
                <p className="font-semibold text-foreground mt-0.5">
                  {detail.completed_at ? new Date(detail.completed_at).toLocaleTimeString() : "—"}
                </p>
              </div>
            </div>

            {/* Prompt Excerpt & Hash */}
            <div className="space-y-1 text-xs">
              <div className="flex items-center justify-between text-muted-foreground">
                <span className="font-semibold uppercase tracking-wider">
                  Sanitized Prompt Excerpt
                </span>
                <span className="font-mono text-[10px]">
                  Hash: {detail.prompt_hash.slice(0, 16)}…
                </span>
              </div>
              <div className="rounded-lg border border-border bg-card p-3 font-mono text-[11px] whitespace-pre-wrap text-foreground">
                {detail.prompt_excerpt}
              </div>
            </div>

            {/* Response Excerpt */}
            <div className="space-y-1 text-xs">
              <span className="font-semibold uppercase tracking-wider text-muted-foreground">
                Response Excerpt
              </span>
              <div className="rounded-lg border border-border bg-muted/20 p-3 text-xs leading-relaxed text-foreground whitespace-pre-wrap">
                {detail.response_excerpt}
              </div>
            </div>

            {/* Tool Calls */}
            {detail.tool_calls && detail.tool_calls.length > 0 ? (
              <div className="space-y-2 text-xs">
                <span className="font-semibold uppercase tracking-wider text-muted-foreground">
                  Read Tool Executions ({detail.tool_calls.length})
                </span>
                <div className="space-y-2">
                  {detail.tool_calls.map((tc) => (
                    <div
                      key={tc.id}
                      className="rounded-lg border border-border bg-card p-3 space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-primary">{tc.tool_name}</span>
                        <span className="font-bold text-status-green">{tc.status}</span>
                      </div>
                      <div className="text-[11px] text-muted-foreground font-mono truncate">
                        Input: {tc.input_excerpt || "—"}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            {/* Feedbacks recorded */}
            {detail.feedbacks && detail.feedbacks.length > 0 ? (
              <div className="space-y-2 text-xs">
                <span className="font-semibold uppercase tracking-wider text-muted-foreground">
                  User Feedback ({detail.feedbacks.length})
                </span>
                <div className="space-y-1.5">
                  {detail.feedbacks.map((fb) => (
                    <div
                      key={fb.feedback_id}
                      className="rounded-lg border border-border bg-card p-2.5 flex items-center justify-between"
                    >
                      <div className="flex items-center gap-2">
                        {fb.is_helpful ? (
                          <span className="text-status-green font-bold inline-flex items-center gap-1">
                            <ThumbsUp className="size-3.5" /> Helpful
                          </span>
                        ) : (
                          <span className="text-status-red font-bold inline-flex items-center gap-1">
                            <ThumbsDown className="size-3.5" /> Not helpful
                          </span>
                        )}
                        {fb.comment ? (
                          <span className="text-foreground">“{fb.comment}”</span>
                        ) : null}
                      </div>
                      <span className="text-muted-foreground text-[11px]">
                        {new Date(fb.created_at).toLocaleString()}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="flex justify-end pt-2 border-t border-border">
              <Button type="button" onClick={() => setSelectedInteractionId(null)}>Close</Button>
            </div>
          </div>
        ) : null}
      </AppDialog>
    </div>
  );
}
