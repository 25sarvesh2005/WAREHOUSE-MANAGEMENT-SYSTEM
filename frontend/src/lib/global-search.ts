export type GlobalSearchDestination =
  | { route: "/orders"; label: "Orders"; q: string }
  | { route: "/receipts"; label: "Receiving"; q: string }
  | { route: "/transfers"; label: "Transfers"; q: string }
  | { route: "/returns"; label: "Returns"; q: string }
  | { route: "/inventory"; label: "Inventory"; q: string };

export function resolveGlobalSearch(input: unknown): GlobalSearchDestination | null {
  if (typeof input !== "string") {
    return null;
  }

  const trimmed = input.trim();
  if (!trimmed) {
    return null;
  }

  const upper = trimmed.toUpperCase();

  if (upper.startsWith("ORD-") || upper.startsWith("SO-")) {
    return { route: "/orders", label: "Orders", q: trimmed };
  }

  if (upper.startsWith("REC-") || upper.startsWith("1Z")) {
    return { route: "/receipts", label: "Receiving", q: trimmed };
  }

  if (upper.startsWith("TRF-") || upper.startsWith("TRN-")) {
    return { route: "/transfers", label: "Transfers", q: trimmed };
  }

  if (upper.startsWith("RET-") || upper.startsWith("RMA-")) {
    return { route: "/returns", label: "Returns", q: trimmed };
  }

  if (upper.startsWith("SKU-") || upper.startsWith("PROD-")) {
    return { route: "/inventory", label: "Inventory", q: trimmed };
  }

  return null;
}

export function normalizeSearchQuery(value: unknown): string | undefined {
  if (typeof value !== "string") {
    return undefined;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return undefined;
  }
  return trimmed.slice(0, 100);
}
