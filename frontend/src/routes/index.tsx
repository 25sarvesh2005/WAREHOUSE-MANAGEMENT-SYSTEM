import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/AppShell";
import { Dashboard } from "@/components/Dashboard";
import { Landing } from "@/components/Landing";
import { useAuth } from "@/lib/auth";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Whitfield Ops — Warehouse Operations Platform" },
      {
        name: "description",
        content:
          "Multi-warehouse inventory, receiving, fulfillment, transfers and returns in one operating layer.",
      },
      { property: "og:title", content: "Whitfield Ops — Warehouse Operations Platform" },
      {
        property: "og:description",
        content: "Live inventory, role-based access and audit-ready logs across every site.",
      },
    ],
  }),
  component: Index,
});

function Index() {
  const { user, ready } = useAuth();
  if (!ready) return <div className="min-h-screen bg-background" />;
  if (!user) return <Landing />;
  return (
    <AppShell>
      <Dashboard user={user} />
    </AppShell>
  );
}
