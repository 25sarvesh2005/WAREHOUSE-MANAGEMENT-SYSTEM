import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { ArrowRight, CheckCircle2, Clock, Loader2, Lock, Mail, Store, User } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui-kit";
import { registerSellerPublicApi } from "@/lib/api-services";
import { useAuth } from "@/lib/auth";

export const Route = createFileRoute("/signup")({
  head: () => ({
    meta: [
      { title: "Seller Registration | Whitfield Ops" },
      {
        name: "description",
        content: "Request a seller tenant account for Whitfield Fulfillment.",
      },
    ],
  }),
  component: SignupPage,
});

function SignupPage() {
  const navigate = useNavigate();
  const { user: currentUser, ready } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [sellerCode, setSellerCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (ready && currentUser) navigate({ to: "/" });
  }, [ready, currentUser, navigate]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!name.trim()) return setError("Please enter your full name.");
    if (!email.includes("@")) return setError("Please enter a valid work email address.");
    if (!companyName.trim()) return setError("Company or brand name is required.");
    if (password.length < 6) return setError("Password must be at least 6 characters.");
    if (password !== confirmPassword) return setError("Passwords do not match.");

    setBusy(true);
    try {
      await registerSellerPublicApi({
        name,
        email,
        password,
        company_name: companyName,
        ...(sellerCode ? { seller_code: sellerCode } : {}),
      });
      setSubmitted(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen bg-background px-4 py-10 text-foreground sm:px-6">
      <div className="mx-auto max-w-5xl">
        <Link to="/" className="inline-flex items-center gap-2.5">
          <span className="flex size-10 items-center justify-center rounded-2xl bg-primary text-sm font-bold text-primary-foreground">
            W
          </span>
          <span className="text-[15px] font-semibold tracking-tight">Whitfield Ops</span>
        </Link>

        <div className="mt-8 grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <section className="card-surface animate-rise p-7">
            <span className="inline-flex items-center gap-2 rounded-full bg-primary-tint px-3 py-1.5 text-xs font-semibold text-primary">
              <Store className="size-4" />
              Seller onboarding
            </span>
            <h1 className="mt-5 text-3xl font-semibold tracking-tight md:text-4xl">
              Request access to the Whitfield seller portal.
            </h1>
            <p className="mt-4 text-sm leading-6 text-muted-foreground">
              Seller accounts remain pending until an administrator approves the tenant. Warehouse
              staff are created inside the admin console, not through this public form.
            </p>
            <div className="mt-6 space-y-3">
              {[
                "White-first modern interface",
                "Blue accent workflow cues",
                "Seller-scoped inventory access",
                "Administrator approval required",
              ].map((item) => (
                <div key={item} className="flex items-center gap-3 rounded-3xl bg-primary-tint p-3">
                  <CheckCircle2 className="size-5 shrink-0 text-primary" />
                  <span className="text-sm font-medium text-foreground">{item}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="card-surface animate-rise p-6 sm:p-8">
            {submitted ? (
              <div className="py-4 text-center">
                <div className="mx-auto flex size-16 items-center justify-center rounded-full bg-primary-tint text-primary">
                  <Clock className="size-8" />
                </div>
                <h2 className="mt-4 text-2xl font-semibold tracking-tight">
                  Registration submitted
                </h2>
                <p className="mx-auto mt-3 max-w-md text-sm leading-6 text-muted-foreground">
                  Your request for <strong>{companyName}</strong> was recorded. You can sign in
                  after administrator approval.
                </p>
                <div className="mt-6 flex flex-col gap-2.5 sm:flex-row sm:justify-center">
                  <Link to="/login">
                    <Button variant="outline" className="w-full sm:w-auto">
                      Back to sign in
                    </Button>
                  </Link>
                  <Link to="/">
                    <Button className="w-full sm:w-auto">
                      Return home <ArrowRight className="size-4" />
                    </Button>
                  </Link>
                </div>
              </div>
            ) : (
              <>
                <p className="text-sm font-semibold text-primary">Seller access request</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-tight">
                  Register seller tenant
                </h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Fill this once. Approval happens inside Whitfield admin.
                </p>

                {error ? (
                  <div className="mt-5 rounded-2xl border border-status-red/30 bg-status-red/5 px-4 py-3 text-sm text-status-red">
                    {error}
                  </div>
                ) : null}

                <form onSubmit={handleSubmit} className="mt-6 space-y-4">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <TextField
                      label="Company"
                      value={companyName}
                      onChange={setCompanyName}
                      placeholder="Apex Apparel LLC"
                      required
                    />
                    <TextField
                      label="Seller code"
                      value={sellerCode}
                      onChange={(value) => setSellerCode(value.toUpperCase())}
                      placeholder="Optional"
                      mono
                    />
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <TextField
                      icon={<User className="size-4" />}
                      label="Full name"
                      value={name}
                      onChange={setName}
                      placeholder="Alex Whitfield"
                      required
                    />
                    <TextField
                      icon={<Mail className="size-4" />}
                      label="Work email"
                      type="email"
                      value={email}
                      onChange={setEmail}
                      placeholder="alex@company.com"
                      required
                    />
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <TextField
                      icon={<Lock className="size-4" />}
                      label="Password"
                      type="password"
                      value={password}
                      onChange={setPassword}
                      placeholder="Minimum 6 characters"
                      required
                    />
                    <TextField
                      icon={<Lock className="size-4" />}
                      label="Confirm"
                      type="password"
                      value={confirmPassword}
                      onChange={setConfirmPassword}
                      placeholder="Repeat password"
                      required
                    />
                  </div>

                  <Button type="submit" disabled={busy} className="w-full">
                    {busy ? <Loader2 className="size-4 animate-spin" /> : null}
                    Submit for approval <ArrowRight className="size-4" />
                  </Button>
                </form>
              </>
            )}

            <div className="mt-6 border-t border-border pt-5 text-center text-sm text-muted-foreground">
              Already approved?{" "}
              <Link to="/login" className="font-semibold text-primary hover:underline">
                Sign in
              </Link>
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}

interface TextFieldProps {
  icon?: React.ReactNode;
  label: string;
  mono?: boolean;
  onChange: (value: string) => void;
  placeholder: string;
  required?: boolean;
  type?: string;
  value: string;
}

function TextField({
  icon,
  label,
  mono,
  onChange,
  placeholder,
  required,
  type = "text",
  value,
}: TextFieldProps) {
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
          required={required}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className={`w-full rounded-full border border-input bg-white py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 ${
            icon ? "pl-9 pr-3" : "px-3"
          } ${mono ? "font-mono font-semibold uppercase" : ""}`}
        />
      </div>
    </label>
  );
}
