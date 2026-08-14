import { createFileRoute } from "@tanstack/react-router";
import { CalendarDays, Hash, Layers, Store } from "lucide-react";
import { useMemo, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { DetailPanel } from "@/components/DetailPanel";
import { StatusBadge } from "@/components/StatusBadge";
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  ExceptionBanner,
  LoadingState,
} from "@/components/ui-kit";
import { productName, productSku, sellerLabel, toReturnLineItem } from "@/lib/display";
import { formatDate, formatQty } from "@/lib/format";
import {
  useInspectReturnMutation,
  useProductsQuery,
  useReceiveReturnMutation,
  useReturnQuery,
  useSellersQuery,
} from "@/hooks/use-api";

const DISPOSITIONS = ["AVAILABLE", "DAMAGED", "QUARANTINED", "SCRAPPED", "REJECTED"];
const STEPS = ["EXPECTED", "RECEIVED", "INSPECTION", "COMPLETED"];

export const Route = createFileRoute("/returns/$id")({
  head: () => ({
    meta: [
      { title: "Return Detail | Whitfield Ops" },
      {
        name: "description",
        content: "Inspect a return line by line and record dispositions before restocking.",
      },
      { property: "og:title", content: "Return Detail | Whitfield Ops" },
      {
        property: "og:description",
        content: "Inspection-first return handling with a full event trail.",
      },
    ],
  }),
  component: ReturnDetail,
});

function ReturnDetail() {
  const { id } = Route.useParams();
  const returnQuery = useReturnQuery(id);
  const sellersQuery = useSellersQuery();
  const productsQuery = useProductsQuery();
  const receiveReturnMutation = useReceiveReturnMutation();
  const inspectReturnMutation = useInspectReturnMutation();
  const returnOrder = returnQuery.data;
  const sellers = sellersQuery.data ?? [];
  const products = productsQuery.data ?? [];
  const [dispositions, setDispositions] = useState<Record<string, string>>({});
  const [receivedQuantities, setReceivedQuantities] = useState<Record<string, string>>({});
  const [dispositionQuantities, setDispositionQuantities] = useState<Record<string, string>>({});

  const status = returnOrder?.status ?? "EXPECTED";
  const stepIndex = useMemo(() => Math.max(STEPS.indexOf(status), 0), [status]);

  async function receiveReturn() {
    if (!returnOrder) return;
    await receiveReturnMutation.mutateAsync({
      id: returnOrder.id,
      lines: returnOrder.lines
        .map((line) => ({
          line_id: line.id,
          received_quantity: Number(
            receivedQuantities[line.id] ?? line.received_quantity ?? line.expected_quantity ?? 0,
          ),
        }))
        .filter((line) => line.received_quantity > 0),
    });
    setReceivedQuantities({});
  }

  async function recordDispositions() {
    if (!returnOrder) return;
    await inspectReturnMutation.mutateAsync({
      id: returnOrder.id,
      dispositions: returnOrder.lines.map((line) => ({
        return_line_id: line.id,
        disposition_state: dispositions[line.id] ?? "AVAILABLE",
        quantity: Number(
          dispositionQuantities[line.id] ?? line.received_quantity ?? line.expected_quantity ?? 0,
        ),
      })),
    });
    setDispositionQuantities({});
  }

  if (returnQuery.isLoading) {
    return (
      <AppShell>
        <LoadingState />
      </AppShell>
    );
  }

  if (returnQuery.isError) {
    return (
      <AppShell>
        <ErrorState
          message="Could not load this return from the backend."
          onRetry={() => returnQuery.refetch()}
        />
      </AppShell>
    );
  }

  if (!returnOrder) {
    return (
      <AppShell>
        <div className="card-surface">
          <EmptyState message="Return not found" />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <DetailPanel
        backTo="/returns"
        backLabel="Back to returns"
        title={returnOrder.return_number}
        status={status}
        banner={
          <ExceptionBanner>
            Returns never post directly to AVAILABLE. Every line must pass inspection and receive a
            disposition.
          </ExceptionBanner>
        }
        chips={[
          {
            icon: Hash,
            label: "Reference",
            value: returnOrder.rma_number || returnOrder.return_number,
          },
          { icon: Store, label: "Seller", value: sellerLabel(sellers, returnOrder.seller_id) },
          { icon: Layers, label: "Line count", value: String(returnOrder.lines.length) },
          { icon: CalendarDays, label: "Created", value: formatDate(returnOrder.created_at) },
        ]}
        lines={returnOrder.lines.map((line) => toReturnLineItem(line, products))}
        events={[]}
      />

      {receiveReturnMutation.isError || inspectReturnMutation.isError ? (
        <ErrorState
          message={
            receiveReturnMutation.error?.message ||
            inspectReturnMutation.error?.message ||
            "Could not update return."
          }
        />
      ) : null}

      <div className="mt-6 grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        <Card className="p-5">
          <h2 className="mb-4 font-semibold text-navy">Inspection & disposition</h2>
          <div className="space-y-3">
            {returnOrder.lines.map((line) => (
              <div
                key={line.id}
                className="grid gap-3 rounded-xl bg-muted px-3 py-3 text-sm md:grid-cols-[1fr_auto_auto]"
              >
                <div className="min-w-0">
                  <p className="truncate font-medium">{productName(products, line.product_id)}</p>
                  <p className="text-xs text-muted-foreground">
                    {productSku(products, line.product_id)} - expected{" "}
                    {formatQty(line.expected_quantity)} / received{" "}
                    {formatQty(line.received_quantity)}
                  </p>
                </div>
                <label className="block">
                  <span className="text-xs font-medium text-muted-foreground">Receive qty</span>
                  <input
                    type="number"
                    min="0"
                    value={
                      receivedQuantities[line.id] ??
                      String(line.received_quantity || line.expected_quantity || 0)
                    }
                    onChange={(e) =>
                      setReceivedQuantities({
                        ...receivedQuantities,
                        [line.id]: e.target.value,
                      })
                    }
                    className="mt-1 w-28 rounded-xl border border-border bg-card px-3 py-2 text-sm outline-none focus:border-primary"
                  />
                </label>
                <div className="flex flex-wrap items-end gap-2">
                  <label className="block">
                    <span className="text-xs font-medium text-muted-foreground">Disposition</span>
                    <select
                      value={dispositions[line.id] ?? "AVAILABLE"}
                      onChange={(e) =>
                        setDispositions({ ...dispositions, [line.id]: e.target.value })
                      }
                      className="mt-1 rounded-xl border border-border bg-card px-3 py-2 text-sm outline-none focus:border-primary"
                    >
                      {DISPOSITIONS.map((disposition) => (
                        <option key={disposition}>{disposition}</option>
                      ))}
                    </select>
                  </label>
                  <label className="block">
                    <span className="text-xs font-medium text-muted-foreground">Qty</span>
                    <input
                      type="number"
                      min="0"
                      value={
                        dispositionQuantities[line.id] ??
                        String(line.received_quantity || line.expected_quantity || 0)
                      }
                      onChange={(e) =>
                        setDispositionQuantities({
                          ...dispositionQuantities,
                          [line.id]: e.target.value,
                        })
                      }
                      className="mt-1 w-24 rounded-xl border border-border bg-card px-3 py-2 text-sm outline-none focus:border-primary"
                    />
                  </label>
                  <StatusBadge value={dispositions[line.id] ?? "AVAILABLE"} />
                </div>
              </div>
            ))}
          </div>
          <div className="mt-5 flex flex-wrap gap-2">
            <Button
              disabled={
                !["EXPECTED", "UNIDENTIFIED"].includes(status) || receiveReturnMutation.isPending
              }
              onClick={receiveReturn}
            >
              {receiveReturnMutation.isPending ? "Receiving..." : "Receive return"}
            </Button>
            <Button
              disabled={status !== "INSPECTION" || inspectReturnMutation.isPending}
              onClick={recordDispositions}
            >
              {inspectReturnMutation.isPending ? "Recording..." : "Record dispositions"}
            </Button>
          </div>
        </Card>

        <Card className="p-5">
          <h2 className="mb-4 font-semibold text-navy">Return flow</h2>
          <ol className="space-y-3">
            {STEPS.map((step, index) => (
              <li key={step} className="flex items-center gap-3 text-sm">
                <span
                  className={`flex size-6 items-center justify-center rounded-full text-xs font-semibold ${
                    index <= stepIndex
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted text-muted-foreground"
                  }`}
                >
                  {index + 1}
                </span>
                <span
                  className={
                    index <= stepIndex ? "font-medium text-foreground" : "text-muted-foreground"
                  }
                >
                  {step.replaceAll("_", " ")}
                </span>
              </li>
            ))}
          </ol>
        </Card>
      </div>
    </AppShell>
  );
}
