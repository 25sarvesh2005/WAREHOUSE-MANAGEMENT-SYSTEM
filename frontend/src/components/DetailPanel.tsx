import { Link } from "@tanstack/react-router";
import { ArrowLeft } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { StatusBadge } from "@/components/StatusBadge";
import { Card, IconTile, TableShell, Td, Th, Timeline } from "@/components/ui-kit";
import { formatQty } from "@/lib/format";
import type { EventLogEntry, LineItem } from "@/lib/types";

export function DetailPanel({
  backTo,
  backLabel,
  title,
  status,
  chips,
  lines,
  events,
  banner,
  actions,
}: {
  backTo: "/receipts" | "/transfers" | "/returns";
  backLabel: string;
  title: string;
  status: string;
  chips: { icon: LucideIcon; label: string; value: string }[];
  lines: LineItem[];
  events: EventLogEntry[];
  banner?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div>
      <Link
        to={backTo}
        className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-primary"
      >
        <ArrowLeft className="size-4" /> {backLabel}
      </Link>

      {banner}

      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-semibold tracking-tight text-navy">{title}</h1>
          <StatusBadge value={status} />
        </div>
        {actions ? <div className="flex flex-wrap gap-2">{actions}</div> : null}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        <div className="space-y-6">
          <Card className="grid gap-4 p-5 sm:grid-cols-2 xl:grid-cols-4">
            {chips.map((c) => (
              <div key={c.label} className="flex items-center gap-3">
                <IconTile icon={c.icon} size="sm" />
                <div className="min-w-0">
                  <p className="text-xs text-muted-foreground">{c.label}</p>
                  <p className="truncate text-sm font-semibold text-navy">{c.value}</p>
                </div>
              </div>
            ))}
          </Card>

          <div>
            <h2 className="mb-3 font-semibold text-navy">Lines</h2>
            <TableShell>
              <thead>
                <tr>
                  <Th>SKU</Th>
                  <Th>Product</Th>
                  <Th className="text-right">Quantity</Th>
                </tr>
              </thead>
              <tbody>
                {lines.map((l) => (
                  <tr key={l.id} className="hover:bg-primary-tint/40">
                    <Td className="font-medium">{l.sku}</Td>
                    <Td className="text-muted-foreground">{l.product_name}</Td>
                    <Td className="text-right">{formatQty(l.quantity)}</Td>
                  </tr>
                ))}
              </tbody>
            </TableShell>
          </div>
        </div>

        <Card className="p-5">
          <h2 className="mb-4 font-semibold text-navy">Event log</h2>
          <Timeline items={events} />
        </Card>
      </div>
    </div>
  );
}
