import { createFileRoute } from "@tanstack/react-router";
import { useState, useMemo } from "react";
import {
  Boxes,
  Database,
  Download,
  Filter,
  Layers,
  PackageSearch,
  Search,
  ShieldCheck,
  Warehouse as WarehouseIcon,
} from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { FacilityBadge, StatusBadge } from "@/components/StatusBadge";
import {
  Card,
  EmptyState,
  ErrorState,
  LedgerNoticeBanner,
  LoadingState,
  PageHeader,
  ScannerInputField,
  TableShell,
  Td,
  Th,
} from "@/components/ui-kit";
import { productName, productSku, sellerLabel, warehouseLabel } from "@/lib/display";
import { formatDate, formatQty } from "@/lib/format";
import {
  useBalancesQuery,
  useMovementsQuery,
  useProductsQuery,
  useSellersQuery,
  useWarehousesQuery,
} from "@/hooks/use-api";
import type { Balance, Movement, Product, Seller, Warehouse } from "@/lib/types";

export const Route = createFileRoute("/inventory")({
  head: () => ({
    meta: [
      { title: "Inventory Balances & Ledger | Whitfield Ops" },
      {
        name: "description",
        content: "Authoritative multi-warehouse inventory balances and immutable movement ledger.",
      },
      { property: "og:title", content: "Inventory Balances & Ledger | Whitfield Ops" },
      {
        property: "og:description",
        content: "Track sellable and non-sellable stock across Reno and Columbus facilities.",
      },
    ],
  }),
  component: InventoryPage,
});

const STATES = [
  "ALL",
  "AVAILABLE",
  "RESERVED",
  "DAMAGED",
  "QUARANTINED",
  "IN_TRANSIT",
  "RETURN_INSPECTION",
  "SHIPPED",
];

const EMPTY_BALANCES: Balance[] = [];
const EMPTY_MOVEMENTS: Movement[] = [];
const EMPTY_SELLERS: Seller[] = [];
const EMPTY_WAREHOUSES: Warehouse[] = [];
const EMPTY_PRODUCTS: Product[] = [];

function InventoryPage() {
  const [selectedState, setSelectedState] = useState("ALL");
  const [selectedWarehouseId, setSelectedWarehouseId] = useState<string>("ALL");
  const [selectedSellerId, setSelectedSellerId] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState("");

  const balancesQuery = useBalancesQuery();
  const movementsQuery = useMovementsQuery(200);
  const sellersQuery = useSellersQuery();
  const warehousesQuery = useWarehousesQuery();
  const productsQuery = useProductsQuery();

  const balances = balancesQuery.data ?? EMPTY_BALANCES;
  const movements = movementsQuery.data ?? EMPTY_MOVEMENTS;
  const sellers = sellersQuery.data ?? EMPTY_SELLERS;
  const warehouses = warehousesQuery.data ?? EMPTY_WAREHOUSES;
  const products = productsQuery.data ?? EMPTY_PRODUCTS;

  // Filtered Balances
  const filteredBalances = useMemo(() => {
    return balances.filter((b) => {
      if (selectedState !== "ALL" && b.inventory_state !== selectedState) return false;
      if (selectedWarehouseId !== "ALL" && b.warehouse_id !== selectedWarehouseId) return false;
      if (selectedSellerId !== "ALL" && b.seller_id !== selectedSellerId) return false;

      if (searchQuery.trim()) {
        const query = searchQuery.trim().toLowerCase();
        const sku = productSku(products, b.product_id).toLowerCase();
        const name = productName(products, b.product_id).toLowerCase();
        const seller = sellerLabel(sellers, b.seller_id).toLowerCase();
        if (!sku.includes(query) && !name.includes(query) && !seller.includes(query)) {
          return false;
        }
      }
      return true;
    });
  }, [
    balances,
    selectedState,
    selectedWarehouseId,
    selectedSellerId,
    searchQuery,
    products,
    sellers,
  ]);

  // Aggregated Stock Numbers
  const totalAvailable = useMemo(() => {
    return balances
      .filter((b) => b.inventory_state === "AVAILABLE")
      .reduce((sum, b) => sum + Number(b.quantity || 0), 0);
  }, [balances]);

  const totalReserved = useMemo(() => {
    return balances
      .filter((b) => b.inventory_state === "RESERVED")
      .reduce((sum, b) => sum + Number(b.quantity || 0), 0);
  }, [balances]);

  const totalDamaged = useMemo(() => {
    return balances
      .filter((b) => b.inventory_state === "DAMAGED")
      .reduce((sum, b) => sum + Number(b.quantity || 0), 0);
  }, [balances]);

  const totalQuarantined = useMemo(() => {
    return balances
      .filter((b) => b.inventory_state === "QUARANTINED")
      .reduce((sum, b) => sum + Number(b.quantity || 0), 0);
  }, [balances]);

  const isLoading =
    balancesQuery.isLoading ||
    movementsQuery.isLoading ||
    sellersQuery.isLoading ||
    warehousesQuery.isLoading ||
    productsQuery.isLoading;

  const isError =
    balancesQuery.isError ||
    movementsQuery.isError ||
    sellersQuery.isError ||
    warehousesQuery.isError ||
    productsQuery.isError;

  return (
    <AppShell>
      <PageHeader
        title="Inventory Balances & Ledger"
        subtitle="Immutable, ledger-backed stock records replacing spreadsheet cells across Reno and Columbus."
      />

      <LedgerNoticeBanner message="Inventory balances are the computed mathematical sum of all confirmed movement events. Quantities cannot be manually edited or overwritten." />

      {isLoading ? <LoadingState message="Loading multi-warehouse inventory ledger..." /> : null}
      {isError ? (
        <ErrorState
          message="Could not load inventory balances from backend."
          onRetry={() => {
            balancesQuery.refetch();
            movementsQuery.refetch();
            sellersQuery.refetch();
            warehousesQuery.refetch();
            productsQuery.refetch();
          }}
        />
      ) : null}

      {/* Top Metrics Cards: Sellable vs Non-Sellable */}
      <section className="mb-6 grid grid-cols-2 gap-3.5 sm:grid-cols-4">
        <Card className="border-l-4 border-l-emerald-600 p-4">
          <span className="text-[10px] font-bold tracking-wider text-emerald-800 uppercase">
            Sellable Available
          </span>
          <p className="mt-1 font-mono text-2xl font-extrabold text-emerald-950">
            {totalAvailable.toLocaleString()}
          </p>
          <p className="mt-1 text-[11px] text-slate-500 font-medium">Ready for order allocation</p>
        </Card>

        <Card className="border-l-4 border-l-amber-500 p-4">
          <span className="text-[10px] font-bold tracking-wider text-amber-800 uppercase">
            Reserved for Orders
          </span>
          <p className="mt-1 font-mono text-2xl font-extrabold text-amber-950">
            {totalReserved.toLocaleString()}
          </p>
          <p className="mt-1 text-[11px] text-slate-500 font-medium">Locked during pick/pack</p>
        </Card>

        <Card className="border-l-4 border-l-rose-500 p-4">
          <span className="text-[10px] font-bold tracking-wider text-rose-800 uppercase">
            Damaged (Crushed/Broken)
          </span>
          <p className="mt-1 font-mono text-2xl font-extrabold text-rose-950">
            {totalDamaged.toLocaleString()}
          </p>
          <p className="mt-1 text-[11px] text-slate-500 font-medium">Non-sellable dock damage</p>
        </Card>

        <Card className="border-l-4 border-l-purple-500 p-4">
          <span className="text-[10px] font-bold tracking-wider text-purple-800 uppercase">
            Quarantined / Returns
          </span>
          <p className="mt-1 font-mono text-2xl font-extrabold text-purple-950">
            {totalQuarantined.toLocaleString()}
          </p>
          <p className="mt-1 text-[11px] text-slate-500 font-medium">
            Awaiting physical inspection
          </p>
        </Card>
      </section>

      {/* Filter & Barcode Search Bar */}
      <Card className="mb-5 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          {/* Scanner Search Input */}
          <div className="w-full sm:w-80">
            <ScannerInputField
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Scan barcode, SKU, product name..."
            />
          </div>

          {/* Facility Dropdown */}
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <label className="flex items-center gap-1.5 font-bold text-foreground">
              <WarehouseIcon className="size-3.5 text-primary" />
              <span>Facility:</span>
              <select
                value={selectedWarehouseId}
                onChange={(e) => setSelectedWarehouseId(e.target.value)}
                className="rounded-full border border-border bg-white px-3.5 py-1.5 text-xs font-bold text-foreground shadow-xs outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 transition-all cursor-pointer"
              >
                <option value="ALL">All Facilities (RNO & CMH)</option>
                {warehouses.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.code} ({w.city || "Hub"})
                  </option>
                ))}
              </select>
            </label>

            {/* Seller Filter */}
            <label className="flex items-center gap-1.5 font-bold text-foreground">
              <span>Seller:</span>
              <select
                value={selectedSellerId}
                onChange={(e) => setSelectedSellerId(e.target.value)}
                className="rounded-full border border-border bg-white px-3.5 py-1.5 text-xs font-bold text-foreground shadow-xs outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 transition-all cursor-pointer"
              >
                <option value="ALL">All Sellers</option>
                {sellers.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.code})
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>

        {/* State Pill Filter Strip */}
        <div className="mt-3.5 flex flex-wrap items-center gap-1.5 border-t border-slate-100 pt-3">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mr-1">
            State Filter:
          </span>
          {STATES.map((s) => (
            <button
              key={s}
              onClick={() => setSelectedState(s)}
              className={`rounded-md border px-2.5 py-1 text-xs font-semibold transition-all cursor-pointer ${
                selectedState === s
                  ? "border-blue-600 bg-blue-600 text-white shadow-xs"
                  : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
              }`}
            >
              {s.replaceAll("_", " ")}
            </button>
          ))}
        </div>
      </Card>

      {/* Main Balances Table */}
      <section className="mb-8">
        <div className="mb-2.5 flex items-center justify-between">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700">
            Current Stock Balances ({filteredBalances.length} records)
          </h2>
        </div>

        {filteredBalances.length === 0 ? (
          <Card className="p-8">
            <EmptyState
              message="No inventory balances found matching current filters"
              hint="Try clearing search query or selecting 'ALL' facilities."
            />
          </Card>
        ) : (
          <TableShell>
            <thead>
              <tr>
                <Th>Product SKU</Th>
                <Th>Product Name</Th>
                <Th>Seller Tenant</Th>
                <Th>Warehouse Facility</Th>
                <Th>Inventory State</Th>
                <Th>Classification</Th>
                <Th className="text-right">Quantity</Th>
              </tr>
            </thead>
            <tbody>
              {filteredBalances.map((b) => {
                const isSellable = b.inventory_state === "AVAILABLE";
                const whCode = warehouses.find((w) => w.id === b.warehouse_id)?.code || "WH";

                return (
                  <tr key={b.id} className="hover:bg-slate-50/80 transition-colors">
                    <Td className="font-mono font-bold text-slate-900">
                      {productSku(products, b.product_id)}
                    </Td>
                    <Td className="font-medium text-slate-800">
                      {productName(products, b.product_id)}
                    </Td>
                    <Td className="text-slate-600 font-medium">
                      {sellerLabel(sellers, b.seller_id)}
                    </Td>
                    <Td>
                      <FacilityBadge code={whCode} />
                    </Td>
                    <Td>
                      <StatusBadge value={b.inventory_state} />
                    </Td>
                    <Td>
                      <span
                        className={`inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-semibold border ${
                          isSellable
                            ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                            : "bg-slate-100 text-slate-600 border-slate-200"
                        }`}
                      >
                        {isSellable ? "Sellable" : "Non-Sellable"}
                      </span>
                    </Td>
                    <Td className="text-right font-mono text-sm font-extrabold text-slate-900">
                      {formatQty(b.quantity)}
                    </Td>
                  </tr>
                );
              })}
            </tbody>
          </TableShell>
        )}
      </section>

      {/* Movement Ledger Audit Section */}
      <section>
        <div className="mb-2.5 flex items-center justify-between border-b border-slate-200 pb-2">
          <div>
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-tight flex items-center gap-2">
              <Database className="size-4 text-blue-600" />
              <span>Immutable Movement Ledger Trail</span>
            </h2>
            <p className="text-xs text-slate-500 font-medium">
              Every stock delta is permanently stamped with workflow, actor, and source document ID.
            </p>
          </div>
          <span className="text-xs font-mono text-slate-400">Append-Only</span>
        </div>

        {movements.length === 0 ? (
          <Card className="p-6">
            <EmptyState
              message="No ledger movements recorded yet"
              hint="Movement events generate automatically as receipts, orders, transfers, and returns are completed."
            />
          </Card>
        ) : (
          <TableShell>
            <thead>
              <tr>
                <Th>Recorded Timestamp</Th>
                <Th>Product SKU</Th>
                <Th>Facility</Th>
                <Th>Movement Type</Th>
                <Th>Source Reference</Th>
                <Th className="text-right">Quantity Delta</Th>
              </tr>
            </thead>
            <tbody>
              {movements.slice(0, 15).map((m) => {
                const deltaNum = Number(m.quantity_delta || 0);
                const isPositive = deltaNum >= 0;
                const whCode = warehouses.find((w) => w.id === m.warehouse_id)?.code || "WH";

                return (
                  <tr key={m.id} className="hover:bg-slate-50">
                    <Td className="font-mono text-xs text-slate-600">
                      {formatDate(m.occurred_at)}
                    </Td>
                    <Td className="font-mono font-bold text-slate-900">
                      {productSku(products, m.product_id)}
                    </Td>
                    <Td>
                      <FacilityBadge code={whCode} />
                    </Td>
                    <Td>
                      <StatusBadge value={m.movement_type} />
                    </Td>
                    <Td className="font-mono text-xs text-slate-500">
                      {m.source_type
                        ? `${m.source_type}: ${m.source_id.slice(0, 8)}`
                        : m.source_id?.slice(0, 8) || "Ledger Entry"}
                    </Td>
                    <Td
                      className={`text-right font-mono font-extrabold text-sm ${
                        isPositive ? "text-emerald-700" : "text-rose-700"
                      }`}
                    >
                      {isPositive ? "+" : ""}
                      {formatQty(m.quantity_delta)}
                    </Td>
                  </tr>
                );
              })}
            </tbody>
          </TableShell>
        )}
      </section>
    </AppShell>
  );
}
