import { Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowRight,
  Bot,
  Boxes,
  CheckCircle2,
  Globe2,
  Layers,
  Loader2,
  Lock,
  Mail,
  MapPin,
  PackageCheck,
  PackageSearch,
  Repeat,
  Search,
  Sparkles,
  Store,
  Truck,
  Undo2,
} from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui-kit";
import { registerSellerPublicApi } from "@/lib/api-services";
import { signInAsync } from "@/lib/auth";

interface FacilityInfo {
  code: string;
  name: string;
  location: string;
  sqft: string;
  dockDoors: number;
  coverage: string;
  features: string[];
  status: "ONLINE" | "EXPANDING";
}

const NETWORK_HUBS: FacilityInfo[] = [
  {
    code: "RNO",
    name: "Reno Fulfillment Center",
    location: "Reno, Nevada",
    sqft: "250,000 sq. ft.",
    dockDoors: 28,
    coverage: "West Coast, Pacific Northwest, California Same-Day/1-Day & Mountain West",
    features: [
      "Port of Oakland direct logistics corridor",
      "Late Pacific 6:00 PM PST carrier cutoff",
      "Dedicated high-velocity pick towers",
      "Temperature-monitored quarantine zones",
    ],
    status: "ONLINE",
  },
  {
    code: "CMH",
    name: "Columbus Fulfillment Center",
    location: "Columbus, Ohio",
    sqft: "320,000 sq. ft.",
    dockDoors: 36,
    coverage: "Midwest, Mid-Atlantic, New England, Southeast & 47% of US Population in 10h drive",
    features: [
      "Major interstate nexus (I-70 / I-71 corridor)",
      "High-throughput cross-docking infrastructure",
      "Automated sortation & pallet conveyor systems",
      "Full returns inspection & refurb grading lab",
    ],
    status: "ONLINE",
  },
];

const CAPABILITIES = [
  {
    icon: Truck,
    title: "Omnichannel B2C & B2B Fulfillment",
    subtitle: "DTC, Wholesale & Retail Prep",
    description:
      "Seamlessly fulfill direct-to-consumer orders, Amazon FBA prep, TikTok Shop, and EDI wholesale shipments from unified inventory pools with zero split-order friction.",
    badge: "99.98% Accuracy",
  },
  {
    icon: Boxes,
    title: "Real-Time Client Inventory Ledger",
    subtitle: "100% Audit-Grade Transparency",
    description:
      "Track live Sellable, Reserved, Damaged, and Quarantined stock across all facilities. Every unit movement is recorded in an immutable, append-only ledger.",
    badge: "Live Balance Sync",
  },
  {
    icon: PackageCheck,
    title: "High-Throughput Dock Inbound",
    subtitle: "Sub-12h Dock-to-Stock SLA",
    description:
      "Advanced receiving with barcode verification, duplicate tracking prevention, voice-assisted intake, and instant discrepancy flagging right at the unloading bay.",
    badge: "< 12h Turnaround",
  },
  {
    icon: Repeat,
    title: "Intelligent Network Transfers",
    subtitle: "Dynamic Inventory Rebalancing",
    description:
      "Algorithmically rebalance stock between Reno and Columbus to position goods closer to your highest-density customer clusters and cut shipping zone costs.",
    badge: "Cost Optimization",
  },
  {
    icon: Undo2,
    title: "Frictionless Reverse Logistics",
    subtitle: "RMA Inspection & Rapid Restock",
    description:
      "Customer returns are verified, photographed, graded (A/B/C/Scrap), and immediately routed back to active sellable stock or quarantine within hours.",
    badge: "Rapid Grading",
  },
  {
    icon: Bot,
    title: "AI Logistics Intelligence",
    subtitle: "Natural Language Analytics",
    description:
      "Query inventory velocity, track batch movement histories, diagnose order exceptions, and receive actionable restock recommendations with our AI copilot.",
    badge: "Powered by Gemini",
  },
];

interface TrackingItem {
  type: "ORDER" | "INBOUND" | "TRANSFER";
  id: string;
  status: string;
  facility: string;
  details: string;
  steps: Array<{ label: string; done: boolean; timestamp?: string }>;
}

const SAMPLE_TRACKING_DATA: Record<string, TrackingItem> = {
  "ORD-1001": {
    type: "ORDER",
    id: "ORD-1001",
    status: "DISPATCHED",
    facility: "Reno Hub (RNO)",
    details: "Priority 2-Day Air • 4 Items • Tracking # 1Z999AA10123456784",
    steps: [
      { label: "Order Received & Reserved", done: true, timestamp: "Today, 08:30 AM" },
      { label: "Batch Picked in Aisle B-04", done: true, timestamp: "Today, 10:15 AM" },
      { label: "Packed & Weight Verified", done: true, timestamp: "Today, 11:45 AM" },
      { label: "Handed to Carrier (UPS)", done: true, timestamp: "Today, 02:20 PM" },
    ],
  },
  "REC-1001": {
    type: "INBOUND",
    id: "REC-1001",
    status: "INSPECTION COMPLETED",
    facility: "Columbus Hub (CMH)",
    details: "Dock Bay 04 • 450 Units Received • 0 Damaged • 100% Match",
    steps: [
      { label: "Carrier Arrived at Dock", done: true, timestamp: "Yesterday, 02:00 PM" },
      { label: "Pallets Unloaded & Scanned", done: true, timestamp: "Yesterday, 03:30 PM" },
      { label: "QC Inspection & Barcode Check", done: true, timestamp: "Today, 09:00 AM" },
      { label: "Posted to Active Sellable Inventory", done: true, timestamp: "Today, 10:15 AM" },
    ],
  },
  "TRF-1001": {
    type: "TRANSFER",
    id: "TRF-1001",
    status: "IN TRANSIT",
    facility: "RNO -> CMH",
    details: "Freight Line #FL-882 • 2,400 Units • Estimated Arrival Tomorrow",
    steps: [
      { label: "Transfer Requested & Approved", done: true, timestamp: "2 Days Ago" },
      { label: "Picked & Palletized at Reno (RNO)", done: true, timestamp: "Yesterday" },
      { label: "Dispatched via Interstate Transit", done: true, timestamp: "Yesterday, 06:00 PM" },
      { label: "Arrival & Putaway at Columbus (CMH)", done: false },
    ],
  },
};

export function Landing() {
  const navigate = useNavigate();
  const [panel, setPanel] = useState<"SIGN_IN" | "SELLER">("SIGN_IN");
  const [loginEmail, setLoginEmail] = useState("admin@whitfield.local");
  const [loginPassword, setLoginPassword] = useState("");
  const [loginError, setLoginError] = useState<string | null>(null);
  const [loginBusy, setLoginBusy] = useState(false);

  // Seller registration state
  const [regName, setRegName] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regPassword, setRegPassword] = useState("");
  const [regCompany, setRegCompany] = useState("");
  const [regCode, setRegCode] = useState("");
  const [regError, setRegError] = useState<string | null>(null);
  const [regSubmitted, setRegSubmitted] = useState(false);
  const [regBusy, setRegBusy] = useState(false);

  // Interactive Live Tracker state
  const [searchQuery, setSearchQuery] = useState("ORD-1001");
  const [trackedResult, setTrackedResult] = useState<TrackingItem | null>(
    SAMPLE_TRACKING_DATA["ORD-1001"] ?? null,
  );

  async function handleLoginSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoginError(null);
    if (!loginEmail.includes("@")) return setLoginError("Valid email required.");
    if (loginPassword.length < 8) return setLoginError("Password must be at least 8 characters.");

    setLoginBusy(true);
    try {
      await signInAsync(loginEmail, loginPassword);
      navigate({ to: "/", replace: true });
    } catch (err: unknown) {
      setLoginError(err instanceof Error ? err.message : "Sign in failed. Check credentials.");
    } finally {
      setLoginBusy(false);
    }
  }

  function handleQuickLogin(accountType: "ADMIN" | "MANAGER" | "RECEIVER" | "PICKER" | "SELLER") {
    if (accountType === "ADMIN") {
      setLoginEmail("admin@whitfield.local");
      setLoginPassword("");
    } else if (accountType === "MANAGER") {
      setLoginEmail("manager@whitfield.local");
      setLoginPassword("Manager123!");
    } else if (accountType === "RECEIVER") {
      setLoginEmail("receiver@whitfield.local");
      setLoginPassword("Receiver123!");
    } else if (accountType === "PICKER") {
      setLoginEmail("picker@whitfield.local");
      setLoginPassword("Picker123!");
    } else if (accountType === "SELLER") {
      setLoginEmail("seller@whitfield.local");
      setLoginPassword("Seller123!");
    }
    setLoginError(null);
  }

  async function handleRegisterSubmit(e: React.FormEvent) {
    e.preventDefault();
    setRegError(null);
    if (!regName.trim()) return setRegError("Full name required.");
    if (!regEmail.includes("@")) return setRegError("Valid email required.");
    if (!regCompany.trim()) return setRegError("Company or brand name is required.");
    if (regPassword.length < 6) return setRegError("Password must be at least 6 characters.");

    setRegBusy(true);
    try {
      await registerSellerPublicApi({
        name: regName,
        email: regEmail,
        password: regPassword,
        company_name: regCompany,
        ...(regCode ? { seller_code: regCode } : {}),
      });
      setRegSubmitted(true);
    } catch (err: unknown) {
      setRegError(err instanceof Error ? err.message : "Registration request failed.");
    } finally {
      setRegBusy(false);
    }
  }

  function handleTrackLookup(e: React.FormEvent) {
    e.preventDefault();
    const clean = searchQuery.trim().toUpperCase();
    if (SAMPLE_TRACKING_DATA[clean]) {
      setTrackedResult(SAMPLE_TRACKING_DATA[clean]);
    } else {
      setTrackedResult({
        type: clean.startsWith("REC") ? "INBOUND" : clean.startsWith("TRF") ? "TRANSFER" : "ORDER",
        id: clean || "ORD-LIVE",
        status: "PROCESSING IN NETWORK",
        facility: clean.includes("RNO") ? "Reno Hub (RNO)" : "Columbus Hub (CMH)",
        details: `Live record verified • Verified at Whitfield Facility • 100% Stock Reserved`,
        steps: [
          { label: "Entry Logged in Ledger", done: true, timestamp: "Today, 09:12 AM" },
          {
            label: "Facility Allocation & Barcode Verification",
            done: true,
            timestamp: "Today, 10:45 AM",
          },
          { label: "Active Staging & Inspection", done: true, timestamp: "In Progress" },
          { label: "Carrier Handoff & Dispatch", done: false },
        ],
      });
    }
  }

  return (
    <main className="min-h-screen bg-background text-foreground selection:bg-primary/20 selection:text-primary">
      {/* Top Network Status Banner */}
      <div className="border-b border-primary/20 bg-primary-dark px-4 py-2 text-center text-xs font-medium text-white sm:px-6">
        <div className="mx-auto flex max-w-7xl items-center justify-center gap-2">
          <span className="flex size-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>
            <strong>Bicoastal Fulfillment Network Active</strong> — Reno (RNO) & Columbus (CMH) hubs
            operating at 99.98% on-time dispatch.
          </span>
        </div>
      </div>

      {/* Main Navigation Bar */}
      <header className="sticky top-0 z-50 border-b border-border/80 bg-white/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3.5 sm:px-6 lg:px-8">
          <Link to="/" className="flex items-center gap-3">
            <span className="flex size-10 items-center justify-center rounded-2xl bg-gradient-to-tr from-primary-dark via-primary to-blue-500 text-base font-bold text-white shadow-[0_8px_20px_rgba(37,99,235,0.28)]">
              W
            </span>
            <span>
              <span className="block text-base font-bold tracking-tight text-foreground">
                Whitfield <span className="text-primary">Logistics</span>
              </span>
              <span className="block text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                Enterprise Fulfillment Network
              </span>
            </span>
          </Link>

          <nav className="hidden items-center gap-8 text-sm font-semibold text-muted-foreground lg:flex">
            <a href="#network" className="transition-colors hover:text-primary">
              Fulfillment Network
            </a>
            <a href="#capabilities" className="transition-colors hover:text-primary">
              Solutions
            </a>
            <a href="#live-tracker" className="transition-colors hover:text-primary">
              Live Tracking
            </a>
            <a href="#ai-intelligence" className="transition-colors hover:text-primary">
              AI Copilot
            </a>
            <a href="#access" className="transition-colors hover:text-primary">
              Client Portal
            </a>
          </nav>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => {
                const el = document.getElementById("access");
                el?.scrollIntoView({ behavior: "smooth" });
                setPanel("SIGN_IN");
              }}
              className="hidden rounded-full px-4 py-2 text-sm font-semibold text-foreground transition-colors hover:bg-muted sm:inline-flex"
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                const el = document.getElementById("access");
                el?.scrollIntoView({ behavior: "smooth" });
                setPanel("SELLER");
              }}
              className="inline-flex items-center gap-2 rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-white shadow-[0_8px_18px_rgba(37,99,235,0.24)] transition-all hover:bg-primary-dark hover:shadow-[0_10px_24px_rgba(37,99,235,0.34)]"
            >
              Open Seller Account
              <ArrowRight className="size-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden border-b border-border/60 bg-gradient-to-b from-white via-[#f8faff] to-[#edf4fe] py-16 lg:py-24">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_-20%,rgba(37,99,235,0.12),transparent)]" />

        <div className="relative mx-auto grid max-w-7xl gap-12 px-4 sm:px-6 lg:grid-cols-[1.1fr_0.9fr] lg:items-center lg:px-8">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary-tint px-3.5 py-1.5 text-xs font-semibold text-primary shadow-sm">
              <Sparkles className="size-4" />
              <span>Bicoastal 3PL & Intelligent Inventory Infrastructure</span>
            </div>

            <h1 className="mt-6 text-4xl font-extrabold tracking-tight text-foreground sm:text-5xl lg:text-6xl">
              Next-Generation Fulfillment & Live Inventory Operations.
            </h1>

            <p className="mt-6 max-w-2xl text-lg leading-relaxed text-muted-foreground">
              Reach <strong>98% of the United States in 2 days</strong> from our modern Reno, NV and
              Columbus, OH fulfillment centers. Powered by real-time inventory ledger precision,
              automated carrier dispatch, and AI-driven supply chain analytics.
            </p>

            <div className="mt-8 flex flex-wrap items-center gap-4">
              <button
                type="button"
                onClick={() => {
                  const el = document.getElementById("access");
                  el?.scrollIntoView({ behavior: "smooth" });
                  setPanel("SIGN_IN");
                }}
                className="inline-flex items-center gap-2 rounded-full bg-primary px-7 py-3.5 text-base font-semibold text-white shadow-[0_10px_24px_rgba(37,99,235,0.26)] transition-all hover:bg-primary-dark hover:-translate-y-0.5"
              >
                Access Client Portal
                <ArrowRight className="size-4.5" />
              </button>
              <button
                type="button"
                onClick={() => {
                  const el = document.getElementById("live-tracker");
                  el?.scrollIntoView({ behavior: "smooth" });
                }}
                className="inline-flex items-center gap-2 rounded-full border border-border bg-white px-6 py-3.5 text-base font-semibold text-foreground shadow-sm transition-all hover:border-primary/40 hover:bg-primary-tint/30"
              >
                <PackageSearch className="size-4.5 text-primary" />
                Track an Order / Inbound
              </button>
            </div>

            {/* Live Metrics Grid */}
            <div className="mt-12 grid grid-cols-2 gap-4 border-t border-border/80 pt-8 sm:grid-cols-4">
              <div>
                <p className="font-mono text-2xl font-bold tracking-tight text-primary sm:text-3xl">
                  99.98%
                </p>
                <p className="mt-1 text-xs font-medium text-muted-foreground">
                  Pick & Pack Accuracy
                </p>
              </div>
              <div>
                <p className="font-mono text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
                  &lt; 12h
                </p>
                <p className="mt-1 text-xs font-medium text-muted-foreground">Dock-to-Stock SLA</p>
              </div>
              <div>
                <p className="font-mono text-2xl font-bold tracking-tight text-primary sm:text-3xl">
                  98%
                </p>
                <p className="mt-1 text-xs font-medium text-muted-foreground">
                  2-Day US Population Reach
                </p>
              </div>
              <div>
                <p className="font-mono text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
                  100%
                </p>
                <p className="mt-1 text-xs font-medium text-muted-foreground">Audit-Grade Ledger</p>
              </div>
            </div>
          </div>

          {/* Hero Live Interactive Card Preview */}
          <div className="relative">
            <div className="rounded-[2rem] border border-border/80 bg-white p-6 shadow-[0_20px_50px_rgba(15,23,42,0.09)] sm:p-8">
              <div className="flex items-center justify-between border-b border-border pb-4">
                <div className="flex items-center gap-2.5">
                  <span className="flex size-3 rounded-full bg-emerald-500 animate-ping" />
                  <span className="font-semibold text-sm text-foreground">Live Network Pulse</span>
                </div>
                <span className="rounded-full bg-primary-tint px-3 py-1 font-mono text-xs font-bold text-primary">
                  ALL HUBS OPERATIONAL
                </span>
              </div>

              <div className="mt-5 space-y-4">
                <div className="rounded-2xl border border-border/70 bg-[#fafcff] p-4 transition-all hover:border-primary/30">
                  <div className="flex items-center justify-between">
                    <span className="inline-flex items-center gap-2 text-xs font-bold text-primary">
                      <MapPin className="size-3.5" /> RENO, NV HUB (RNO)
                    </span>
                    <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full">
                      Receiving & Shipping
                    </span>
                  </div>
                  <div className="mt-2.5 flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Active Sellable Units:</span>
                    <span className="font-mono font-bold text-foreground">42,850 units</span>
                  </div>
                  <div className="mt-1 flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Today's Dispatch SLA:</span>
                    <span className="font-mono font-semibold text-emerald-600">
                      100% on schedule
                    </span>
                  </div>
                </div>

                <div className="rounded-2xl border border-border/70 bg-[#fafcff] p-4 transition-all hover:border-primary/30">
                  <div className="flex items-center justify-between">
                    <span className="inline-flex items-center gap-2 text-xs font-bold text-amber-700">
                      <MapPin className="size-3.5" /> COLUMBUS, OH HUB (CMH)
                    </span>
                    <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full">
                      Receiving & Shipping
                    </span>
                  </div>
                  <div className="mt-2.5 flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Active Sellable Units:</span>
                    <span className="font-mono font-bold text-foreground">68,410 units</span>
                  </div>
                  <div className="mt-1 flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Inbound Dock Velocity:</span>
                    <span className="font-mono font-semibold text-primary">12 Trucks Cleared</span>
                  </div>
                </div>

                {/* Quick 1-Click Demo Shortcut */}
                <div className="rounded-2xl bg-gradient-to-r from-primary-tint to-blue-100/60 p-4">
                  <p className="text-xs font-bold uppercase tracking-wider text-primary">
                    Instant Experience Preview
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Test drive the platform with pre-configured client or staff access:
                  </p>
                  <div className="mt-3 flex gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        handleQuickLogin("SELLER");
                        const el = document.getElementById("access");
                        el?.scrollIntoView({ behavior: "smooth" });
                      }}
                      className="flex-1 rounded-xl bg-white px-3 py-2 text-xs font-bold text-primary shadow-sm hover:bg-primary hover:text-white transition-colors"
                    >
                      🏢 Seller Client View
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        handleQuickLogin("ADMIN");
                        const el = document.getElementById("access");
                        el?.scrollIntoView({ behavior: "smooth" });
                      }}
                      className="flex-1 rounded-xl bg-white px-3 py-2 text-xs font-bold text-foreground shadow-sm hover:bg-primary-dark hover:text-white transition-colors"
                    >
                      📦 Warehouse Admin View
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Strategic Bicoastal Network Section */}
      <section id="network" className="border-b border-border bg-white py-16 sm:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-3xl text-center">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-primary-tint px-3.5 py-1 text-xs font-semibold text-primary">
              <Globe2 className="size-3.5" /> Strategically Positioned Facilities
            </span>
            <h2 className="mt-4 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Nationwide Reach with Bi-Coastal Fulfillment Hubs
            </h2>
            <p className="mt-4 text-base text-muted-foreground">
              By splitting your inventory between Reno and Columbus, you reduce transit zones, cut
              shipping rates by up to 35%, and reach virtually all continental customers in 2 days
              via standard ground.
            </p>
          </div>

          <div className="mt-12 grid gap-8 lg:grid-cols-2">
            {NETWORK_HUBS.map((hub) => (
              <div
                key={hub.code}
                className="group relative rounded-3xl border border-border bg-card p-8 transition-all hover:border-primary/40 hover:shadow-panel"
              >
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <span className="flex size-12 items-center justify-center rounded-2xl bg-primary font-mono text-lg font-bold text-white shadow-md">
                      {hub.code}
                    </span>
                    <div>
                      <h3 className="text-xl font-bold text-foreground">{hub.name}</h3>
                      <p className="text-sm text-muted-foreground">{hub.location}</p>
                    </div>
                  </div>
                  <span className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700 border border-emerald-200">
                    ● ACTIVE FACILITY
                  </span>
                </div>

                <div className="mt-6 grid grid-cols-2 gap-4 rounded-2xl bg-muted/60 p-4 text-sm">
                  <div>
                    <span className="text-xs text-muted-foreground">Facility Footprint:</span>
                    <p className="font-semibold text-foreground">{hub.sqft}</p>
                  </div>
                  <div>
                    <span className="text-xs text-muted-foreground">Loading Bay Capacity:</span>
                    <p className="font-semibold text-foreground">{hub.dockDoors} Dock Doors</p>
                  </div>
                  <div className="col-span-2 border-t border-border/60 pt-2">
                    <span className="text-xs text-muted-foreground">Primary Shipping Zone:</span>
                    <p className="font-semibold text-primary">{hub.coverage}</p>
                  </div>
                </div>

                <div className="mt-6 space-y-2.5">
                  <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                    Key Infrastructure Advantages:
                  </p>
                  {hub.features.map((feature) => (
                    <div key={feature} className="flex items-center gap-2.5 text-sm">
                      <CheckCircle2 className="size-4 shrink-0 text-primary" />
                      <span className="text-foreground">{feature}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Interactive Live Shipment & Order Tracker */}
      <section id="live-tracker" className="border-b border-border bg-[#f8faff] py-16 sm:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-primary-tint px-3.5 py-1 text-xs font-semibold text-primary">
              <PackageSearch className="size-3.5" /> Real-Time Transparency
            </span>
            <h2 className="mt-3 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Live Shipment & Dock Intake Tracker
            </h2>
            <p className="mt-3 text-sm text-muted-foreground">
              Search any Customer Order ID (e.g. <code>ORD-1001</code>), Dock Inbound Ticket (e.g.{" "}
              <code>REC-1001</code>), or Transfer (e.g. <code>TRF-1001</code>) to view real-time
              status.
            </p>
          </div>

          <div className="mx-auto mt-10 max-w-3xl">
            <form onSubmit={handleTrackLookup} className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-4 top-1/2 size-5 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Enter Order # (ORD-1001), Receipt # (REC-1001), or Tracking #"
                  className="w-full rounded-2xl border border-border bg-white py-3.5 pl-12 pr-4 font-mono text-sm font-semibold uppercase shadow-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/20"
                />
              </div>
              <Button type="submit" className="rounded-2xl px-6 font-semibold">
                Track Status
              </Button>
            </form>

            <div className="mt-3 flex flex-wrap items-center justify-center gap-2 text-xs text-muted-foreground">
              <span>Quick test queries:</span>
              {["ORD-1001", "REC-1001", "TRF-1001"].map((sample) => (
                <button
                  key={sample}
                  type="button"
                  onClick={() => {
                    setSearchQuery(sample);
                    if (SAMPLE_TRACKING_DATA[sample]) {
                      setTrackedResult(SAMPLE_TRACKING_DATA[sample]);
                    }
                  }}
                  className="rounded-lg bg-white px-2.5 py-1 font-mono font-semibold text-primary border border-border/80 hover:bg-primary-tint transition-colors"
                >
                  {sample}
                </button>
              ))}
            </div>

            {trackedResult && (
              <div className="mt-8 rounded-3xl border border-border bg-white p-6 sm:p-8 shadow-card animate-rise">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-5">
                  <div>
                    <span className="font-mono text-xs font-bold text-primary">
                      {trackedResult.type} IDENTIFIER
                    </span>
                    <h3 className="font-mono text-2xl font-bold text-foreground">
                      {trackedResult.id}
                    </h3>
                  </div>
                  <div className="text-right">
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-primary-tint px-3.5 py-1 text-xs font-bold text-primary">
                      ● {trackedResult.status}
                    </span>
                    <p className="mt-1 text-xs text-muted-foreground">{trackedResult.facility}</p>
                  </div>
                </div>

                <p className="mt-4 text-sm font-medium text-foreground">{trackedResult.details}</p>

                {/* Tracking Milestones Timeline */}
                <div className="mt-8 relative">
                  <div className="space-y-6">
                    {trackedResult.steps.map((step, idx) => (
                      <div key={step.label} className="relative flex items-start gap-4">
                        <span
                          className={`flex size-8 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                            step.done
                              ? "bg-primary text-white shadow-md shadow-primary/30"
                              : "bg-muted text-muted-foreground border border-border"
                          }`}
                        >
                          {step.done ? <CheckCircle2 className="size-4.5" /> : idx + 1}
                        </span>
                        <div className="pt-0.5">
                          <p
                            className={`text-sm font-semibold ${
                              step.done ? "text-foreground" : "text-muted-foreground"
                            }`}
                          >
                            {step.label}
                          </p>
                          {step.timestamp && (
                            <p className="text-xs text-muted-foreground">{step.timestamp}</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Solutions & Capabilities Grid */}
      <section id="capabilities" className="border-b border-border bg-white py-16 sm:py-24">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-3xl text-center">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-primary-tint px-3.5 py-1 text-xs font-semibold text-primary">
              <Layers className="size-3.5" /> Comprehensive Operations
            </span>
            <h2 className="mt-4 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Engineered for High-Growth E-Commerce & Retail Brands
            </h2>
            <p className="mt-4 text-base text-muted-foreground">
              Eliminate stockouts, blind spots, and fulfillment errors. Every capability is designed
              for enterprise accuracy and speed.
            </p>
          </div>

          <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {CAPABILITIES.map((cap) => {
              const Icon = cap.icon;
              return (
                <article
                  key={cap.title}
                  className="group relative rounded-3xl border border-border bg-card p-7 transition-all hover:-translate-y-1 hover:border-primary/40 hover:shadow-panel"
                >
                  <div className="flex items-center justify-between">
                    <span className="flex size-12 items-center justify-center rounded-2xl bg-primary-tint text-primary transition-colors group-hover:bg-primary group-hover:text-white">
                      <Icon className="size-6" />
                    </span>
                    <span className="rounded-full bg-muted px-3 py-1 font-mono text-xs font-semibold text-muted-foreground">
                      {cap.badge}
                    </span>
                  </div>

                  <h3 className="mt-5 text-lg font-bold text-foreground">{cap.title}</h3>
                  <p className="text-xs font-medium text-primary">{cap.subtitle}</p>
                  <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                    {cap.description}
                  </p>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      {/* AI Assistant & Copilot Showcase */}
      <section
        id="ai-intelligence"
        className="border-b border-border bg-gradient-to-br from-slate-900 via-[#0b1b36] to-slate-950 py-16 sm:py-24 text-white"
      >
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid gap-12 lg:grid-cols-2 lg:items-center">
            <div>
              <span className="inline-flex items-center gap-2 rounded-full border border-blue-400/30 bg-blue-500/10 px-3.5 py-1.5 text-xs font-semibold text-blue-300">
                <Bot className="size-4" /> AI Operations Copilot
              </span>
              <h2 className="mt-6 text-3xl font-extrabold tracking-tight sm:text-4xl lg:text-5xl">
                Real-Time Supply Chain Intelligence in Plain English.
              </h2>
              <p className="mt-4 text-base text-slate-300 leading-relaxed">
                Empower your inventory managers and client success teams to query real-time stock
                balances, diagnose order exceptions, and get instant explanations for any inventory
                movement across Reno and Columbus.
              </p>

              <div className="mt-8 space-y-4">
                {[
                  "Read-only verified data queries — Zero hallucinations on inventory numbers",
                  "Automated short-pick & transfer discrepancy root-cause detection",
                  "Push-to-talk voice receiving intake parsing with instant draft generation",
                  "100% audited interaction trail for enterprise governance",
                ].map((item) => (
                  <div key={item} className="flex items-center gap-3">
                    <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-blue-500 text-white text-xs font-bold">
                      ✓
                    </span>
                    <span className="text-sm text-slate-200">{item}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Mock Copilot Chat Terminal */}
            <div className="rounded-3xl border border-slate-700 bg-slate-900/90 p-6 shadow-2xl backdrop-blur-xl">
              <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                <div className="flex items-center gap-2">
                  <span className="size-3 rounded-full bg-red-500" />
                  <span className="size-3 rounded-full bg-amber-500" />
                  <span className="size-3 rounded-full bg-emerald-500" />
                  <span className="ml-2 font-mono text-xs text-slate-400">
                    whitfield-copilot-v1
                  </span>
                </div>
                <span className="text-xs font-mono text-blue-400 font-semibold">ONLINE</span>
              </div>

              <div className="mt-5 space-y-4 text-sm">
                <div className="rounded-2xl bg-slate-800/80 p-4 text-slate-200">
                  <p className="text-xs font-bold text-blue-400">CLIENT INQUIRY:</p>
                  <p className="mt-1">
                    "How many units of SKU-APEX-01 are sellable in Reno vs Columbus, and do we have
                    pending orders?"
                  </p>
                </div>

                <div className="rounded-2xl border border-blue-500/30 bg-blue-950/40 p-4 text-slate-100">
                  <p className="flex items-center gap-2 text-xs font-bold text-emerald-400">
                    <Bot className="size-4" /> WHITFIELD AI RESPONSE:
                  </p>
                  <p className="mt-2 text-xs leading-relaxed text-slate-300">
                    • <strong>Reno Hub (RNO):</strong> 1,240 Sellable units (180 Reserved for active
                    wave picks).
                    <br />• <strong>Columbus Hub (CMH):</strong> 3,100 Sellable units (45 Reserved).
                    <br />• <strong>Total Available:</strong> 4,115 Sellable units ready for
                    same-day dispatch.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Client Portal Sign In & Registration Section */}
      <section id="access" className="border-b border-border bg-[#f8faff] py-16 sm:py-24">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-primary-tint px-3.5 py-1 text-xs font-semibold text-primary">
              <Lock className="size-3.5" /> Secure Client & Staff Access
            </span>
            <h2 className="mt-3 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Access the Whitfield Operations Portal
            </h2>
            <p className="mt-3 text-sm text-muted-foreground">
              Sign in to manage your inventory, review orders, and track shipments.
            </p>
          </div>

          <div className="mt-10 rounded-[2.5rem] border border-border bg-white p-6 sm:p-10 shadow-panel">
            <div className="mb-8 flex rounded-full bg-muted p-1.5 text-sm font-semibold max-w-md mx-auto">
              <button
                type="button"
                onClick={() => setPanel("SIGN_IN")}
                className={`flex-1 rounded-full py-2.5 text-center transition-all ${
                  panel === "SIGN_IN"
                    ? "bg-white text-primary shadow-sm font-bold"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Sign In to Portal
              </button>
              <button
                type="button"
                onClick={() => setPanel("SELLER")}
                className={`flex-1 rounded-full py-2.5 text-center transition-all ${
                  panel === "SELLER"
                    ? "bg-white text-primary shadow-sm font-bold"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                Open Seller Account
              </button>
            </div>

            {panel === "SIGN_IN" ? (
              <form onSubmit={handleLoginSubmit} className="max-w-xl mx-auto space-y-4">
                {loginError && <ErrorBox message={loginError} />}

                {/* 1-Click Demo Buttons */}
                <div className="rounded-2xl border border-primary/20 bg-primary-tint/50 p-4 text-xs">
                  <span className="font-bold text-primary uppercase tracking-wider text-[10px]">
                    1-Click Quick Demo Login:
                  </span>
                  <div className="mt-2.5 flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => handleQuickLogin("ADMIN")}
                      className="rounded-xl bg-white px-3 py-1.5 font-bold text-foreground shadow-xs border border-border hover:bg-primary-dark hover:text-white transition-all cursor-pointer whitespace-nowrap shrink-0 text-xs"
                    >
                      👑 Admin
                    </button>
                    <button
                      type="button"
                      onClick={() => handleQuickLogin("MANAGER")}
                      className="rounded-xl bg-white px-3 py-1.5 font-bold text-foreground shadow-xs border border-border hover:bg-primary hover:text-white transition-all cursor-pointer whitespace-nowrap shrink-0 text-xs"
                    >
                      📊 Manager
                    </button>
                    <button
                      type="button"
                      onClick={() => handleQuickLogin("RECEIVER")}
                      className="rounded-xl bg-white px-3 py-1.5 font-bold text-foreground shadow-xs border border-border hover:bg-primary hover:text-white transition-all cursor-pointer whitespace-nowrap shrink-0 text-xs"
                    >
                      📥 Receiver
                    </button>
                    <button
                      type="button"
                      onClick={() => handleQuickLogin("PICKER")}
                      className="rounded-xl bg-white px-3 py-1.5 font-bold text-foreground shadow-xs border border-border hover:bg-primary hover:text-white transition-all cursor-pointer whitespace-nowrap shrink-0 text-xs"
                    >
                      📦 Picker
                    </button>
                    <button
                      type="button"
                      onClick={() => handleQuickLogin("SELLER")}
                      className="rounded-xl bg-white px-3 py-1.5 font-bold text-primary shadow-xs border border-primary/30 hover:bg-primary hover:text-white transition-all cursor-pointer whitespace-nowrap shrink-0 text-xs"
                    >
                      🏢 Seller
                    </button>
                  </div>
                </div>

                <InputField
                  label="Work Email Address"
                  type="email"
                  value={loginEmail}
                  onChange={setLoginEmail}
                  icon={<Mail className="size-4" />}
                />
                <InputField
                  label="Password"
                  type="password"
                  value={loginPassword}
                  onChange={setLoginPassword}
                  icon={<Lock className="size-4" />}
                />

                <Button
                  type="submit"
                  disabled={loginBusy}
                  className="w-full py-3.5 font-bold text-base mt-2"
                >
                  {loginBusy ? <Loader2 className="size-5 animate-spin" /> : null}
                  Sign in to Portal
                </Button>
              </form>
            ) : (
              <form onSubmit={handleRegisterSubmit} className="max-w-xl mx-auto space-y-4">
                {regSubmitted ? (
                  <div className="rounded-3xl border border-emerald-300 bg-emerald-50 p-6 text-center text-emerald-900">
                    <CheckCircle2 className="mx-auto size-12 text-emerald-600" />
                    <h3 className="mt-3 text-lg font-bold">Onboarding Request Received</h3>
                    <p className="mt-2 text-sm text-emerald-800">
                      Your seller tenant request for <strong>{regCompany}</strong> has been
                      submitted. Our team will verify your catalog profile and activate your portal
                      credentials shortly.
                    </p>
                  </div>
                ) : (
                  <>
                    {regError && <ErrorBox message={regError} />}
                    <div className="grid gap-3 sm:grid-cols-2">
                      <InputField
                        label="Company / Brand Name"
                        value={regCompany}
                        onChange={setRegCompany}
                        placeholder="Apex Brands Inc"
                      />
                      <InputField
                        label="Seller Code (Optional)"
                        value={regCode}
                        onChange={(v) => setRegCode(v.toUpperCase())}
                        placeholder="APEX"
                        mono
                      />
                    </div>
                    <InputField
                      label="Contact Full Name"
                      value={regName}
                      onChange={setRegName}
                      placeholder="Alex Whitfield"
                    />
                    <InputField
                      label="Work Email"
                      type="email"
                      value={regEmail}
                      onChange={setRegEmail}
                      placeholder="alex@company.com"
                      icon={<Mail className="size-4" />}
                    />
                    <InputField
                      label="Desired Password"
                      type="password"
                      value={regPassword}
                      onChange={setRegPassword}
                      placeholder="Minimum 6 characters"
                      icon={<Lock className="size-4" />}
                    />
                    <Button
                      type="submit"
                      disabled={regBusy}
                      className="w-full py-3.5 font-bold text-base mt-2"
                    >
                      {regBusy ? <Loader2 className="size-5 animate-spin" /> : null}
                      Submit Seller Application
                    </Button>
                  </>
                )}
              </form>
            )}
          </div>
        </div>
      </section>

      {/* Enterprise Footer */}
      <footer className="border-t border-border bg-white py-12 text-sm text-muted-foreground">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <div className="flex items-center gap-2.5">
                <span className="flex size-8 items-center justify-center rounded-xl bg-primary font-bold text-white text-sm">
                  W
                </span>
                <span className="font-bold text-foreground text-base">Whitfield Logistics</span>
              </div>
              <p className="mt-3 text-xs leading-relaxed">
                High-precision multi-warehouse fulfillment and inventory ledger technology for
                modern commerce.
              </p>
              <div className="mt-4 flex items-center gap-2">
                <span className="size-2 rounded-full bg-emerald-500" />
                <span className="text-xs font-semibold text-emerald-700">
                  All Facilities Operational
                </span>
              </div>
            </div>

            <div>
              <p className="font-bold text-foreground">Fulfillment Hubs</p>
              <ul className="mt-3 space-y-2 text-xs">
                <li>📍 Reno Hub (RNO) — 250k sq. ft.</li>
                <li>📍 Columbus Hub (CMH) — 320k sq. ft.</li>
                <li>🚚 Nationwide 2-Day Ground Reach</li>
              </ul>
            </div>

            <div>
              <p className="font-bold text-foreground">Platform Solutions</p>
              <ul className="mt-3 space-y-2 text-xs">
                <li>• Multi-Channel B2C/B2B Fulfillment</li>
                <li>• Append-Only Inventory Ledger</li>
                <li>• AI Supply Chain Analytics</li>
                <li>• Barcode Dock Receiving</li>
                <li>• Reverse Logistics & RMAs</li>
              </ul>
            </div>

            <div>
              <p className="font-bold text-foreground">Security & Compliance</p>
              <ul className="mt-3 space-y-2 text-xs">
                <li>🛡️ SOC2 Type II Aligned</li>
                <li>🔒 256-Bit Encrypted Data & APIs</li>
                <li>📋 100% Immutable Audit Trail</li>
                <li>⚡ 99.99% Guaranteed SLA Uptime</li>
              </ul>
            </div>
          </div>

          <div className="mt-12 border-t border-border/80 pt-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between text-xs">
            <p>© {new Date().getFullYear()} Whitfield Fulfillment Inc. All rights reserved.</p>
            <div className="flex gap-6">
              <a href="#network" className="hover:text-primary">
                Facilities
              </a>
              <a href="#capabilities" className="hover:text-primary">
                Services
              </a>
              <a href="#access" className="hover:text-primary">
                Client Portal
              </a>
            </div>
          </div>
        </div>
      </footer>
    </main>
  );
}

function InputField({
  icon,
  label,
  mono,
  onChange,
  placeholder,
  type = "text",
  value,
}: {
  icon?: React.ReactNode;
  label: string;
  mono?: boolean;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: string;
  value: string;
}) {
  return (
    <label className="block">
      <span className="text-xs font-semibold text-foreground uppercase tracking-wider">
        {label}
      </span>
      <div className="relative mt-1.5">
        {icon ? (
          <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground">
            {icon}
          </span>
        ) : null}
        <input
          type={type}
          value={value}
          placeholder={placeholder}
          onChange={(e) => onChange(e.target.value)}
          className={`w-full rounded-xl border border-input bg-white py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 transition-all ${
            icon ? "pl-10 pr-3.5" : "px-3.5"
          } ${mono ? "font-mono font-bold uppercase" : ""}`}
        />
      </div>
    </label>
  );
}

function ErrorBox({ message }: { message: string }) {
  return (
    <div className="rounded-xl border border-status-red/30 bg-status-red/5 px-4 py-3 text-xs font-semibold text-status-red">
      {message}
    </div>
  );
}
