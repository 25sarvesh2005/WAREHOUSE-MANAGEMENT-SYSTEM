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
import { ThemeToggle } from "@/components/ThemeToggle";
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

  const statusReportQuery = useOperationalStatusReportQuery();
  const health = statusReportQuery.data;

  // Protect client routes
  useEffect(() => {
    if (ready && !user) {
      navigate({ to: "/login" });
    }
  }, [ready, user, navigate]);

  const accessibleGroups = useMemo(() => {
    if (!user) return [];
    const allowed = new Set(ROLE_SECTIONS[user.role] ?? []);
    return NAV_GROUPS.map((group) => ({
      ...group,
      items: group.items.filter((item) => allowed.has(item.to)),
    })).filter((group) => group.items.length > 0);
  }, [user]);

  // Keep navigation in view on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  if (!ready || !user) {
    return (
      <div className="flex h-screen items-center justify-center bg-background text-foreground">
        <div className="size-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  const handleGlobalSearch = async (event: React.FormEvent) => {
    event.preventDefault();
    const query = globalSearch.trim();
    if (!query) return;

    try {
      const destination = resolveGlobalSearch(query);
      if (!destination) {
        toast.error("Search format not recognized");
        return;
      }

      const allowed = new Set(ROLE_SECTIONS[user.role] ?? []);
      if (!allowed.has(destination.route)) {
        toast.error(`You do not have access to search ${destination.label}.`);
        return;
      }

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
    <div className="flex h-full w-[240px] flex-col border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950">
      <div className="px-5 py-4 border-b border-slate-100 dark:border-slate-800">
        <Link
          to="/"
          aria-label="Whitfield Logistics dashboard"
          className="flex items-center gap-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 rounded-lg"
        >
          <span
            aria-hidden="true"
            className="flex size-9 items-center justify-center rounded-lg bg-primary text-sm font-bold text-white shadow-xs"
          >
            W
          </span>
          <div className="min-w-0">
            <p className="truncate text-sm font-bold tracking-tight text-slate-900 dark:text-slate-100">
              Whitfield <span className="text-primary font-bold">Logistics</span>
            </p>
            <p className="truncate text-[11px] text-slate-500 dark:text-slate-400 font-medium">
              Client & Ops Portal
            </p>
          </div>
        </Link>
      </div>

      <div role="group" aria-label="Warehouse locations" className="mx-3 my-2.5 flex items-center gap-2 px-2 text-xs text-slate-500 dark:text-slate-400">
        <span className="font-medium text-slate-700 dark:text-slate-300">Locations</span>
        <span>RNO · Reno</span>
        <span className="text-slate-300 dark:text-slate-700" aria-hidden="true">/</span>
        <span>CMH · Columbus</span>
      </div>

      <nav aria-label="Primary navigation" className="flex-1 space-y-4 overflow-y-auto px-3 py-2">
        {accessibleGroups.map((group) => (
          <div key={group.name} className="space-y-0.5">
            <p className="px-2.5 py-1 text-[11px] font-semibold tracking-wider text-slate-400 dark:text-slate-500 uppercase select-none">
              {group.name}
            </p>
            {group.items.map(({ to, label, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                activeOptions={{ exact: to === "/" }}
                onClick={() => setMobileOpen(false)}
                className="flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm font-medium text-slate-600 dark:text-slate-400 transition-colors hover:bg-slate-100 dark:hover:bg-slate-900 hover:text-slate-900 dark:hover:text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 [&.active]:bg-blue-50 dark:[&.active]:bg-blue-950/60 [&.active]:text-primary dark:[&.active]:text-blue-400 [&.active]:font-semibold min-h-[44px]"
              >
                <Icon className="size-4 shrink-0" aria-hidden="true" />
                <span>{label}</span>
              </Link>
            ))}
          </div>
        ))}
      </nav>

      <div className="border-t border-slate-100 dark:border-slate-800 px-3 py-3">
        {/* Operations Service Status Card */}
        {(() => {
          let statusLabel = "Checking";
          let statusColorClass = "text-slate-500 dark:text-slate-400";
          let dotColorClass = "bg-blue-500";
          let supportingText: React.ReactNode = null;
          let warningText: string | null = null;
          let showRetry = false;

          if (!health) {
            if (statusReportQuery.isError) {
              statusLabel = "Status unavailable";
              statusColorClass = "text-amber-700 dark:text-amber-400 font-semibold";
              dotColorClass = "bg-amber-500";
              supportingText = (
                <p className="text-[11px] text-slate-500 dark:text-slate-400">Live health could not be verified.</p>
              );
              showRetry = true;
            } else {
              statusLabel = "Checking";
              statusColorClass = "text-blue-600 dark:text-blue-400 font-semibold";
              dotColorClass = "bg-blue-500";
              supportingText = (
                <p className="text-[11px] text-slate-500 dark:text-slate-400">Checking live system health…</p>
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
              statusColorClass = "text-emerald-700 dark:text-emerald-400 font-semibold";
              dotColorClass = "bg-emerald-500";

              let dbText = "Database connected";
              if (health.database?.status === "connected") {
                if (
                  typeof health.database.latency_ms === "number" &&
                  Number.isFinite(health.database.latency_ms)
                ) {
                  dbText = `Database connected · ${health.database.latency_ms} ms`;
                }
              }
              supportingText = <p className="text-[11px] text-slate-500 dark:text-slate-400">{dbText}</p>;
            } else if (health.status === "DEGRADED") {
              statusLabel = "Degraded";
              statusColorClass = "text-amber-700 dark:text-amber-400 font-semibold";
              dotColorClass = "bg-amber-500";
              supportingText = (
                <p className="text-[11px] text-amber-700 dark:text-amber-400">Some system checks need attention.</p>
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
              className="mb-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/60 p-2.5 space-y-1"
            >
              <div className="flex items-center justify-between text-xs">
                <span className="flex items-center gap-1.5 font-semibold text-slate-800 dark:text-slate-200">
                  <span className={`size-2 rounded-full ${dotColorClass}`} aria-hidden="true" />
                  Operations service
                </span>
                <span className={`text-xs ${statusColorClass}`}>{statusLabel}</span>
              </div>

              {supportingText}

              {warningText ? (
                <p className="text-[11px] font-medium text-amber-600 dark:text-amber-400">{warningText}</p>
              ) : null}

              {health && statusReportQuery.isFetching ? (
                <p className="text-[10px] text-slate-400">Refreshing…</p>
              ) : null}

              {formattedTime && health ? (
                <p className="text-[10px] text-slate-400 dark:text-slate-500 font-mono">
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
                  className="mt-1.5 flex min-h-[44px] w-full items-center justify-center rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-2.5 py-1.5 text-xs font-semibold text-slate-700 dark:text-slate-200 shadow-xs hover:bg-slate-50 dark:hover:bg-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                >
                  {statusReportQuery.isFetching ? "Checking…" : "Retry status check"}
                </button>
              ) : null}
            </div>
          );
        })()}

        <div className="flex items-center gap-2 pt-1">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-slate-900 dark:bg-slate-800 text-xs font-bold text-white dark:text-slate-200">
            {initials(user?.name || "User")}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-bold text-slate-900 dark:text-slate-100">{user.name}</p>
            <p className="truncate text-[11px] text-slate-500 dark:text-slate-400 font-medium">
              {user.role.replaceAll("_", " ")}
            </p>
          </div>
          <ThemeToggle />
          <button
            type="button"
            aria-label="Sign out"
            onClick={async () => {
              await signOutAsync();
              navigate({ to: "/login" });
            }}
            className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg p-2 text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 cursor-pointer"
          >
            <LogOut className="size-4" aria-hidden="true" />
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex min-h-screen bg-background text-foreground">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:rounded-lg focus:bg-primary focus:px-4 focus:py-2 focus:text-sm focus:font-bold focus:text-white focus:shadow-md focus:outline-none focus:ring-2 focus:ring-primary/40"
      >
        Skip to main content
      </a>

      <aside className="sticky top-0 hidden h-screen shrink-0 lg:block">{sidebarContent}</aside>

      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent
          side="left"
          id="mobile-navigation"
          className="w-[260px] p-0 border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 flex flex-col [&>button]:size-11 [&>button]:min-h-[44px] [&>button]:min-w-[44px] [&>button]:flex [&>button]:items-center [&>button]:justify-center [&>button]:right-2 [&>button]:top-2 [&>button]:rounded-lg [&>button]:hover:bg-slate-100 dark:[&>button]:hover:bg-slate-800 [&>button]:transition-colors"
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
          <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-slate-200 dark:border-slate-800 bg-white/90 dark:bg-slate-950/90 px-4 py-2.5 backdrop-blur-md md:px-6">
            <SheetTrigger asChild>
              <button
                aria-label="Open navigation"
                aria-expanded={mobileOpen}
                aria-controls="mobile-navigation"
                className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 lg:hidden min-h-[44px] min-w-[44px] flex items-center justify-center cursor-pointer"
              >
                <Menu className="size-5" aria-hidden="true" />
              </button>
            </SheetTrigger>

            <form onSubmit={handleGlobalSearch} className="relative max-w-2xl flex-1 min-w-0">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400 dark:text-slate-500" aria-hidden="true" />
              <input
                aria-label="Search warehouse records"
                maxLength={100}
                value={globalSearch}
                onChange={(event) => setGlobalSearch(event.target.value)}
                placeholder="Search by order, receipt, transfer, return, or SKU"
                className="w-full min-h-10 rounded-md border border-input bg-slate-50 dark:bg-slate-900 py-2 pl-9 pr-3 text-sm text-slate-900 dark:text-slate-100 outline-none placeholder:text-slate-400 dark:placeholder:text-slate-500 focus:bg-white dark:focus:bg-slate-900 focus:border-primary focus:ring-2 focus:ring-primary/15 transition-[background-color,border-color,box-shadow] duration-150"
              />
            </form>

            <ThemeToggle className="hidden sm:inline-flex" />

            <div className="flex items-center lg:hidden">
              <span
                aria-label={`Signed in as ${user.name}`}
                className="flex size-8 items-center justify-center rounded-full bg-slate-900 dark:bg-slate-800 font-bold text-xs text-white"
              >
                {initials(user?.name || "User")}
              </span>
            </div>
          </header>

          <main id="main-content" tabIndex={-1} className="flex-1 p-4 outline-none sm:p-5 lg:p-7">
            <div className="mx-auto w-full max-w-[1600px]">
              {children}
            </div>
          </main>
        </div>
      </Sheet>
    </div>
  );
}
