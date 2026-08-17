import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowRight,
  Boxes,
  CheckCircle2,
  Eye,
  EyeOff,
  Globe2,
  Loader2,
  Lock,
  Mail,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui-kit";
import { getApiBaseUrl, setCustomApiBaseUrl } from "@/lib/api-client";
import { signInAsync, useAuth } from "@/lib/auth";
import { clearSession } from "@/lib/session";

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [
      { title: "Client Portal Sign In | Whitfield Logistics" },
      {
        name: "description",
        content: "Sign in to the Whitfield Fulfillment client and operations portal.",
      },
    ],
  }),
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const { user, ready } = useAuth();
  const [email, setEmail] = useState("admin@whitfield.local");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showApiConfig, setShowApiConfig] = useState(false);
  const [apiUrlInput, setApiUrlInput] = useState(() => getApiBaseUrl().replace(/\/api\/v1$/, ""));

  useEffect(() => {
    if (ready && user) navigate({ to: "/", replace: true });
  }, [ready, user, navigate]);

  async function submit(e?: React.FormEvent | React.MouseEvent) {
    if (e) e.preventDefault();
    setError(null);
    if (!email.includes("@")) return setError("Enter a valid email address.");
    if (password.length < 8) return setError("Password must be at least 8 characters.");
    setBusy(true);
    try {
      await signInAsync(email, password);
      navigate({ to: "/", replace: true });
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Sign in failed. Please check your credentials.",
      );
    } finally {
      setBusy(false);
    }
  }

  function handleQuickFill(type: "ADMIN" | "MANAGER" | "RECEIVER" | "PICKER" | "SELLER") {
    if (type === "ADMIN") {
      setEmail("admin@whitfield.local");
      setPassword("");
    } else if (type === "MANAGER") {
      setEmail("manager@whitfield.local");
      setPassword("Manager123!");
    } else if (type === "RECEIVER") {
      setEmail("receiver@whitfield.local");
      setPassword("Receiver123!");
    } else if (type === "PICKER") {
      setEmail("picker@whitfield.local");
      setPassword("Picker123!");
    } else if (type === "SELLER") {
      setEmail("seller@whitfield.local");
      setPassword("Seller123!");
    }
    setError(null);
  }

  function resetLocalSession(): void {
    clearSession();
    setError(null);
  }

  return (
    <main className="min-h-screen bg-background px-4 py-10 text-foreground sm:px-6">
      <div className="mx-auto grid min-h-[calc(100vh-5rem)] max-w-6xl items-center gap-12 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="animate-rise">
          <Link to="/" className="inline-flex items-center gap-3">
            <span className="flex size-11 items-center justify-center rounded-2xl bg-gradient-to-tr from-primary-dark via-primary to-blue-500 text-lg font-bold text-white shadow-[0_8px_20px_rgba(37,99,235,0.28)]">
              W
            </span>
            <span>
              <span className="block text-lg font-bold tracking-tight text-foreground">
                Whitfield <span className="text-primary">Logistics</span>
              </span>
              <span className="block text-xs font-medium text-muted-foreground">
                Client & Operations Portal
              </span>
            </span>
          </Link>

          <div className="mt-10 rounded-[2.5rem] border border-border bg-white p-8 sm:p-10 shadow-card">
            <span className="inline-flex items-center gap-2 rounded-full bg-primary-tint px-3.5 py-1.5 text-xs font-semibold text-primary">
              <ShieldCheck className="size-4" />
              Enterprise Single Sign-On
            </span>

            <h1 className="mt-5 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Real-time inventory visibility & fulfillment command.
            </h1>

            <p className="mt-4 text-base leading-relaxed text-muted-foreground">
              Sign in to manage multi-channel orders, track dock-to-stock inbound receipts, monitor
              inter-facility inventory balances, and query the AI copilot across our Reno and
              Columbus hubs.
            </p>

            <div className="mt-8 grid gap-3 sm:grid-cols-3">
              {[
                { label: "Reno Hub (RNO)", status: "Online & Dispatching" },
                { label: "Columbus Hub (CMH)", status: "Online & Receiving" },
                { label: "Ledger Core", status: "100% Real-Time Sync" },
              ].map((item) => (
                <div
                  key={item.label}
                  className="rounded-2xl bg-muted/60 p-3.5 border border-border/60"
                >
                  <p className="text-xs font-bold text-foreground">{item.label}</p>
                  <p className="mt-0.5 text-[11px] font-semibold text-emerald-600">
                    ● {item.status}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="card-surface animate-rise w-full p-6 sm:p-10">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-primary">
                Portal Access
              </p>
              <h2 className="mt-1 text-2xl font-bold tracking-tight">Sign In</h2>
            </div>
            <span className="flex size-10 items-center justify-center rounded-2xl bg-primary-tint text-primary">
              <Lock className="size-5" />
            </span>
          </div>

          <p className="mt-2 text-sm text-muted-foreground">
            Enter your authorized Whitfield client or staff credentials.
          </p>

          {/* 1-Click Quick Login Helpers */}
          <div className="mt-5 rounded-2xl border border-primary/20 bg-primary-tint/40 p-4 text-xs">
            <p className="font-bold text-primary uppercase tracking-wider text-[10px]">
              1-Click Quick Demo Login:
            </p>
            <div className="mt-2.5 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => handleQuickFill("ADMIN")}
                className="rounded-xl bg-white px-3 py-1.5 font-bold text-foreground shadow-xs border border-border hover:bg-primary-dark hover:text-white transition-all cursor-pointer whitespace-nowrap shrink-0 text-xs"
              >
                👑 Admin
              </button>
              <button
                type="button"
                onClick={() => handleQuickFill("MANAGER")}
                className="rounded-xl bg-white px-3 py-1.5 font-bold text-foreground shadow-xs border border-border hover:bg-primary hover:text-white transition-all cursor-pointer whitespace-nowrap shrink-0 text-xs"
              >
                📊 Manager
              </button>
              <button
                type="button"
                onClick={() => handleQuickFill("RECEIVER")}
                className="rounded-xl bg-white px-3 py-1.5 font-bold text-foreground shadow-xs border border-border hover:bg-primary hover:text-white transition-all cursor-pointer whitespace-nowrap shrink-0 text-xs"
              >
                📥 Receiver
              </button>
              <button
                type="button"
                onClick={() => handleQuickFill("PICKER")}
                className="rounded-xl bg-white px-3 py-1.5 font-bold text-foreground shadow-xs border border-border hover:bg-primary hover:text-white transition-all cursor-pointer whitespace-nowrap shrink-0 text-xs"
              >
                📦 Picker
              </button>
              <button
                type="button"
                onClick={() => handleQuickFill("SELLER")}
                className="rounded-xl bg-white px-3 py-1.5 font-bold text-primary shadow-xs border border-primary/30 hover:bg-primary hover:text-white transition-all cursor-pointer whitespace-nowrap shrink-0 text-xs"
              >
                🏢 Seller
              </button>
            </div>
          </div>

          {error && (
            <div
              id="login-error-message"
              className="mt-5 rounded-xl border border-status-red/30 bg-status-red/5 px-4 py-3 text-xs font-semibold text-status-red"
            >
              {error}
            </div>
          )}

          <form id="login-form" onSubmit={submit} className="mt-6 space-y-4">
            <InputField
              icon={<Mail className="size-4" />}
              label="Work Email"
              type="email"
              value={email}
              onChange={setEmail}
            />

            <label className="block" htmlFor="login-password">
              <span className="text-xs font-semibold uppercase tracking-wider text-foreground">
                Password
              </span>
              <div className="relative mt-1.5">
                <Lock className="absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <input
                  id="login-password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-xl border border-input bg-white py-2.5 pl-10 pr-10 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 transition-all"
                />
                <button
                  type="button"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-primary"
                >
                  {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </button>
              </div>
            </label>

            <Button
              id="login-submit-button"
              type="button"
              onClick={submit}
              disabled={busy}
              className="w-full py-3 text-sm font-bold mt-2"
            >
              {busy ? <Loader2 className="size-4 animate-spin" /> : null}
              Sign In to Portal
            </Button>
          </form>

          <div className="mt-6 space-y-3 border-t border-border pt-5 text-center text-xs text-muted-foreground">
            <p>
              New brand or seller?{" "}
              <Link to="/signup" className="font-bold text-primary hover:underline">
                Open a Seller Account
              </Link>
            </p>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <button
                type="button"
                onClick={resetLocalSession}
                className="font-medium text-muted-foreground transition-colors hover:text-primary"
              >
                Reset session
              </button>
              <span>•</span>
              <button
                type="button"
                onClick={() => setShowApiConfig((v) => !v)}
                className="font-medium text-primary hover:underline"
              >
                {showApiConfig ? "Hide API Server" : "API Server Settings"}
              </button>
            </div>

            {showApiConfig && (
              <div className="mt-3 rounded-xl border border-border bg-muted/40 p-3 text-left">
                <label className="block text-[11px] font-semibold text-foreground">
                  Backend API URL (Render / Cloud):
                  <input
                    type="url"
                    value={apiUrlInput}
                    onChange={(e) => setApiUrlInput(e.target.value)}
                    placeholder="https://your-service.onrender.com"
                    className="mt-1 w-full rounded-lg border border-input bg-white px-2.5 py-1.5 font-mono text-xs outline-none focus:border-primary"
                  />
                </label>
                <div className="mt-2 flex items-center justify-between gap-2">
                  <span className="text-[10px] text-muted-foreground">
                    Active: <code className="font-mono text-foreground">{getApiBaseUrl()}</code>
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      setCustomApiBaseUrl(apiUrlInput);
                      setError(null);
                      alert(`API Backend updated to: ${getApiBaseUrl()}`);
                    }}
                    className="rounded-md bg-primary px-2.5 py-1 text-xs font-semibold text-white hover:bg-primary-dark"
                  >
                    Save & Reconnect
                  </button>
                </div>
              </div>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}

function InputField({
  icon,
  label,
  onChange,
  type,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  onChange: (value: string) => void;
  type: string;
  value: string;
}) {
  return (
    <label className="block">
      <span className="text-xs font-semibold uppercase tracking-wider text-foreground">
        {label}
      </span>
      <div className="relative mt-1.5">
        <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground">
          {icon}
        </span>
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full rounded-xl border border-input bg-white py-2.5 pl-10 pr-3.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 transition-all"
        />
      </div>
    </label>
  );
}
