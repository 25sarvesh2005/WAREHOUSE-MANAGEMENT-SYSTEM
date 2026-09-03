import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import {
  Bot,
  Boxes,
  ClipboardList,
  FileSpreadsheet,
  LayoutDashboard,
  LogOut,
  Menu,
  PackageCheck,
  Repeat,
  Search,
  Settings,
  ShoppingCart,
  Truck,
  Undo2,
} from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { toast } from "sonner";
import { useOperationalStatusReportQuery } from "@/hooks/use-api";
import { ROLE_SECTIONS, signOutAsync, useAuth } from "@/lib/auth";
import { initials } from "@/lib/format";
import { resolveGlobalSearch } from "@/lib/global-search";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";

interface NavItem {
  to: string;
  label: string;
  icon: typeof LayoutDashboard;
}

interface NavGroup {
  name: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    name: "Overview",
    items: [{ to: "/", label: "Dashboard", icon: LayoutDashboard }],
  },
  {
    name: "Inbound",
    items: [
      { to: "/receipts", label: "Receiving", icon: PackageCheck },
      { to: "/returns", label: "Returns", icon: Undo2 },
    ],
  },
  {
    name: "Inventory Control",
    items: [
      { to: "/inventory", label: "Inventory", icon: Boxes },
      { to: "/transfers", label: "Transfers", icon: Repeat },
    ],
  },
  {
    name: "Fulfillment",
    items: [
      { to: "/orders", label: "Orders", icon: ShoppingCart },
      { to: "/pick-tasks", label: "Pick Tasks", icon: ClipboardList },
      { to: "/shipments", label: "Shipments", icon: Truck },
    ],
  },
  {
    name: "Intelligence",
    items: [{ to: "/ai-assistant", label: "AI Assistant", icon: Bot }],
  },
  {
    name: "Administration",
    items: [
      { to: "/migration", label: "Inventory Migration", icon: FileSpreadsheet },
      { to: "/admin", label: "Admin", icon: Settings },
    ],
  },
];

function formatLastChecked(isoString?: string): string | null {
  if (!isoString) return null;
  const d = new Date(isoString);
  if (Number.isNaN(d.getTime())) return null;
  try {
    return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit", second: "2-digit" });
  } catch {
    return null;
  }
}

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

  const accessibleGroups = useMemo(() => {
    if (!user) return [];
    const allowedPaths = ROLE_SECTIONS[user.role] ?? [];
    return NAV_GROUPS.map((group) => ({
      ...group,
      items: group.items.filter((item) => allowedPaths.includes(item.to)),
    })).filter((group) => group.items.length > 0);
  }, [user]);

  if (!ready || !user) {
    return <div className="min-h-screen bg-background" />;
  }

  const health = statusReportQuery.data;

  const handleGlobalSearch = async (event: React.FormEvent) => {
    event.preventDefault();
    const trimmed = globalSearch.trim();
    if (!trimmed) return;

    const destination = resolveGlobalSearch(trimmed);
    if (!destination) {
      toast.error("Search format not recognized", {
        description:
          "Supported prefixes: ORD-, SO-, REC-, 1Z, TRF-, TRN-, RET-, RMA-, SKU-, PROD-",
      });
      return;
    }

    const allowedPaths = ROLE_SECTIONS[user.role] ?? [];
    if (!allowedPaths.includes(destination.route)) {
      toast.error(`You do not have access to search ${destination.label}.`);
      return;
    }

    try {
      switch (destination.route) {
        case "/orders":
          await navigate({ to: "/orders", search: { q: destination.q } });
          break;
        case "/receipts":
          await navigate({ to: "/receipts", search: { q: destination.q } });
          break;
        case "/transfers":
          await navigate({ to: "/transfers", search: { q: destination.q } });
          break;
        case "/returns":
          await navigate({ to: "/returns", search: { q: destination.q } });
          break;
        case "/inventory":
          await navigate({ to: "/inventory", search: { q: destination.q } });
          break;
      }
      setGlobalSearch("");
    } catch {
      toast.error("Search could not be opened");
    }
  };

  const sidebarContent = (
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

      <nav className="flex-1 space-y-4 overflow-y-auto px-3 py-2">
        {accessibleGroups.map((group) => (
          <div key={group.name} className="space-y-1">
            <p className="px-3 text-[11px] font-semibold tracking-wider text-muted-foreground/70 uppercase select-none">
              {group.name}
            </p>
            {group.items.map(({ to, label, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                activeOptions={{ exact: to === "/" }}
                onClick={() => setMobileOpen(false)}
                className="flex items-center gap-3 rounded-xl px-3.5 py-2 text-sm font-semibold text-muted-foreground transition-all hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 [&.active]:bg-primary-tint [&.active]:text-primary min-h-[44px]"
              >
                <Icon className="size-4.5 shrink-0" />
                <span>{label}</span>
              </Link>
            ))}
          </div>
        ))}
      </nav>

      <div className="border-t border-border px-4 py-4">
        {/* Operations Service Status Card */}
        {(() => {
          let statusLabel = "Checking";
          let statusColorClass = "text-muted-foreground";
          let dotColorClass = "bg-blue-500";
          let supportingText: React.ReactNode = null;
          let warningText: string | null = null;
          let showRetry = false;

          if (!health) {
            if (statusReportQuery.isError) {
              statusLabel = "Status unavailable";
              statusColorClass = "text-amber-700";
              dotColorClass = "bg-amber-500";
              supportingText = (
                <p className="text-[11px] text-muted-foreground">Live health could not be verified.</p>
              );
              showRetry = true;
            } else {
              statusLabel = "Checking";
              statusColorClass = "text-blue-600";
              dotColorClass = "bg-blue-500";
              supportingText = (
                <p className="text-[11px] text-muted-foreground">Checking live system health…</p>
              );
            }
          } else {
            const warningCount = health.warnings?.length ?? 0;
            if (warningCount === 1) {
              warningText = "1 configuration warning";
            } else if (warningCount > 1) {
              warningText = `${warningCount} configuration warnings`;
            }

            if (health.status === "HEALTHY") {
              statusLabel = "Operational";
              statusColorClass = "text-emerald-600 font-semibold";
              dotColorClass = "bg-emerald-500";

              let dbText = "Database status needs attention";
              if (health.database?.status === "connected") {
                if (
                  typeof health.database.latency_ms === "number" &&
                  Number.isFinite(health.database.latency_ms)
                ) {
                  dbText = `Database connected · ${health.database.latency_ms} ms`;
                } else {
                  dbText = "Database connected";
                }
              }
              supportingText = <p className="text-[11px] text-muted-foreground">{dbText}</p>;
            } else if (health.status === "DEGRADED") {
              statusLabel = "Degraded";
              statusColorClass = "text-amber-600 font-semibold";
              dotColorClass = "bg-amber-500";
              supportingText = (
                <p className="text-[11px] text-amber-700">Some system checks need attention.</p>
              );
            } else {
              statusLabel = "Unavailable";
              statusColorClass = "text-destructive font-semibold";
              dotColorClass = "bg-destructive";
              supportingText = (
                <p className="text-[11px] text-destructive">
                  The operations service reported an unhealthy state.
                </p>
              );
            }
          }

          const formattedTime = health ? formatLastChecked(health.timestamp) : null;

          return (
            <div
              role="status"
              aria-live="polite"
              aria-label={`System status: ${statusLabel}`}
              className="mb-4 rounded-2xl border border-border/80 bg-background/80 p-3 space-y-1.5"
            >
              <div className="flex items-center justify-between text-xs font-semibold">
                <span className="flex items-center gap-1.5 text-foreground">
                  <span className={`size-2 rounded-full ${dotColorClass}`} aria-hidden="true" />
                  Operations service
                </span>
                <span className={`text-xs ${statusColorClass}`}>{statusLabel}</span>
              </div>

              {supportingText}

              {warningText ? (
                <p className="text-[11px] font-medium text-amber-600">{warningText}</p>
              ) : null}

              {health && statusReportQuery.isFetching ? (
                <p className="text-[10px] text-muted-foreground">Refreshing…</p>
              ) : null}

              {formattedTime && health ? (
                <p className="text-[10px] text-muted-foreground">
                  Last checked <time dateTime={health.timestamp}>{formattedTime}</time>
                </p>
              ) : null}

              {showRetry ? (
                <button
                  type="button"
                  onClick={() => {
                    statusReportQuery.refetch();
                  }}
                  disabled={statusReportQuery.isFetching}
                  aria-busy={statusReportQuery.isFetching ? "true" : undefined}
                  className="mt-2 flex min-h-[44px] w-full items-center justify-center rounded-xl border border-border bg-white px-3 py-2 text-xs font-semibold text-foreground shadow-xs transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                >
                  {statusReportQuery.isFetching ? "Checking…" : "Retry status check"}
                </button>
              ) : null}
            </div>
          );
        })()}

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
            className="rounded-full p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-primary cursor-pointer"
          >
            <LogOut className="size-4" />
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex min-h-screen bg-background">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:rounded-xl focus:bg-primary focus:px-4 focus:py-2 focus:text-sm focus:font-bold focus:text-white focus:shadow-lg focus:outline-none focus:ring-2 focus:ring-primary/40"
      >
        Skip to main content
      </a>

      <aside className="sticky top-0 hidden h-screen shrink-0 lg:block">{sidebarContent}</aside>

      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent
          side="left"
          id="mobile-navigation"
          className="w-[260px] p-0 border-r border-border bg-card flex flex-col [&>button]:size-11 [&>button]:min-h-[44px] [&>button]:min-w-[44px] [&>button]:flex [&>button]:items-center [&>button]:justify-center [&>button]:right-2 [&>button]:top-2 [&>button]:rounded-full [&>button]:hover:bg-muted [&>button]:transition-colors"
        >
          <SheetHeader className="sr-only">
            <SheetTitle>Navigation Menu</SheetTitle>
            <SheetDescription>Access Whitfield Logistics operational sections and tools</SheetDescription>
          </SheetHeader>
          <div className="flex-1 overflow-y-auto">
            {sidebarContent}
          </div>
        </SheetContent>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-border bg-background/90 px-4 py-3 backdrop-blur-md md:px-6">
            <SheetTrigger asChild>
              <button
                aria-label="Open navigation"
                aria-expanded={mobileOpen}
                aria-controls="mobile-navigation"
                className="rounded-full p-2.5 text-muted-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 lg:hidden min-h-[44px] min-w-[44px] flex items-center justify-center cursor-pointer"
              >
                <Menu className="size-5" />
              </button>
            </SheetTrigger>

            <form onSubmit={handleGlobalSearch} className="relative max-w-xl flex-1 min-w-0">
              <Search className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <input
                aria-label="Search warehouse records"
                maxLength={100}
                value={globalSearch}
                onChange={(event) => setGlobalSearch(event.target.value)}
                placeholder="Search ORD-, REC-/1Z, TRF-/TRN-, RET-/RMA-, or SKU-…"
                className="w-full rounded-full border border-border/80 bg-white py-2 pl-10 pr-4 text-sm text-foreground shadow-sm outline-none placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/15"
              />
            </form>

            <div className="flex items-center lg:hidden">
              <span
                aria-label={`Signed in as ${user.name}`}
                className="flex size-9 items-center justify-center rounded-full bg-primary font-bold text-xs text-white shadow-sm"
              >
                {initials(user.name)}
              </span>
            </div>
          </header>

          <main id="main-content" tabIndex={-1} className="flex-1 p-4 md:p-6 outline-none">
            {children}
          </main>
        </div>
      </Sheet>
    </div>
  );
}
