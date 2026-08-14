import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/AppShell";
import { MigrationPanel } from "@/components/MigrationPanel";
import { PageHeader } from "@/components/ui-kit";

export const Route = createFileRoute("/migration")({
  head: () => ({
    meta: [
      { title: "Opening Inventory Migration | Whitfield Ops" },
      {
        name: "description",
        content:
          "Stage, validate, approve, and apply opening inventory batches with ledger movements.",
      },
    ],
  }),
  component: MigrationPage,
});

function MigrationPage() {
  return (
    <AppShell>
      <PageHeader
        title="Opening Inventory Migration"
        subtitle="Controlled spreadsheet staging, multi-rule validation, approval guards, and movement ledger application."
      />
      <MigrationPanel />
    </AppShell>
  );
}
