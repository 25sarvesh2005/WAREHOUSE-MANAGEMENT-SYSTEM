import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/AppShell";
import { Dashboard } from "@/components/Dashboard";
import { Landing } from "@/components/Landing";
import { useAuth } from "@/lib/auth";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Whitfield Logistics — Nationwide Fulfillment & Live Inventory Network" },
      {
        name: "description",
        content:
          "Bicoastal 3PL fulfillment network in Reno, NV and Columbus, OH. Real-time multi-channel inventory sync, AI-assisted supply chain analytics, and audit-grade ledger precision.",
      },
      { property: "og:title", content: "Whitfield Logistics — Nationwide Fulfillment & Live Inventory Network" },
      {
        property: "og:description",
        content: "2-Day delivery to 98% of the US from our Reno and Columbus fulfillment centers.",
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
