import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { Eye, EyeOff, Loader2, Lock, Mail, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui-kit";
import { signInAsync, useAuth } from "@/lib/auth";

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [
      { title: "Sign In | Whitfield Logistics" },
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
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [invalidField, setInvalidField] = useState<"email" | "password" | null>(null);
  const [busy, setBusy] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (ready && user) navigate({ to: "/", replace: true });
  }, [ready, user, navigate]);

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (busy) return;
    setError(null);
    setInvalidField(null);
    if (!email.includes("@")) {
      setError("Enter a valid email address.");
      setInvalidField("email");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      setInvalidField("password");
      return;
    }
    setBusy(true);
    signInAsync(email, password)
      .then(() => {
        navigate({ to: "/", replace: true });
      })
      .catch((err: unknown) => {
        setError(
          err instanceof Error ? err.message : "Sign in failed. Please check your credentials.",
        );
        setInvalidField(null);
      })
      .finally(() => {
        setBusy(false);
      });
  }

  return (
    <main className="min-h-screen bg-background px-4 py-10 text-foreground sm:px-6">
      <div className="mx-auto max-w-6xl">
        <Link to="/login" className="inline-flex items-center gap-3">
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

        <div className="mt-8 grid items-start gap-8 lg:grid-cols-[1fr_1.1fr]">
          {/* Form Section - First in DOM for mobile accessibility */}
          <section className="card-surface animate-rise w-full p-6 sm:p-10 lg:order-2">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-wider text-primary">
                  Portal Access
                </p>
                <h1 className="mt-1 text-2xl font-bold tracking-tight text-foreground">
                  Sign in to Whitfield WMS
                </h1>
              </div>
              <span className="flex size-10 items-center justify-center rounded-2xl bg-primary-tint text-primary">
                <Lock className="size-5" />
              </span>
            </div>

            <p className="mt-2 text-sm text-muted-foreground">
              Use your assigned work email and password.
            </p>

            {error ? (
              <div
                id="login-error-message"
                role="alert"
                aria-live="assertive"
                className="mt-5 rounded-xl border border-status-red/30 bg-status-red/5 px-4 py-3 text-xs font-semibold text-status-red"
              >
                {error}
              </div>
            ) : null}

            <form
              id="login-form"
              data-hydrated={mounted ? "true" : "false"}
              onSubmit={handleSubmit}
              noValidate
              className="mt-6 space-y-4"
            >
              <div>
                <label
                  htmlFor="login-email"
                  className="block text-xs font-semibold uppercase tracking-wider text-foreground"
                >
                  Work Email
                </label>
                <div className="relative mt-1.5">
                  <Mail className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <input
                    id="login-email"
                    name="email"
                    type="email"
                    autoComplete="username"
                    required
                    disabled={busy}
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value);
                      if (invalidField === "email") {
                        setInvalidField(null);
                      }
                    }}
                    aria-describedby={invalidField === "email" ? "login-error-message" : undefined}
                    aria-invalid={invalidField === "email"}
                    placeholder="name@company.com"
                    className="w-full rounded-xl border border-input bg-white py-2.5 pl-10 pr-3.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 transition-all disabled:opacity-60"
                  />
                </div>
              </div>

              <div>
                <label
                  htmlFor="login-password"
                  className="block text-xs font-semibold uppercase tracking-wider text-foreground"
                >
                  Password
                </label>
                <div className="relative mt-1.5">
                  <Lock className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <input
                    id="login-password"
                    name="password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    required
                    disabled={busy}
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value);
                      if (invalidField === "password") {
                        setInvalidField(null);
                      }
                    }}
                    aria-describedby={invalidField === "password" ? "login-error-message" : undefined}
                    aria-invalid={invalidField === "password"}
                    placeholder="••••••••"
                    className="w-full rounded-xl border border-input bg-white py-2.5 pl-10 pr-12 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 transition-all disabled:opacity-60"
                  />
                  <button
                    type="button"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    disabled={busy}
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-1.5 top-1/2 -translate-y-1/2 flex size-11 min-h-[44px] min-w-[44px] items-center justify-center rounded-xl text-muted-foreground transition-colors hover:text-primary disabled:pointer-events-none disabled:opacity-50 cursor-pointer"
                  >
                    {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                    <span className="sr-only">{showPassword ? "Hide password" : "Show password"}</span>
                  </button>
                </div>
              </div>

              <Button
                id="login-submit-button"
                type="submit"
                disabled={busy}
                className="w-full py-3 text-sm font-bold mt-2"
              >
                {busy ? <Loader2 className="size-4 animate-spin" /> : null}
                Sign In to Portal
              </Button>
            </form>

            <div className="mt-6 border-t border-border pt-5 text-center text-xs text-muted-foreground">
              <p>
                New brand or seller?{" "}
                <Link to="/signup" className="font-bold text-primary hover:underline">
                  Open a Seller Account
                </Link>
              </p>
            </div>
          </section>

          {/* Context Section - Second in DOM, lg:order-1 on desktop */}
          <section className="animate-rise lg:order-1">
            <div className="rounded-[2.5rem] border border-border bg-white p-8 sm:p-10 shadow-card">
              <span className="inline-flex items-center gap-2 rounded-full bg-primary-tint px-3.5 py-1.5 text-xs font-semibold text-primary">
                <ShieldCheck className="size-4" />
                Secure portal access
              </span>

              <h2 className="mt-5 text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
                Warehouse work starts with the right access.
              </h2>

              <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
                Use your assigned account to open the inventory and fulfillment workflows permitted for your role.
              </p>

              <div className="mt-8 space-y-4">
                <div className="rounded-2xl bg-muted/60 p-4 border border-border/60">
                  <p className="text-xs font-bold text-foreground">Role-based access</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Your navigation and actions follow your assigned role.
                  </p>
                </div>
                <div className="rounded-2xl bg-muted/60 p-4 border border-border/60">
                  <p className="text-xs font-bold text-foreground">Operational records</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Inventory and workflow data comes from the connected WMS API.
                  </p>
                </div>
                <div className="rounded-2xl bg-muted/60 p-4 border border-border/60">
                  <p className="text-xs font-bold text-foreground">Session security</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Expired or invalid sessions return you to sign in.
                  </p>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
