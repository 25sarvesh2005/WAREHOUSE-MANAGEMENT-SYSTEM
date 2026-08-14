import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import {
  Bell,
  Bot,
  Boxes,
  ClipboardList,
  Database,
  FileSpreadsheet,
  LayoutDashboard,
  LogOut,
  Menu,
  PackageCheck,
  Repeat,
  Search,
  Settings,
  ShieldCheck,
  ShoppingCart,
  Truck,
  Undo2,
} from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useOperationalStatusReportQuery } from "@/hooks/use-api";
import { ROLE_SECTIONS, signOutAsync, useAuth } from "@/lib/auth";
import { initials } from "@/lib/format";

interface NavItem {
  to: string;
  label: string;
  icon: typeof LayoutDashboard;
}

const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/inventory", label: "Inventory", icon: Boxes },
  { to: "/receipts", label: "Receipts", icon: PackageCheck },
  { to: "/orders", label: "Orders", icon: ShoppingCart },
  { to: "/pick-tasks", label: "Pick Tasks", icon: ClipboardList },
  { to: "/shipments", label: "Shipments", icon: Truck },
  { to: "/transfers", label: "Transfers", icon: Repeat },
  { to: "/returns", label: "Returns", icon: Undo2 },
  { to: "/migration", label: "Migration", icon: FileSpreadsheet },
  { to: "/ai-assistant", label: "AI Assistant", icon: Bot },
];

export function AppShell({ children }: { children: ReactNode }) {
  const { user, ready } = useAuth();
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const [mobileOpen, setMobileOpen] = useState(false);
  const [globalSearch, setGlobalSearch] = useState("");
  const statusReportQuery = useOperationalStatusReportQuery({ enabled: Boolean(user) });

  useEffect(() => {
    if (ready && !user) navigate({ to: "/login" });
  }, [navigate, ready, user]);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  const accessibleItems = useMemo(() => {
    if (!user) return [];
    const allowedPaths = ROLE_SECTIONS[user.role] ?? [];
    return NAV_ITEMS.filter((item) => allowedPaths.includes(item.to));
  }, [user]);

  if (!ready || !user) {
    return <div className="min-h-screen bg-background" />;
  }

  const health = statusReportQuery.data;
  const systemHealthy = health?.status === "HEALTHY";
  const aiStatus = health?.ai?.status ?? "UNKNOWN";
  const voiceConfigured = Boolean(health?.voice?.stt_configured || health?.voice?.tts_configured);

  const handleGlobalSearch = (event: React.FormEvent) => {
    event.preventDefault();
    const query = globalSearch.trim().toUpperCase();
    if (!query) return;

    if (query.startsWith("REC-") || query.startsWith("1Z")) {
      navigate({ to: "/receipts" });
    } else if (query.startsWith("ORD-") || query.startsWith("SO-")) {
      navigate({ to: "/orders" });
    } else if (query.startsWith("TRF-")) {
      navigate({ to: "/transfers" });
    } else if (query.startsWith("RET-") || query.startsWith("RMA-")) {
      navigate({ to: "/returns" });
    } else {
      navigate({ to: "/inventory" });
    }
  };

  const sidebar = (
    <div className="flex h-full w-[232px] flex-col border-r border-border bg-card">
      <div className="px-5 py-5">
        <div className="flex items-center gap-2.5">
          <span className="flex size-10 items-center justify-center rounded-2xl bg-primary text-sm font-bold text-primary-foreground shadow-[0_8px_18px_rgba(37,99,235,0.22)]">
            W
          </span>
          <div className="min-w-0">
            <p className="truncate text-[15px] font-semibold tracking-tight text-foreground">
              Whitfield Ops
            </p>
            <p className="truncate text-xs text-muted-foreground">Warehouse console</p>
          </div>
        </div>
      </div>

      <div className="mx-4 mb-4 grid grid-cols-2 gap-2 rounded-3xl bg-primary-tint p-2 text-center text-[11px] font-semibold text-primary">
        <span className="rounded-full bg-white px-2 py-1.5 shadow-[0_1px_5px_rgba(37,99,235,0.08)]">
          RNO
        </span>
        <span className="rounded-full bg-white px-2 py-1.5 shadow-[0_1px_5px_rgba(37,99,235,0.08)]">
          CMH
        </span>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3">
        {accessibleItems.map(({ to, label, icon: Icon }) => (
          <Link
            key={to}
            to={to}
            activeOptions={{ exact: to === "/" }}
            className="flex items-center gap-3 rounded-full px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted [&.active]:bg-primary-tint [&.active]:text-primary"
          >
            <Icon className="size-4.5" />
            {label}
          </Link>
        ))}

        {["ADMINISTRATOR", "WAREHOUSE_MANAGER"].includes(user.role) ? (
          <>
            <div className="my-3 border-t border-border" />
            <Link
              to="/admin"
              className="flex items-center gap-3 rounded-full px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted [&.active]:bg-primary-tint [&.active]:text-primary"
            >
              <Settings className="size-4.5" />
              Admin Panel
            </Link>
          </>
        ) : null}
      </nav>

      <div className="border-t border-border px-4 py-4">
        <div className="mb-4 rounded-3xl border border-border bg-background p-3">
          <div className="flex items-center justify-between text-xs">
            <span className="flex items-center gap-2 font-medium text-foreground">
              <span
                className={`size-2 rounded-full ${systemHealthy ? "bg-primary" : "bg-status-amber"}`}
              />
              Ledger API
            </span>
            <span className="text-muted-foreground">{health?.alembic_head ?? "checking"}</span>
          </div>
          <div className="mt-2 grid grid-cols-2 gap-2 text-[11px] text-muted-foreground">
            <span>AI: {aiStatus}</span>
            <span>Voice: {voiceConfigured ? "Ready" : "Manual"}</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
            {initials(user.name)}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-foreground">{user.name}</p>
            <p className="truncate text-xs text-muted-foreground">
              {user.role.replaceAll("_", " ")}
            </p>
          </div>
          <button
            aria-label="Sign out"
            onClick={async () => {
              await signOutAsync();
              navigate({ to: "/login" });
            }}
            className="rounded-full p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-primary"
          >
            <LogOut className="size-4" />
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex min-h-screen bg-background">
      <aside className="sticky top-0 hidden h-screen shrink-0 lg:block">{sidebar}</aside>

      {mobileOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            aria-label="Close navigation"
            className="absolute inset-0 bg-navy/40"
            onClick={() => setMobileOpen(false)}
          />
          <div className="absolute inset-y-0 left-0">{sidebar}</div>
        </div>
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-border bg-background/85 px-4 py-3 backdrop-blur md:px-6">
          <button
            aria-label="Open navigation"
            className="rounded-full p-2 text-muted-foreground hover:bg-muted lg:hidden"
            onClick={() => setMobileOpen(true)}
          >
            <Menu className="size-5" />
          </button>

          <form onSubmit={handleGlobalSearch} className="relative max-w-xl flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={globalSearch}
              onChange={(event) => setGlobalSearch(event.target.value)}
              placeholder="Search orders, SKUs, tracking numbers..."
              className="w-full rounded-full border border-transparent bg-muted py-2 pl-9 pr-4 text-sm text-foreground outline-none placeholder:text-muted-foreground focus:border-primary focus:bg-card"
            />
          </form>

          <span className="hidden items-center gap-1.5 rounded-full bg-primary-tint px-3 py-2 text-xs font-semibold text-primary md:inline-flex">
            <Database className="size-4" />
            Ledger
          </span>
          <span className="hidden items-center gap-1.5 rounded-full bg-primary-tint px-3 py-2 text-xs font-semibold text-primary md:inline-flex">
            <ShieldCheck className="size-4" />
            Scoped
          </span>
          <Link
            to="/ai-assistant"
            className="hidden items-center gap-1.5 rounded-full bg-primary-tint px-3 py-2 text-xs font-semibold text-primary transition-colors hover:bg-blue-100 sm:inline-flex"
          >
            <Bot className="size-4" />
            AI
          </Link>
          <button className="relative rounded-full p-2 text-muted-foreground hover:bg-muted">
            <Bell className="size-5" />
            <span className="absolute right-1.5 top-1.5 size-2 rounded-full bg-primary" />
          </button>
          <span className="flex size-9 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
            {initials(user.name)}
          </span>
        </header>

        <main className="flex-1 p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
