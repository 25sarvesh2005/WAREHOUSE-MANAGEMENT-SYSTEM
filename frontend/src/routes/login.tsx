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
      <div className="mx-auto max-w-5xl">
        <Link to="/login" className="inline-flex items-center gap-2.5">
          <span className="flex size-9 items-center justify-center rounded-lg bg-primary text-sm font-bold text-white shadow-xs">
            W
          </span>
          <span>
            <span className="block text-base font-bold tracking-tight text-slate-900">
              Whitfield <span className="text-primary font-bold">Logistics</span>
            </span>
            <span className="block text-[11px] font-medium text-slate-500">
              Client & Operations Portal
            </span>
          </span>
        </Link>

        <div className="mt-8 grid items-start gap-7 lg:grid-cols-[1fr_1.1fr]">
          {/* Form Section - First in DOM for mobile accessibility */}
          <section className="card-surface animate-rise w-full p-6 sm:p-8 lg:order-2 rounded-xl">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-primary">
                  Portal Access
                </p>
                <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
                  Sign in to Whitfield WMS
                </h1>
              </div>
              <span className="flex size-9 items-center justify-center rounded-lg bg-blue-50 text-primary border border-blue-200/80">
                <Lock className="size-4" />
              </span>
            </div>

            <p className="mt-1.5 text-xs text-slate-500">
              Use your assigned work email and password.
            </p>

            {error ? (
              <div
                id="login-error-message"
                role="alert"
                aria-live="assertive"
                className="mt-4 rounded-lg border border-rose-200 bg-rose-50/80 px-3.5 py-2.5 text-xs font-semibold text-rose-700"
              >
                {error}
              </div>
            ) : null}

            <form
              id="login-form"
              data-hydrated={mounted ? "true" : "false"}
              onSubmit={handleSubmit}
              noValidate
              className="mt-5 space-y-4"
            >
              <div>
                <label
                  htmlFor="login-email"
                  className="block text-xs font-semibold text-slate-700 uppercase tracking-wider"
                >
                  Work Email
                </label>
                <div className="relative mt-1.5">
                  <Mail className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
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
                    className="w-full rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-3.5 text-sm text-slate-900 shadow-xs outline-none placeholder:text-slate-400 transition-colors focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:opacity-60"
                  />
                </div>
              </div>

              <div>
                <label
                  htmlFor="login-password"
                  className="block text-xs font-semibold text-slate-700 uppercase tracking-wider"
                >
                  Password
                </label>
                <div className="relative mt-1.5">
                  <Lock className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
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
                    className="w-full rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-11 text-sm text-slate-900 shadow-xs outline-none placeholder:text-slate-400 transition-colors focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:opacity-60"
                  />
                  <button
                    type="button"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    disabled={busy}
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-1 top-1/2 -translate-y-1/2 flex size-10 min-h-[44px] min-w-[44px] items-center justify-center rounded-md text-slate-400 transition-colors hover:text-slate-700 disabled:pointer-events-none disabled:opacity-50 cursor-pointer"
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
                className="w-full py-2.5 text-sm font-semibold mt-1"
              >
                {busy ? <Loader2 className="size-4 animate-spin" /> : null}
                Sign In to Portal
              </Button>
            </form>

            <div className="mt-5 border-t border-slate-100 pt-4 text-center text-xs text-slate-500">
              <p>
                New brand or seller?{" "}
                <Link to="/signup" className="font-semibold text-primary hover:underline">
                  Open a Seller Account
                </Link>
              </p>
            </div>
          </section>

          {/* Context Section - Second in DOM, lg:order-1 on desktop */}
          <section className="animate-rise lg:order-1">
            <div className="rounded-xl border border-slate-200 bg-white p-7 sm:p-8 shadow-xs">
              <span className="inline-flex items-center gap-1.5 rounded-md bg-blue-50 px-2.5 py-1 text-xs font-semibold text-primary border border-blue-200/80">
                <ShieldCheck className="size-3.5" />
                Secure portal access
              </span>

              <h2 className="mt-4 text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">
                Warehouse work starts with the right access.
              </h2>

              <p className="mt-3 text-xs leading-relaxed text-slate-500">
                Use your assigned account to open the inventory and fulfillment workflows permitted for your role.
              </p>

              <div className="mt-6 space-y-3">
                <div className="rounded-lg bg-slate-50 p-3.5 border border-slate-100">
                  <p className="text-xs font-bold text-slate-800">Role-based access</p>
                  <p className="mt-0.5 text-xs text-slate-500">
                    Your navigation and actions follow your assigned role.
                  </p>
                </div>
                <div className="rounded-lg bg-slate-50 p-3.5 border border-slate-100">
                  <p className="text-xs font-bold text-slate-800">Operational records</p>
                  <p className="mt-0.5 text-xs text-slate-500">
                    Inventory and workflow data comes from the connected WMS API.
                  </p>
                </div>
                <div className="rounded-lg bg-slate-50 p-3.5 border border-slate-100">
                  <p className="text-xs font-bold text-slate-800">Session security</p>
                  <p className="mt-0.5 text-xs text-slate-500">
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
