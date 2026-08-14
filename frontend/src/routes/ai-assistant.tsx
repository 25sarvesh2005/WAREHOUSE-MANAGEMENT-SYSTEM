import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { Bot, ShieldCheck } from "lucide-react";
import { useEffect } from "react";
import { AppShell } from "@/components/AppShell";
import { AiAssistant } from "@/components/AiAssistant";
import { PageHeader } from "@/components/ui-kit";
import { useAuth } from "@/lib/auth";

export const Route = createFileRoute("/ai-assistant")({
  head: () => ({
    meta: [
      { title: "Operations AI Assistant | Whitfield Ops" },
      {
        name: "description",
        content:
          "Read-only AI assistant for inventory, orders, receipts, transfers, shipments and returns. AI cannot mutate any records.",
      },
      { property: "og:title", content: "Operations AI Assistant | Whitfield Ops" },
      {
        property: "og:description",
        content:
          "Ask the AI about inventory availability, ledger history, or operational record status.",
      },
    ],
  }),
  component: AiAssistantPage,
});

function AiAssistantPage() {
  const { user, ready } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (ready && !user) void navigate({ to: "/login" });
  }, [ready, user, navigate]);

  if (!ready || !user) return <div className="min-h-screen bg-slate-900" />;

  return (
    <AppShell>
      <PageHeader
        title="Operations AI Assistant"
        subtitle="Read-only inquiry engine for inventory availability, ledger audits, exception summaries, and draft recommendations."
        actions={
          <span className="inline-flex items-center gap-1.5 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-800">
            <ShieldCheck className="size-3.5 text-indigo-600" />
            Read-Only Guard Active
          </span>
        }
      />
      <div className="mx-auto max-w-3xl">
        <AiAssistant userRole={user.role} />
      </div>
    </AppShell>
  );
}
