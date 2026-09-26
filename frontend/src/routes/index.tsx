import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { AppShell } from "@/components/AppShell";
import { Dashboard } from "@/components/Dashboard";
import { useAuth } from "@/lib/auth";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Whitfield WMS" },
      {
        name: "description",
        content: "Secure warehouse operations and inventory management.",
      },
    ],
  }),
  component: Index,
});

function Index() {
  const { user, ready } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (ready && !user) {
      void navigate({ to: "/login", replace: true });
    }
  }, [ready, user, navigate]);

  if (!ready || !user) {
    return (
      <div
        role="status"
        aria-live="polite"
        className="flex min-h-screen items-center justify-center bg-background text-sm text-muted-foreground"
      >
        Checking session…
      </div>
    );
  }

  return (
    <AppShell>
      <Dashboard user={user} />
    </AppShell>
  );
}
