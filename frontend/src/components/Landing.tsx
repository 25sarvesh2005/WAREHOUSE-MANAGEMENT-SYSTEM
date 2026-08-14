import { Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowRight,
  Boxes,
  CheckCircle2,
  ClipboardCheck,
  Clock,
  Loader2,
  Lock,
  Mail,
  PackageCheck,
  Repeat,
  ShieldCheck,
  Store,
  Truck,
  Undo2,
  Warehouse,
} from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui-kit";
import { registerSellerPublicApi } from "@/lib/api-services";
import { signInAsync } from "@/lib/auth";

const FACILITIES = [
  { code: "RNO", label: "Reno, Nevada", note: "West Coast and Pacific Northwest fulfillment" },
  { code: "CMH", label: "Columbus, Ohio", note: "Midwest, East Coast and Southern fulfillment" },
];

const CONTROL_POINTS = [
  {
    icon: PackageCheck,
    title: "Duplicate-safe receiving",
    copy: "Tracking numbers, seller drop-off tickets, UPC scans, and damaged counts are controlled at the dock.",
  },
  {
    icon: ShieldCheck,
    title: "Server-reserved stock",
    copy: "Orders reserve inventory through backend transactions instead of spreadsheet edits.",
  },
  {
    icon: Repeat,
    title: "RNO to CMH transfers",
    copy: "Inter-facility movement is approved, dispatched, received, and reconciled through the ledger.",
  },
  {
    icon: Undo2,
    title: "Returns quarantine",
    copy: "Returned items remain quarantined until inspection decides restock, damage, or rejection.",
  },
];

const ROLES = [
  "Administrator",
  "Warehouse manager",
  "Receiving operator",
  "Picker / packer",
  "Seller",
];

export function Landing() {
  const navigate = useNavigate();
  const [panel, setPanel] = useState<"SIGN_IN" | "SELLER">("SIGN_IN");
  const [loginEmail, setLoginEmail] = useState("admin@whitfield.local");
  const [loginPassword, setLoginPassword] = useState("");
  const [loginError, setLoginError] = useState<string | null>(null);
  const [loginBusy, setLoginBusy] = useState(false);
  const [regName, setRegName] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regPassword, setRegPassword] = useState("");
  const [regCompany, setRegCompany] = useState("");
  const [regCode, setRegCode] = useState("");
  const [regError, setRegError] = useState<string | null>(null);
  const [regSubmitted, setRegSubmitted] = useState(false);
  const [regBusy, setRegBusy] = useState(false);

  async function handleLoginSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoginError(null);
    if (!loginEmail.includes("@")) return setLoginError("Valid email required.");
    if (loginPassword.length < 8) return setLoginError("Password must be at least 8 characters.");

    setLoginBusy(true);
    try {
      await signInAsync(loginEmail, loginPassword);
      navigate({ to: "/" });
    } catch (err: unknown) {
      setLoginError(err instanceof Error ? err.message : "Sign in failed.");
    } finally {
      setLoginBusy(false);
    }
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
      setRegError(err instanceof Error ? err.message : "Registration failed.");
    } finally {
      setRegBusy(false);
    }
  }

  return (
    <main className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border bg-white/85 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <Link to="/" className="flex items-center gap-3">
            <span className="flex size-10 items-center justify-center rounded-2xl bg-primary text-sm font-bold text-primary-foreground">
              W
            </span>
            <span>
              <span className="block text-[15px] font-semibold tracking-tight">Whitfield Ops</span>
              <span className="block text-xs text-muted-foreground">Fulfillment operations</span>
            </span>
          </Link>
          <nav className="hidden items-center gap-6 text-sm font-medium text-muted-foreground md:flex">
            <a href="#operations" className="hover:text-primary">
              Operations
            </a>
            <a href="#controls" className="hover:text-primary">
              Controls
            </a>
            <a href="#access" className="hover:text-primary">
              Access
            </a>
          </nav>
          <Link to="/login">
            <Button variant="outline">Staff sign in</Button>
          </Link>
        </div>
      </header>

      <section className="mx-auto grid max-w-7xl gap-8 px-4 py-10 sm:px-6 lg:grid-cols-[1.05fr_0.95fr] lg:px-8 lg:py-16">
        <div className="flex flex-col justify-center">
          <div className="inline-flex w-fit items-center gap-2 rounded-full bg-primary-tint px-3 py-1.5 text-xs font-semibold text-primary">
            <ClipboardCheck className="size-4" />
            Excel replacement for live warehouses
          </div>
          <h1 className="mt-6 max-w-4xl text-4xl font-semibold tracking-tight sm:text-5xl lg:text-6xl">
            A controlled warehouse console for receipts, stock, orders, and exceptions.
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-muted-foreground">
            Whitfield Ops is built for Dan Whitfield's Reno and Columbus fulfillment sites:
            duplicate-safe receiving, damaged-stock separation, append-only inventory movements,
            role-scoped access, and manager-visible reconciliation.
          </p>

          <div className="mt-8 grid gap-3 sm:grid-cols-2">
            {FACILITIES.map((facility) => (
              <div key={facility.code} className="card-surface p-4">
                <div className="flex items-center gap-3">
                  <span className="rounded-full bg-primary px-3 py-1 font-mono text-sm font-semibold text-white">
                    {facility.code}
                  </span>
                  <span className="font-semibold">{facility.label}</span>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">{facility.note}</p>
              </div>
            ))}
          </div>

          <div className="mt-8 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => setPanel("SIGN_IN")}
              className="rounded-full bg-primary px-5 py-3 text-sm font-semibold text-white shadow-[0_8px_20px_rgba(37,99,235,0.22)] transition-colors hover:bg-primary-dark"
            >
              Open operator console
            </button>
            <button
              type="button"
              onClick={() => setPanel("SELLER")}
              className="rounded-full border border-primary/30 bg-white px-5 py-3 text-sm font-semibold text-primary transition-colors hover:bg-primary-tint"
            >
              Request seller access
            </button>
          </div>
        </div>

        <section id="access" className="card-surface p-5 sm:p-6">
          <div className="mb-4 flex rounded-full bg-muted p-1 text-sm font-semibold">
            <button
              type="button"
              onClick={() => setPanel("SIGN_IN")}
              className={`flex-1 rounded-full px-3 py-2 ${
                panel === "SIGN_IN" ? "bg-white text-primary shadow-card" : "text-muted-foreground"
              }`}
            >
              Sign in
            </button>
            <button
              type="button"
              onClick={() => setPanel("SELLER")}
              className={`flex-1 rounded-full px-3 py-2 ${
                panel === "SELLER" ? "bg-white text-primary shadow-card" : "text-muted-foreground"
              }`}
            >
              Seller request
            </button>
          </div>

          {panel === "SIGN_IN" ? (
            <form onSubmit={handleLoginSubmit} className="space-y-4">
              <PanelHeading
                icon={<Lock className="size-5" />}
                title="Secure console access"
                copy="Role permissions determine which warehouse, seller, and workflow data you can see."
              />
              {loginError ? <ErrorBox message={loginError} /> : null}
              <InputField
                label="Email"
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
              <Button type="submit" disabled={loginBusy} className="w-full">
                {loginBusy ? <Loader2 className="size-4 animate-spin" /> : null}
                Sign in to console
              </Button>
            </form>
          ) : (
            <form onSubmit={handleRegisterSubmit} className="space-y-4">
              <PanelHeading
                icon={<Store className="size-5" />}
                title="Seller onboarding request"
                copy="Seller accounts are pending until an administrator approves the tenant."
              />
              {regSubmitted ? (
                <div className="rounded-2xl border border-primary/20 bg-primary-tint p-4 text-sm text-primary">
                  <p className="flex items-center gap-2 font-semibold">
                    <Clock className="size-4" />
                    Submitted for approval
                  </p>
                  <p className="mt-1 text-muted-foreground">
                    Your account can sign in after administrator approval.
                  </p>
                </div>
              ) : null}
              {regError ? <ErrorBox message={regError} /> : null}
              <div className="grid gap-3 sm:grid-cols-2">
                <InputField label="Company" value={regCompany} onChange={setRegCompany} />
                <InputField
                  label="Seller code optional"
                  value={regCode}
                  onChange={(value) => setRegCode(value.toUpperCase())}
                  mono
                />
              </div>
              <InputField label="Full name" value={regName} onChange={setRegName} />
              <InputField
                label="Work email"
                type="email"
                value={regEmail}
                onChange={setRegEmail}
                icon={<Mail className="size-4" />}
              />
              <InputField
                label="Password"
                type="password"
                value={regPassword}
                onChange={setRegPassword}
                icon={<Lock className="size-4" />}
              />
              <Button type="submit" disabled={regBusy || regSubmitted} className="w-full">
                {regBusy ? <Loader2 className="size-4 animate-spin" /> : null}
                Submit for approval
              </Button>
            </form>
          )}
        </section>
      </section>

      <section id="operations" className="border-y border-border bg-white">
        <div className="mx-auto grid max-w-7xl gap-4 px-4 py-8 sm:grid-cols-2 sm:px-6 lg:grid-cols-4 lg:px-8">
          {CONTROL_POINTS.map((point) => {
            const Icon = point.icon;
            return (
              <article key={point.title} className="card-surface p-5">
                <Icon className="size-6 text-primary" />
                <h2 className="mt-4 text-lg font-semibold">{point.title}</h2>
                <p className="mt-2 text-sm leading-6 text-muted-foreground">{point.copy}</p>
              </article>
            );
          })}
        </div>
      </section>

      <section id="controls" className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
          <div>
            <p className="text-sm font-semibold text-primary">What the UI is optimized for</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight">
              Make risky operations visible before they become stock errors.
            </h2>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              The console emphasizes exception queues and hard stops: duplicate receipts, damaged
              goods, short picks, transfer discrepancies, expired reservations, and migration
              approvals.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {[
              { icon: Boxes, text: "Receipt completion posts append-only inventory movements." },
              { icon: Truck, text: "Shipments convert reserved stock into shipped ledger events." },
              { icon: Warehouse, text: "Managers see Reno and Columbus stock from one view." },
              { icon: CheckCircle2, text: "AI and voice helpers stay read-only or draft-only." },
            ].map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.text} className="card-surface flex gap-3 p-4">
                  <Icon className="mt-0.5 size-5 shrink-0 text-primary" />
                  <span className="text-sm font-medium leading-6 text-foreground">{item.text}</span>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <footer className="border-t border-border bg-white px-4 py-8 text-foreground sm:px-6 lg:px-8">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm font-semibold">
            Whitfield Fulfillment Warehouse Operations Platform
          </p>
          <div className="flex flex-wrap gap-2">
            {ROLES.map((role) => (
              <span
                key={role}
                className="rounded-full bg-primary-tint px-3 py-1 text-xs font-semibold text-primary"
              >
                {role}
              </span>
            ))}
          </div>
        </div>
      </footer>
    </main>
  );
}

interface PanelHeadingProps {
  copy: string;
  icon: React.ReactNode;
  title: string;
}

function PanelHeading({ copy, icon, title }: PanelHeadingProps) {
  return (
    <div className="rounded-2xl bg-primary-tint p-4">
      <div className="flex items-center gap-2 text-primary">
        {icon}
        <h2 className="font-semibold">{title}</h2>
      </div>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">{copy}</p>
    </div>
  );
}

interface InputFieldProps {
  icon?: React.ReactNode;
  label: string;
  mono?: boolean;
  onChange: (value: string) => void;
  type?: string;
  value: string;
}

function InputField({ icon, label, mono, onChange, type = "text", value }: InputFieldProps) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-foreground">{label}</span>
      <div className="relative mt-1.5">
        {icon ? (
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
            {icon}
          </span>
        ) : null}
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={`w-full rounded-full border border-input bg-white py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 ${
            icon ? "pl-9 pr-3" : "px-3"
          } ${mono ? "font-mono font-semibold uppercase" : ""}`}
        />
      </div>
    </label>
  );
}

function ErrorBox({ message }: { message: string }) {
  return (
    <div className="rounded-2xl border border-status-red/30 bg-status-red/5 px-4 py-3 text-sm text-status-red">
      {message}
    </div>
  );
}
