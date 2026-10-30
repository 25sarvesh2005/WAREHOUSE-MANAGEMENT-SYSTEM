import { useState } from "react";
import {
  Activity,
  Copy,
  Eye,
  EyeOff,
  Globe,
  Plus,
  Radio,
  RefreshCw,
  Send,
  Shield,
  Trash2,
  Zap,
} from "lucide-react";
import { AppDialog } from "@/components/AppDialog";
import { StatusBadge } from "@/components/StatusBadge";
import {
  Button,
  Card,
  EmptyState,
  LoadingState,
  TableShell,
  Td,
  Th,
} from "@/components/ui-kit";
import {
  useCreateWebhookSubscriptionMutation,
  useDeleteWebhookSubscriptionMutation,
  useTestWebhookSubscriptionMutation,
  useWebhookDeliveriesQuery,
  useWebhookSubscriptionsQuery,
} from "@/hooks/use-api";
import type { WebhookDelivery, WebhookSubscription } from "@/lib/types";

const AVAILABLE_EVENTS = [
  { id: "*", label: "* (All Outbox Events)", desc: "Stream every business event" },
  { id: "order.allocated", label: "order.allocated", desc: "Order inventory reserved" },
  { id: "order.cancelled", label: "order.cancelled", desc: "Customer order voided" },
  { id: "shipment.created", label: "shipment.created", desc: "Pick task finalized" },
  { id: "shipment.shipped", label: "shipment.shipped", desc: "Carrier dispatch recorded" },
  { id: "inventory.adjusted", label: "inventory.adjusted", desc: "Physical cycle count shift" },
];

export function WebhookIntegrationsPanel() {
  const subscriptionsQuery = useWebhookSubscriptionsQuery();
  const deliveriesQuery = useWebhookDeliveriesQuery({ limit: 50 });
  const createMutation = useCreateWebhookSubscriptionMutation();
  const deleteMutation = useDeleteWebhookSubscriptionMutation();
  const testMutation = useTestWebhookSubscriptionMutation();

  const subscriptions = subscriptionsQuery.data ?? [];
  const deliveries = deliveriesQuery.data ?? [];

  const [openCreate, setOpenCreate] = useState(false);
  const [selectedDelivery, setSelectedDelivery] = useState<WebhookDelivery | null>(null);
  const [showSecretMap, setShowSecretMap] = useState<Record<string, boolean>>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<string | null>(null);

  const [newSub, setNewSub] = useState({
    url: "",
    description: "",
    secret: "",
    event_types: ["*"],
  });

  function toggleShowSecret(id: string) {
    setShowSecretMap((prev) => ({ ...prev, [id]: !prev[id] }));
  }

  function copyToClipboard(id: string, text: string) {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  }

  async function handleCreate() {
    if (!newSub.url) return;
    await createMutation.mutateAsync({
      url: newSub.url,
      description: newSub.description || undefined,
      secret: newSub.secret || undefined,
      event_types: newSub.event_types.length > 0 ? newSub.event_types : ["*"],
    });
    setOpenCreate(false);
    setNewSub({ url: "", description: "", secret: "", event_types: ["*"] });
  }

  async function handleDelete(id: string) {
    if (confirm("Are you sure you want to delete this webhook subscription?")) {
      await deleteMutation.mutateAsync(id);
    }
  }

  async function handleTest(sub: WebhookSubscription) {
    setTestingId(sub.id);
    setTestResult(null);
    try {
      const res = await testMutation.mutateAsync(sub.id);
      setTestResult(
        `Test ping delivered! HTTP ${res.status_code ?? "Unknown"} in ${res.latency_ms?.toFixed(1) ?? 0}ms`,
      );
    } catch (err: unknown) {
      setTestResult(err instanceof Error ? err.message : "Test ping failed");
    } finally {
      setTestingId(null);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header card with quick metrics & action */}
      <Card className="p-5 border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="flex size-8 items-center justify-center rounded-lg bg-blue-50 dark:bg-blue-950/60 text-primary border border-blue-200 dark:border-blue-900/60">
                <Radio className="size-4" />
              </span>
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                Transactional Outbox & Webhooks Engine
              </h2>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-2xl">
              Dispatch real-time HMAC-SHA256 signed HTTP webhooks directly from the postgres transactional
              outbox table to external ERPs, Shopify, carrier aggregators, and warehouse client systems.
            </p>
          </div>
          <Button
            variant="primary"
            size="sm"
            onClick={() => setOpenCreate(true)}
            className="gap-2 shrink-0"
          >
            <Plus className="size-4" /> Add Destination
          </Button>
        </div>

        {testResult ? (
          <div className="mt-4 p-3 rounded-lg bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900 text-xs font-medium text-blue-900 dark:text-blue-200 flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Zap className="size-4 text-primary shrink-0" /> {testResult}
            </span>
            <button
              type="button"
              onClick={() => setTestResult(null)}
              className="text-xs text-blue-600 dark:text-blue-400 underline cursor-pointer"
            >
              Dismiss
            </button>
          </div>
        ) : null}
      </Card>

      {/* Subscriptions Table */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Registered Webhook Destinations ({subscriptions.length})
          </h3>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => subscriptionsQuery.refetch()}
            className="gap-1.5 text-xs text-slate-500"
          >
            <RefreshCw className="size-3.5" /> Refresh
          </Button>
        </div>

        {subscriptionsQuery.isLoading ? (
          <LoadingState message="Loading webhook destinations..." />
        ) : subscriptions.length === 0 ? (
          <Card className="p-8 text-center">
            <EmptyState
              message="No webhook endpoints registered"
              hint="Register an HTTPS webhook URL to receive live outbox dispatch events (order allocations, shipments, adjustments)."
            />
          </Card>
        ) : (
          <TableShell>
            <thead>
              <tr>
                <Th>Destination URL & Description</Th>
                <Th className="w-28">Tenant Scope</Th>
                <Th>Subscribed Events</Th>
                <Th className="w-56">HMAC Secret</Th>
                <Th className="w-24">Status</Th>
                <Th className="text-right w-44">Actions</Th>
              </tr>
            </thead>
            <tbody>
              {subscriptions.map((sub: WebhookSubscription) => {
                const isSecretShown = !!showSecretMap[sub.id];
                const isCopied = copiedId === sub.id;
                const isTesting = testingId === sub.id;

                return (
                  <tr key={sub.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors">
                    <Td>
                      <div className="font-mono text-xs font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5 break-all">
                        <Globe className="size-3.5 text-slate-400 shrink-0" />
                        {sub.url}
                      </div>
                      {sub.description ? (
                        <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                          {sub.description}
                        </p>
                      ) : null}
                    </Td>
                    <Td>
                      <span className="inline-flex items-center rounded-md bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-xs font-mono font-semibold text-slate-700 dark:text-slate-300">
                        {sub.tenant_id}
                      </span>
                    </Td>
                    <Td>
                      <div className="flex flex-wrap gap-1 max-w-xs">
                        {sub.event_types.map((ev) => (
                          <span
                            key={ev}
                            className="inline-block rounded bg-blue-50 dark:bg-blue-950/50 border border-blue-200 dark:border-blue-900 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-primary dark:text-blue-400"
                          >
                            {ev}
                          </span>
                        ))}
                      </div>
                    </Td>
                    <Td>
                      <div className="flex items-center gap-1.5 font-mono text-xs text-slate-700 dark:text-slate-300">
                        <span>{isSecretShown ? sub.secret : "••••••••••••••••"}</span>
                        <button
                          type="button"
                          onClick={() => toggleShowSecret(sub.id)}
                          aria-label={isSecretShown ? "Hide secret" : "Reveal secret"}
                          className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 cursor-pointer"
                        >
                          {isSecretShown ? <EyeOff className="size-3.5" /> : <Eye className="size-3.5" />}
                        </button>
                        <button
                          type="button"
                          onClick={() => copyToClipboard(sub.id, sub.secret)}
                          aria-label="Copy secret"
                          className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 cursor-pointer"
                        >
                          <Copy className="size-3.5" />
                        </button>
                        {isCopied ? (
                          <span className="text-[10px] text-emerald-600 font-semibold">Copied!</span>
                        ) : null}
                      </div>
                    </Td>
                    <Td>
                      <StatusBadge value={sub.status} />
                    </Td>
                    <Td className="text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <Button
                          variant="secondary"
                          size="sm"
                          disabled={isTesting}
                          onClick={() => handleTest(sub)}
                          className="gap-1.5 text-xs"
                        >
                          <Send className="size-3" />
                          {isTesting ? "Pinging..." : "Test Ping"}
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(sub.id)}
                          className="text-rose-600 hover:text-rose-700 hover:bg-rose-50 dark:hover:bg-rose-950/40 p-1.5"
                          aria-label={`Delete subscription ${sub.id}`}
                        >
                          <Trash2 className="size-4" />
                        </Button>
                      </div>
                    </Td>
                  </tr>
                );
              })}
            </tbody>
          </TableShell>
        )}
      </div>

      {/* Outbound Delivery Audit Log */}
      <div className="space-y-3 pt-4 border-t border-slate-200 dark:border-slate-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="size-4 text-primary" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
              Live Outbound Delivery Audit Log ({deliveries.length})
            </h3>
          </div>
          <span className="text-[11px] text-slate-400">Auto-refreshes every 10s</span>
        </div>

        {deliveriesQuery.isLoading ? (
          <LoadingState message="Loading delivery audit stream..." />
        ) : deliveries.length === 0 ? (
          <Card className="p-6 text-center text-xs text-slate-400">
            No delivery events recorded yet. Trigger an action (or click "Test Ping") to view outbound logs.
          </Card>
        ) : (
          <TableShell>
            <thead>
              <tr>
                <Th className="w-24">Status</Th>
                <Th>Event Type</Th>
                <Th className="w-24">Latency</Th>
                <Th className="w-20">Attempt</Th>
                <Th>Delivered At</Th>
                <Th className="text-right w-24">Payload</Th>
              </tr>
            </thead>
            <tbody>
              {deliveries.map((del: WebhookDelivery) => {
                const isSuccess = del.status_code && del.status_code >= 200 && del.status_code < 300;

                return (
                  <tr
                    key={del.id}
                    className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors cursor-pointer text-xs"
                    onClick={() => setSelectedDelivery(del)}
                  >
                    <Td>
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono font-bold ${
                          isSuccess
                            ? "bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-900"
                            : "bg-rose-50 dark:bg-rose-950/60 text-rose-700 dark:text-rose-400 border border-rose-200 dark:border-rose-900"
                        }`}
                      >
                        {del.status_code ?? "ERR"}
                      </span>
                    </Td>
                    <Td>
                      <span className="font-mono font-semibold text-slate-900 dark:text-slate-100">
                        {del.event_type}
                      </span>
                    </Td>
                    <Td>
                      <span className="font-mono text-slate-600 dark:text-slate-400">
                        {del.latency_ms != null ? `${del.latency_ms.toFixed(0)} ms` : "—"}
                      </span>
                    </Td>
                    <Td>
                      <span className="font-medium text-slate-500">#{del.attempt_number}</span>
                    </Td>
                    <Td>
                      <span className="font-mono text-[11px] text-slate-500">
                        {new Date(del.delivered_at).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit",
                        })}
                      </span>
                    </Td>
                    <Td className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedDelivery(del);
                        }}
                        className="text-xs text-primary underline"
                      >
                        Inspect
                      </Button>
                    </Td>
                  </tr>
                );
              })}
            </tbody>
          </TableShell>
        )}
      </div>

      {/* Inbound Integrations Guide */}
      <Card className="p-5 border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/50">
        <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100 flex items-center gap-2">
          <Shield className="size-4 text-emerald-600" /> Inbound Webhook Specs for External Systems
        </h4>
        <div className="grid md:grid-cols-2 gap-4 mt-3 text-xs text-slate-600 dark:text-slate-400">
          <div className="p-3 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <p className="font-bold text-slate-800 dark:text-slate-200">1. Carrier Tracking Ingestion</p>
            <p className="font-mono text-[11px] text-primary mt-1">POST /api/v1/webhooks/inbound/carrier</p>
            <p className="mt-1 text-[11px]">
              Accepts carrier milestone updates (FedEx, UPS, USPS). Automatically flags out-for-delivery,
              delivered, or exception states.
            </p>
          </div>
          <div className="p-3 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
            <p className="font-bold text-slate-800 dark:text-slate-200">2. Marketplace Order Ingestion</p>
            <p className="font-mono text-[11px] text-primary mt-1">POST /api/v1/webhooks/inbound/order</p>
            <p className="mt-1 text-[11px]">
              Enqueues marketplace orders (Shopify, Amazon, WooCommerce) into Whitfield transactional outbox
              for automated reservation and wave generation.
            </p>
          </div>
        </div>
      </Card>

      {/* Register Destination Dialog */}
      <AppDialog
        open={openCreate}
        onOpenChange={setOpenCreate}
        title="Register Webhook Destination"
        description="Configure an HTTPS endpoint to receive signed JSON event dispatches."
        className="max-w-lg"
        pending={createMutation.isPending}
      >
        <div className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Destination HTTPS URL *
            </label>
            <input
              type="url"
              required
              placeholder="https://api.merchant.com/wms/webhook"
              value={newSub.url}
              onChange={(e) => setNewSub({ ...newSub, url: e.target.value })}
              className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-xs font-mono text-slate-900 dark:text-slate-100 focus:outline-none focus:border-primary"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Description / System Name
            </label>
            <input
              type="text"
              placeholder="e.g. ERP Ingestion Service / Shopify Store"
              value={newSub.description}
              onChange={(e) => setNewSub({ ...newSub, description: e.target.value })}
              className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-primary"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Custom HMAC Secret (optional — leave blank to generate secure 48-char hex)
            </label>
            <input
              type="password"
              placeholder="Leave blank for auto-generated secret"
              value={newSub.secret}
              onChange={(e) => setNewSub({ ...newSub, secret: e.target.value })}
              className="w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-xs font-mono text-slate-900 dark:text-slate-100 focus:outline-none focus:border-primary"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
              Event Subscriptions
            </label>
            <div className="space-y-2 border border-slate-200 dark:border-slate-800 rounded-lg p-3 max-h-40 overflow-y-auto">
              {AVAILABLE_EVENTS.map((ev) => {
                const checked = newSub.event_types.includes(ev.id);
                return (
                  <label key={ev.id} className="flex items-start gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={(e) => {
                        if (ev.id === "*") {
                          setNewSub({ ...newSub, event_types: e.target.checked ? ["*"] : [] });
                        } else {
                          const withoutStar = newSub.event_types.filter((t) => t !== "*");
                          if (e.target.checked) {
                            setNewSub({ ...newSub, event_types: [...withoutStar, ev.id] });
                          } else {
                            setNewSub({ ...newSub, event_types: withoutStar.filter((t) => t !== ev.id) });
                          }
                        }
                      }}
                      className="mt-0.5 rounded border-slate-300 text-primary focus:ring-primary"
                    />
                    <div>
                      <span className="font-mono font-semibold text-slate-800 dark:text-slate-200">
                        {ev.label}
                      </span>
                      <p className="text-[11px] text-slate-400">{ev.desc}</p>
                    </div>
                  </label>
                );
              })}
            </div>
          </div>
        </div>

        <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:items-center sm:justify-end border-t border-slate-100 dark:border-slate-800 pt-4">
          <Button
            type="button"
            variant="secondary"
            size="md"
            disabled={createMutation.isPending}
            onClick={() => setOpenCreate(false)}
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="primary"
            size="md"
            onClick={handleCreate}
            disabled={createMutation.isPending || !newSub.url}
          >
            {createMutation.isPending ? "Registering..." : "Save Subscription"}
          </Button>
        </div>
      </AppDialog>

      {/* Inspect Delivery Detail Dialog */}
      <AppDialog
        open={!!selectedDelivery}
        onOpenChange={(open) => !open && setSelectedDelivery(null)}
        title="Webhook Delivery Inspection"
        description={`Audit record for delivery attempt ${selectedDelivery?.id?.slice(0, 8)}`}
        className="max-w-2xl"
      >
        {selectedDelivery ? (
          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-2 gap-3 p-3 bg-slate-50 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800">
              <div>
                <span className="text-[11px] text-slate-400">Event Type</span>
                <p className="font-mono font-bold text-slate-900 dark:text-slate-100">
                  {selectedDelivery.event_type}
                </p>
              </div>
              <div>
                <span className="text-[11px] text-slate-400">HTTP Status</span>
                <p className="font-mono font-bold text-slate-900 dark:text-slate-100">
                  {selectedDelivery.status_code ?? "Failed / Timeout"}
                </p>
              </div>
              <div>
                <span className="text-[11px] text-slate-400">Latency</span>
                <p className="font-mono font-semibold text-slate-800 dark:text-slate-200">
                  {selectedDelivery.latency_ms != null ? `${selectedDelivery.latency_ms.toFixed(1)} ms` : "—"}
                </p>
              </div>
              <div>
                <span className="text-[11px] text-slate-400">Attempt Number</span>
                <p className="font-medium text-slate-800 dark:text-slate-200">
                  #{selectedDelivery.attempt_number}
                </p>
              </div>
            </div>

            {selectedDelivery.error ? (
              <div className="p-3 bg-rose-50 dark:bg-rose-950/40 rounded-lg border border-rose-200 dark:border-rose-900 text-rose-700 dark:text-rose-300">
                <span className="font-bold">Error:</span> {selectedDelivery.error}
              </div>
            ) : null}

            <div>
              <span className="font-semibold text-slate-700 dark:text-slate-300">Dispatched JSON Payload</span>
              <pre className="mt-1 p-3 rounded-lg bg-slate-950 text-slate-100 font-mono text-[11px] overflow-x-auto max-h-48 border border-slate-800">
                {JSON.stringify(selectedDelivery.payload, null, 2)}
              </pre>
            </div>

            {selectedDelivery.response_body ? (
              <div>
                <span className="font-semibold text-slate-700 dark:text-slate-300">Receiver Response Body</span>
                <pre className="mt-1 p-3 rounded-lg bg-slate-100 dark:bg-slate-900 text-slate-800 dark:text-slate-200 font-mono text-[11px] overflow-x-auto max-h-36 border border-slate-200 dark:border-slate-800">
                  {selectedDelivery.response_body}
                </pre>
              </div>
            ) : null}
          </div>
        ) : null}
      </AppDialog>
    </div>
  );
}

