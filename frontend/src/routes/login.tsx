import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { Eye, EyeOff, Loader2, Lock, Mail, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui-kit";
import { signInAsync, useAuth } from "@/lib/auth";
import { clearSession } from "@/lib/session";

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [
      { title: "Sign In | Whitfield Ops" },
      {
        name: "description",
        content: "Sign in to the Whitfield Fulfillment warehouse operations console.",
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

  useEffect(() => {
    if (ready && user) navigate({ to: "/" });
  }, [ready, user, navigate]);

  async function submit(e?: React.FormEvent | React.MouseEvent) {
    if (e) e.preventDefault();
    setError(null);
    if (!email.includes("@")) return setError("Enter a valid email address.");
    if (password.length < 8) return setError("Password must be at least 8 characters.");
    setBusy(true);
    try {
      await signInAsync(email, password);
      navigate({ to: "/" });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Sign in failed.");
    } finally {
      setBusy(false);
    }
  }

  function resetLocalSession(): void {
    clearSession();
    setError(null);
  }

  return (
    <main className="min-h-screen bg-background px-4 py-10 text-foreground">
      <div className="mx-auto grid min-h-[calc(100vh-5rem)] max-w-6xl items-center gap-8 lg:grid-cols-[1fr_0.8fr]">
        <section className="animate-rise">
          <Link to="/" className="inline-flex items-center gap-2.5">
            <span className="flex size-10 items-center justify-center rounded-2xl bg-primary text-sm font-bold text-primary-foreground">
              W
            </span>
            <span className="text-[15px] font-semibold tracking-tight">Whitfield Ops</span>
          </Link>

          <div className="mt-12 max-w-2xl rounded-[2rem] border border-border bg-white p-8 shadow-card">
            <span className="inline-flex items-center gap-2 rounded-full bg-primary-tint px-3 py-1.5 text-xs font-semibold text-primary">
              <Search className="size-4" />
              Warehouse operations access
            </span>
            <h1 className="mt-5 text-4xl font-semibold tracking-tight md:text-5xl">
              Clean control for receipts, inventory, orders, and exceptions.
            </h1>
            <p className="mt-4 max-w-xl text-sm leading-6 text-muted-foreground">
              Sign in to the role-scoped Whitfield console. The interface is white-first with blue
              operational accents, matching the modern reference style.
            </p>
            <div className="mt-6 grid gap-3 sm:grid-cols-3">
              {["Reno", "Columbus", "Ledger"].map((item) => (
                <div key={item} className="rounded-3xl bg-primary-tint px-4 py-3">
                  <p className="text-sm font-semibold text-primary">{item}</p>
                  <p className="text-xs text-muted-foreground">Ready</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="card-surface animate-rise w-full p-6 sm:p-8">
          <p className="text-sm font-semibold text-primary">Welcome back</p>
          <h2 className="mt-2 text-2xl font-semibold tracking-tight">Sign in</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Use your assigned Whitfield Ops account.
          </p>

          {error ? (
            <div
              id="login-error-message"
              className="mt-5 rounded-2xl border border-status-red/30 bg-status-red/5 px-4 py-3 text-sm text-status-red"
            >
              {error}
            </div>
          ) : null}

          <form id="login-form" onSubmit={submit} className="mt-5 space-y-4">
            <InputField
              icon={<Mail className="size-4" />}
              label="Email"
              type="email"
              value={email}
              onChange={setEmail}
            />
            <label className="block" htmlFor="login-password">
              <span className="text-sm font-medium text-foreground">Password</span>
              <div className="relative mt-1.5">
                <Lock className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <input
                  id="login-password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-full border border-input bg-white py-2.5 pl-9 pr-10 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/15"
                />
                <button
                  type="button"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  onClick={() => setShowPassword((value) => !value)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-primary"
                >
                  {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </button>
              </div>
              <span className="mt-1 block text-xs text-muted-foreground">
                Password length: {password.length}
              </span>
            </label>

            <Button
              id="login-submit-button"
              type="button"
              onClick={submit}
              disabled={busy}
              className="w-full"
            >
              {busy ? <Loader2 className="size-4 animate-spin" /> : null}
              Sign in
            </Button>
          </form>

          <div className="mt-6 space-y-3 border-t border-border pt-5 text-center text-sm text-muted-foreground">
            <p>
              Seller without an account?{" "}
              <Link to="/signup" className="font-semibold text-primary hover:underline">
                Request seller access
              </Link>
            </p>
            <button
              type="button"
              onClick={resetLocalSession}
              className="font-medium text-muted-foreground transition-colors hover:text-primary"
            >
              Session expired? Reset local session
            </button>
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
      <span className="text-sm font-medium text-foreground">{label}</span>
      <div className="relative mt-1.5">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
          {icon}
        </span>
        <input
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full rounded-full border border-input bg-white py-2.5 pl-9 pr-3 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/15"
        />
      </div>
    </label>
  );
}
