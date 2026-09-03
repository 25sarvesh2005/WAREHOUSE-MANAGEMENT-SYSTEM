import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import {
  Bell,
  Bot,
  Boxes,
  ClipboardList,
  Database,
  FileSpreadsheet,
  Globe2,
  LayoutDashboard,
  LogOut,
  Menu,
  PackageCheck,
  Repeat,
  Search,
  Settings,
  ShieldCheck,
  ShoppingCart,
  Sparkles,
  Truck,
  Undo2,
  Warehouse,
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
  { to: "/receipts", label: "Inbound Receipts", icon: PackageCheck },
  { to: "/orders", label: "Customer Orders", icon: ShoppingCart },
  { to: "/pick-tasks", label: "Pick Tasks", icon: ClipboardList },
  { to: "/shipments", label: "Outbound Shipments", icon: Truck },
  { to: "/transfers", label: "Hub Transfers", icon: Repeat },
  { to: "/returns", label: "Returns & RMAs", icon: Undo2 },
  { to: "/migration", label: "Inventory Migration", icon: FileSpreadsheet },
  { to: "/ai-assistant", label: "AI Copilot", icon: Bot },
];

export function AppShell({ children }: { children: ReactNode }) {
  const { user, ready } = useAuth();
  const navigate = useNavigate();
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const [mobileOpen, setMobileOpen] = useState(false);
  const [globalSearch, setGlobalSearch] = useState("");
  const statusReportQuery = useOperationalStatusReportQuery({ enabled: Boolean(ready && user) });

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
  const aiStatus = health?.ai?.status ?? "ONLINE";

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
    <div className="flex h-full w-[240px] flex-col border-r border-border bg-card">
      <div className="px-5 py-5 border-b border-border/60">
        <Link to="/" className="flex items-center gap-3">
          <span className="flex size-10 items-center justify-center rounded-2xl bg-gradient-to-tr from-primary-dark via-primary to-blue-500 text-sm font-bold text-white shadow-[0_8px_18px_rgba(37,99,235,0.24)]">
            W
          </span>
          <div className="min-w-0">
            <p className="truncate text-[15px] font-bold tracking-tight text-foreground">
              Whitfield <span className="text-primary">Logistics</span>
            </p>
            <p className="truncate text-xs text-muted-foreground font-medium">
              Client & Ops Portal
            </p>
          </div>
        </Link>
      </div>

      <div className="mx-4 my-3 grid grid-cols-2 gap-2 rounded-2xl bg-muted/60 p-2 text-center text-[11px] font-bold">
        <span className="inline-flex items-center justify-center gap-1 rounded-xl bg-white px-2 py-1 text-primary shadow-sm">
          <span className="size-1.5 rounded-full bg-emerald-500" /> RNO Hub
        </span>
        <span className="inline-flex items-center justify-center gap-1 rounded-xl bg-white px-2 py-1 text-primary shadow-sm">
          <span className="size-1.5 rounded-full bg-emerald-500" /> CMH Hub
        </span>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-2">
        {accessibleItems.map(({ to, label, icon: Icon }) => (
          <Link
            key={to}
            to={to}
            activeOptions={{ exact: to === "/" }}
            className="flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-semibold text-muted-foreground transition-all hover:bg-muted hover:text-foreground [&.active]:bg-primary-tint [&.active]:text-primary"
          >
            <Icon className="size-4.5 shrink-0" />
            <span>{label}</span>
          </Link>
        ))}

        {["ADMINISTRATOR", "WAREHOUSE_MANAGER"].includes(user.role) ? (
          <>
            <div className="my-3 border-t border-border/80" />
            <Link
              to="/admin"
              className="flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-semibold text-muted-foreground transition-all hover:bg-muted hover:text-foreground [&.active]:bg-primary-tint [&.active]:text-primary"
            >
              <Settings className="size-4.5 shrink-0" />
              <span>Admin Console</span>
            </Link>
          </>
        ) : null}
      </nav>

      <div className="border-t border-border px-4 py-4">
        <div className="mb-4 rounded-2xl border border-border/80 bg-background/80 p-3">
          <div className="flex items-center justify-between text-xs font-semibold">
            <span className="flex items-center gap-1.5 text-foreground">
              <span
                className={`size-2 rounded-full ${systemHealthy ? "bg-emerald-500" : "bg-amber-500"}`}
              />
              Fulfillment Network
            </span>
            <span className="text-[11px] font-mono text-emerald-600">ONLINE</span>
          </div>
          <div className="mt-2 flex items-center justify-between text-[11px] text-muted-foreground">
            <span>Bicoastal 2-Day SLA</span>
            <span className="font-semibold text-primary">99.98%</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-bold text-white shadow-sm">
            {initials(user.name)}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-bold text-foreground">{user.name}</p>
            <p className="truncate text-xs text-muted-foreground font-medium">
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
            className="absolute inset-0 bg-navy/40 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />
          <div className="absolute inset-y-0 left-0">{sidebar}</div>
        </div>
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-border bg-background/90 px-4 py-3 backdrop-blur-md md:px-6">
          <button
            aria-label="Open navigation"
            className="rounded-full p-2 text-muted-foreground hover:bg-muted lg:hidden"
            onClick={() => setMobileOpen(true)}
          >
            <Menu className="size-5" />
          </button>

          <form onSubmit={handleGlobalSearch} className="relative max-w-xl flex-1">
            <Search className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <input
              value={globalSearch}
              onChange={(event) => setGlobalSearch(event.target.value)}
              placeholder="Search Orders (ORD-), Receipts (REC-), Transfers (TRF-), or SKUs..."
              className="w-full rounded-full border border-border/80 bg-white py-2 pl-10 pr-4 text-sm text-foreground shadow-sm outline-none placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/15"
            />
          </form>

          {/* Network Facility Badges */}
          <div className="hidden items-center gap-2 md:flex">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-700">
              <span className="size-1.5 rounded-full bg-emerald-500" /> RNO Reno
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-700">
              <span className="size-1.5 rounded-full bg-emerald-500" /> CMH Columbus
            </span>
          </div>

          <Link
            to="/ai-assistant"
            className="hidden items-center gap-1.5 rounded-full bg-gradient-to-r from-primary-tint to-blue-100 px-3.5 py-1.5 text-xs font-bold text-primary transition-all hover:shadow-sm sm:inline-flex border border-primary/20"
          >
            <Sparkles className="size-3.5" />
            AI Copilot
          </Link>

          <button className="relative rounded-full p-2 text-muted-foreground hover:bg-muted transition-colors">
            <Bell className="size-4.5" />
            <span className="absolute right-1.5 top-1.5 size-2 rounded-full bg-primary" />
          </button>

          <div className="flex items-center gap-2 pl-2 border-l border-border">
            <span className="flex size-9 items-center justify-center rounded-full bg-primary font-bold text-xs text-white shadow-sm">
              {initials(user.name)}
            </span>
          </div>
        </header>

        <main className="flex-1 p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
