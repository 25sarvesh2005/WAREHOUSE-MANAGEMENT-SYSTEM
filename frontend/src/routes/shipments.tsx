import { createFileRoute } from "@tanstack/react-router";
import { Barcode, CheckCircle2, Package, Plus, Scale, Search, Truck } from "lucide-react";
import { useState } from "react";
import { AppDialog } from "@/components/AppDialog";
import { AppShell } from "@/components/AppShell";
import { FacilityBadge, StatusBadge } from "@/components/StatusBadge";
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  ScannerInputField,
  TableShell,
  Td,
  Th,
} from "@/components/ui-kit";
import { warehouseLabel } from "@/lib/display";
import { formatDate } from "@/lib/format";
import {
  useCreateShipmentMutation,
  useOrdersQuery,
  useShipmentsQuery,
  useWarehousesQuery,
} from "@/hooks/use-api";
import type { Shipment } from "@/lib/types";

export const Route = createFileRoute("/shipments")({
  head: () => ({
    meta: [
      { title: "Carrier Shipments & Weighing | Whitfield Ops" },
      {
        name: "description",
        content:
          "Outbound carrier labeling, box weighing & dimensions, and carrier dispatch tracking.",
      },
      { property: "og:title", content: "Carrier Shipments & Weighing | Whitfield Ops" },
      {
        property: "og:description",
        content: "Weigh, measure, label and dispatch packed orders across Reno and Columbus.",
      },
    ],
  }),
  component: ShipmentsPage,
});

function ShipmentsPage() {
  const shipmentsQuery = useShipmentsQuery();
  const ordersQuery = useOrdersQuery();
  const warehousesQuery = useWarehousesQuery();
  const createShipmentMutation = useCreateShipmentMutation();

  const shipments = shipmentsQuery.data ?? [];
  const orders = ordersQuery.data ?? [];
  const warehouses = warehousesQuery.data ?? [];

  const [showCreate, setShowCreate] = useState(false);
  const [newShipment, setNewShipment] = useState({
    order_id: "",
    carrier: "UPS",
    service_level: "GROUND",
    tracking_number: "",
    box_type: "CARTON",
    weight_lbs: "2.5",
    length_in: "12",
    width_in: "9",
    height_in: "6",
  });
  const [filterQuery, setFilterQuery] = useState("");
  const [error, setError] = useState<string | null>(null);

  const eligibleOrders = orders.filter((order) =>
    ["PACKED", "PICKING", "RESERVED"].includes(order.status),
  );
  const selectedOrder = orders.find((order) => order.id === newShipment.order_id);

  function optionalNumber(value: string) {
    return value ? Number(value) : undefined;
  }

  async function createShipment() {
    if (!selectedOrder) {
      return setError("Please select a packed order to ship.");
    }
    setError(null);

    const shipmentPackage: {
      box_type: string;
      weight_lbs?: number;
      length_in?: number;
      width_in?: number;
      height_in?: number;
    } = {
      box_type: newShipment.box_type,
    };
    const weightLbs = optionalNumber(newShipment.weight_lbs);
    const lengthIn = optionalNumber(newShipment.length_in);
    const widthIn = optionalNumber(newShipment.width_in);
    const heightIn = optionalNumber(newShipment.height_in);
    if (weightLbs !== undefined) shipmentPackage.weight_lbs = weightLbs;
    if (lengthIn !== undefined) shipmentPackage.length_in = lengthIn;
    if (widthIn !== undefined) shipmentPackage.width_in = widthIn;
    if (heightIn !== undefined) shipmentPackage.height_in = heightIn;

    try {
      await createShipmentMutation.mutateAsync({
        order_id: selectedOrder.id,
        warehouse_id: selectedOrder.warehouse_id,
        carrier: newShipment.carrier,
        service_level: newShipment.service_level,
        tracking_number: newShipment.tracking_number.trim() || "",
        packages: [shipmentPackage],
      });
      setShowCreate(false);
      setNewShipment({
        order_id: "",
        carrier: "UPS",
        service_level: "GROUND",
        tracking_number: "",
        box_type: "CARTON",
        weight_lbs: "2.5",
        length_in: "12",
        width_in: "9",
        height_in: "6",
      });
      shipmentsQuery.refetch();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create shipment label.");
    }
  }

  const filteredShipments = shipments.filter((s) => {
    if (!filterQuery.trim()) return true;
    const q = filterQuery.toLowerCase().trim();
    const tracking = (s.tracking_number || "").toLowerCase();
    const carrier = (s.carrier || "").toLowerCase();
    return tracking.includes(q) || carrier.includes(q);
  });

  return (
    <AppShell>
      <PageHeader
        title="Carrier Shipments & Dispatch"
        subtitle="Weigh and measure packed orders, print carrier shipping labels, and track carrier pickup dispatch."
        actions={
          <Button onClick={() => setShowCreate(true)} className="gap-2">
            <Plus className="size-4" /> Create Shipping Label
          </Button>
        }
      />

      {[shipmentsQuery, ordersQuery, warehousesQuery].some((q) => q.isLoading) ? (
        <LoadingState message="Loading outbound shipments queue..." />
      ) : null}

      <Card className="mb-5 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="w-full sm:w-80">
            <ScannerInputField
              value={filterQuery}
              onChange={(e) => setFilterQuery(e.target.value)}
              placeholder="Search carrier tracking # or carrier..."
            />
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-500 font-medium">
            <Scale className="size-4 text-blue-600" />
            <span>Packing station scales calibrated</span>
          </div>
        </div>
      </Card>

      {filteredShipments.length === 0 ? (
        <Card className="p-8">
          <EmptyState
            message="No outbound carrier shipments recorded yet"
            hint="Create a shipment label for a packed customer order once ready for carrier dispatch."
          />
        </Card>
      ) : (
        <TableShell>
          <thead>
            <tr>
              <Th>Shipment ID</Th>
              <Th>Carrier</Th>
              <Th>Service Level</Th>
              <Th>Tracking Number</Th>
              <Th>Facility</Th>
              <Th>Status</Th>
              <Th>Created Date</Th>
            </tr>
          </thead>
          <tbody>
            {filteredShipments.map((s: Shipment) => {
              const whCode = warehouses.find((w) => w.id === s.warehouse_id)?.code || "WH";

              return (
                <tr key={s.id} className="hover:bg-slate-50">
                  <Td className="font-mono font-bold text-slate-900">SHIP-{s.id.slice(0, 8)}</Td>
                  <Td className="font-semibold text-slate-800">{s.carrier}</Td>
                  <Td className="text-slate-600">{s.service_level}</Td>
                  <Td className="font-mono font-bold text-blue-700">
                    {s.tracking_number || "Awaiting Carrier Scan"}
                  </Td>
                  <Td>
                    <FacilityBadge code={whCode} />
                  </Td>
                  <Td>
                    <StatusBadge value={s.status} />
                  </Td>
                  <Td className="font-mono text-xs text-slate-500">{formatDate(s.created_at)}</Td>
                </tr>
              );
            })}
          </tbody>
        </TableShell>
      )}

      {/* Weigh & Print Shipping Label Modal */}
      <AppDialog
        open={showCreate}
        onOpenChange={setShowCreate}
        title="Weigh & Print Shipping Label"
        description="Select the fulfilled order and record its carrier, service, package, and tracking details."
        className="max-w-lg"
        pending={createShipmentMutation.isPending}
      >
        {error ? (
          <div className="mb-3">
            <ErrorState message={error} />
          </div>
        ) : null}

        <div className="space-y-4 text-xs">
          <div>
            <label className="block font-bold text-slate-700 uppercase tracking-wider text-[10px]">
              Select Packed Customer Order
            </label>
            <select
              value={newShipment.order_id}
              onChange={(e) => setNewShipment({ ...newShipment, order_id: e.target.value })}
              className="mt-1.5 w-full rounded-xl border border-input bg-white px-3.5 py-2 text-xs font-bold text-foreground shadow-xs outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 transition-all cursor-pointer"
            >
              <option value="">-- Choose Packed Order --</option>
              {eligibleOrders.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.seller_order_number || `ORD-${o.id.slice(0, 8)}`} ({o.status})
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                Carrier
              </label>
              <select
                value={newShipment.carrier}
                onChange={(e) => setNewShipment({ ...newShipment, carrier: e.target.value })}
                className="mt-1.5 w-full rounded-xl border border-input bg-white px-3.5 py-2 text-xs font-bold text-foreground shadow-xs outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 transition-all cursor-pointer"
              >
                <option value="UPS">UPS Ground / Air</option>
                <option value="FEDEX">FedEx Express / Ground</option>
                <option value="USPS">USPS Priority Mail</option>
                <option value="MANUAL_CARRIER">Freight / Local Pickup</option>
              </select>
            </div>

            <div>
              <label className="block font-bold text-slate-700 uppercase tracking-wider text-[10px]">
                Service Level
              </label>
              <select
                value={newShipment.service_level}
                onChange={(e) =>
                  setNewShipment({ ...newShipment, service_level: e.target.value })
                }
                className="mt-1.5 w-full rounded-xl border border-input bg-white px-3.5 py-2 text-xs font-bold text-foreground shadow-xs outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 transition-all cursor-pointer"
              >
                <option value="GROUND">Ground</option>
                <option value="2DAY">2-Day Expedited</option>
                <option value="OVERNIGHT">Standard Overnight</option>
              </select>
            </div>
          </div>

          {/* Physical Weighing & Dimension Fields */}
          <div className="rounded-lg bg-slate-50 p-3 border border-slate-200 space-y-3">
            <span className="font-bold text-slate-700 uppercase text-[10px] flex items-center gap-1.5">
              <Scale className="size-3.5 text-blue-600" /> Package Scale Weight & Dimensions
            </span>
            <div className="grid grid-cols-4 gap-2">
              <div>
                <label className="block font-medium text-slate-600 text-[10px]">
                  Weight (lbs)
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={newShipment.weight_lbs}
                  onChange={(e) =>
                    setNewShipment({ ...newShipment, weight_lbs: e.target.value })
                  }
                  className="mt-0.5 w-full rounded-md border border-slate-300 bg-white px-2 py-1 font-mono text-xs font-bold text-right"
                />
              </div>
              <div>
                <label className="block font-medium text-slate-600 text-[10px]">
                  Length (in)
                </label>
                <input
                  type="number"
                  value={newShipment.length_in}
                  onChange={(e) =>
                    setNewShipment({ ...newShipment, length_in: e.target.value })
                  }
                  className="mt-0.5 w-full rounded-md border border-slate-300 bg-white px-2 py-1 font-mono text-xs font-bold text-right"
                />
              </div>
              <div>
                <label className="block font-medium text-slate-600 text-[10px]">
                  Width (in)
                </label>
                <input
                  type="number"
                  value={newShipment.width_in}
                  onChange={(e) => setNewShipment({ ...newShipment, width_in: e.target.value })}
                  className="mt-0.5 w-full rounded-md border border-slate-300 bg-white px-2 py-1 font-mono text-xs font-bold text-right"
                />
              </div>
              <div>
                <label className="block font-medium text-slate-600 text-[10px]">
                  Height (in)
                </label>
                <input
                  type="number"
                  value={newShipment.height_in}
                  onChange={(e) =>
                    setNewShipment({ ...newShipment, height_in: e.target.value })
                  }
                  className="mt-0.5 w-full rounded-md border border-slate-300 bg-white px-2 py-1 font-mono text-xs font-bold text-right"
                />
              </div>
            </div>
          </div>

          <div>
            <label className="block font-bold text-slate-700 uppercase tracking-wider text-[10px]">
              Manual Tracking Barcode (Optional override)
            </label>
            <input
              type="text"
              value={newShipment.tracking_number}
              onChange={(e) =>
                setNewShipment({ ...newShipment, tracking_number: e.target.value })
              }
              placeholder="e.g. 1Z9999999999999999 or leave blank for auto-generated tracking"
              className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-mono text-xs text-slate-800 focus:outline-none"
            />
          </div>
        </div>

        <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:items-center sm:justify-end border-t border-slate-100 pt-4">
          <Button
            type="button"
            variant="secondary"
            size="md"
            disabled={createShipmentMutation.isPending}
            onClick={() => setShowCreate(false)}
            className="w-full sm:w-auto"
          >
            Cancel
          </Button>
          <Button
            type="button"
            variant="primary"
            size="md"
            onClick={createShipment}
            disabled={createShipmentMutation.isPending || !newShipment.order_id}
            className="font-bold w-full sm:w-auto"
          >
            {createShipmentMutation.isPending
              ? "Generating Label..."
              : "Print Label & Dispatch"}
          </Button>
        </div>
      </AppDialog>
    </AppShell>
  );
}
