import { createFileRoute } from "@tanstack/react-router";
import { ArrowLeftRight, CalendarDays, Hash, Store } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { DetailPanel } from "@/components/DetailPanel";
import { EmptyState, ErrorState, ExceptionBanner, LoadingState } from "@/components/ui-kit";
import { sellerLabel, toTransferLineItem, warehouseLabel } from "@/lib/display";
import { formatDate } from "@/lib/format";
import {
  useProductsQuery,
  useSellersQuery,
  useTransferQuery,
  useWarehousesQuery,
} from "@/hooks/use-api";

export const Route = createFileRoute("/transfers/$id")({
  head: () => ({
    meta: [
      { title: "Transfer Detail | Whitfield Ops" },
      {
        name: "description",
        content: "Transfer lines, approval trail and discrepancy history for a network move.",
      },
      { property: "og:title", content: "Transfer Detail | Whitfield Ops" },
      { property: "og:description", content: "Full audit trail for an inter-warehouse transfer." },
    ],
  }),
  component: TransferDetail,
});

function TransferDetail() {
  const { id } = Route.useParams();
  const transferQuery = useTransferQuery(id);
  const sellersQuery = useSellersQuery();
  const warehousesQuery = useWarehousesQuery();
  const productsQuery = useProductsQuery();
  const transfer = transferQuery.data;
  const sellers = sellersQuery.data ?? [];
  const warehouses = warehousesQuery.data ?? [];
  const products = productsQuery.data ?? [];

  if (transferQuery.isLoading) {
    return (
      <AppShell>
        <LoadingState />
      </AppShell>
    );
  }

  if (transferQuery.isError) {
    return (
      <AppShell>
        <ErrorState
          message="Could not load this transfer from the backend."
          onRetry={() => transferQuery.refetch()}
        />
      </AppShell>
    );
  }

  if (!transfer) {
    return (
      <AppShell>
        <div className="card-surface">
          <EmptyState message="Transfer not found" />
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <DetailPanel
        backTo="/transfers"
        backLabel="Back to transfers"
        title={transfer.transfer_number}
        status={transfer.status}
        banner={
          transfer.status === "DISCREPANCY_REVIEW" ? (
            <ExceptionBanner>
              Received quantities do not match dispatched quantities. A manager must resolve this
              discrepancy.
            </ExceptionBanner>
          ) : undefined
        }
        chips={[
          { icon: Hash, label: "Reference", value: transfer.transfer_number },
          { icon: Store, label: "Seller", value: sellerLabel(sellers, transfer.seller_id) },
          {
            icon: ArrowLeftRight,
            label: "Route",
            value: `${warehouseLabel(warehouses, transfer.origin_warehouse_id)} -> ${warehouseLabel(
              warehouses,
              transfer.destination_warehouse_id,
            )}`,
          },
          { icon: CalendarDays, label: "Created", value: formatDate(transfer.created_at) },
        ]}
        lines={transfer.lines.map((line) => toTransferLineItem(line, products))}
        events={[]}
      />
    </AppShell>
  );
}
