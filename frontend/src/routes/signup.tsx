import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowRight,
  Boxes,
  CheckCircle2,
  Clock,
  Globe2,
  Loader2,
  Lock,
  Mail,
  ShieldCheck,
  Sparkles,
  Store,
  Truck,
  User,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui-kit";
import { registerSellerPublicApi } from "@/lib/api-services";
import { useAuth } from "@/lib/auth";

export const Route = createFileRoute("/signup")({
  head: () => ({
    meta: [
      { title: "Open Seller Account | Whitfield Logistics" },
      {
        name: "description",
        content: "Apply for a multi-channel seller fulfillment account with Whitfield Logistics.",
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

    if (!name.trim()) return setError("Please enter your contact name.");
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
      setError(err instanceof Error ? err.message : "Registration request failed. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen bg-background px-4 py-10 text-foreground sm:px-6">
      <div className="mx-auto max-w-6xl">
        <Link to="/" className="inline-flex items-center gap-3">
          <span className="flex size-11 items-center justify-center rounded-2xl bg-gradient-to-tr from-primary-dark via-primary to-blue-500 text-lg font-bold text-white shadow-[0_8px_20px_rgba(37,99,235,0.28)]">
            W
          </span>
          <span>
            <span className="block text-lg font-bold tracking-tight text-foreground">
              Whitfield <span className="text-primary">Logistics</span>
            </span>
            <span className="block text-xs font-medium text-muted-foreground">
              Seller Account Onboarding
            </span>
          </span>
        </Link>

        <div className="mt-8 grid gap-8 lg:grid-cols-[0.95fr_1.05fr]">
          <section className="card-surface animate-rise p-8 sm:p-10">
            <span className="inline-flex items-center gap-2 rounded-full bg-primary-tint px-3.5 py-1.5 text-xs font-semibold text-primary">
              <Store className="size-4" />
              Direct Brand & Merchant Onboarding
            </span>

            <h1 className="mt-5 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
              Scale your fulfillment nationwide with Whitfield.
            </h1>

            <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
              Join leading e-commerce brands utilizing our Reno and Columbus distribution centers for 2-day delivery, real-time inventory synchronization, and AI logistics support.
            </p>

            <div className="mt-8 space-y-3.5">
              {[
                { title: "Bicoastal 2-Day Reach", desc: "Strategic hubs covering 98% of the US population" },
                { title: "Unified Stock Portal", desc: "Live multi-warehouse balances with zero spreadsheet lag" },
                { title: "Omnichannel Integrations", desc: "Ready for Shopify, Amazon FBA prep, Walmart, and EDI" },
                { title: "Dedicated SLA Guarantee", desc: "99.98% pick accuracy and sub-12h dock-to-stock intake" },
              ].map((item) => (
                <div key={item.title} className="flex items-start gap-3 rounded-2xl bg-primary-tint/60 p-3.5">
                  <CheckCircle2 className="size-5 shrink-0 text-primary mt-0.5" />
                  <div>
                    <p className="text-xs font-bold text-foreground">{item.title}</p>
                    <p className="text-xs text-muted-foreground">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="card-surface animate-rise p-8 sm:p-10">
            {submitted ? (
              <div className="py-6 text-center">
                <div className="mx-auto flex size-16 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
                  <CheckCircle2 className="size-8" />
                </div>
                <h2 className="mt-4 text-2xl font-bold tracking-tight text-foreground">
                  Application Submitted Successfully
                </h2>
                <p className="mx-auto mt-3 max-w-md text-sm leading-relaxed text-muted-foreground">
                  Your seller account request for <strong>{companyName}</strong> has been received. Our onboarding specialist will verify your catalog setup and activate your account.
                </p>
                <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:justify-center">
                  <Link to="/login">
                    <Button variant="outline" className="w-full sm:w-auto">
                      Go to Sign In
                    </Button>
                  </Link>
                  <Link to="/">
                    <Button className="w-full sm:w-auto">
                      Explore Public Site <ArrowRight className="size-4" />
                    </Button>
                  </Link>
                </div>
              </div>
            ) : (
              <>
                <p className="text-xs font-bold uppercase tracking-wider text-primary">
                  Seller Portal Registration
                </p>
                <h2 className="mt-1 text-2xl font-bold tracking-tight">Open a Merchant Account</h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  Complete the profile details below to initiate your tenant setup.
                </p>

                {error && (
                  <div className="mt-5 rounded-xl border border-status-red/30 bg-status-red/5 px-4 py-3 text-xs font-semibold text-status-red">
                    {error}
                  </div>
                )}

                <form onSubmit={handleSubmit} className="mt-6 space-y-4">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <TextField
                      label="Company / Brand Name"
                      value={companyName}
                      onChange={setCompanyName}
                      placeholder="Apex Apparel LLC"
                      required
                    />
                    <TextField
                      label="Seller Code (Optional)"
                      value={sellerCode}
                      onChange={(value) => setSellerCode(value.toUpperCase())}
                      placeholder="APEX"
                      mono
                    />
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <TextField
                      icon={<User className="size-4" />}
                      label="Primary Contact Name"
                      value={name}
                      onChange={setName}
                      placeholder="Alex Whitfield"
                      required
                    />
                    <TextField
                      icon={<Mail className="size-4" />}
                      label="Work Email Address"
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
                      label="Account Password"
                      type="password"
                      value={password}
                      onChange={setPassword}
                      placeholder="Minimum 6 characters"
                      required
                    />
                    <TextField
                      icon={<Lock className="size-4" />}
                      label="Confirm Password"
                      type="password"
                      value={confirmPassword}
                      onChange={setConfirmPassword}
                      placeholder="Re-enter password"
                      required
                    />
                  </div>

                  <Button type="submit" disabled={busy} className="w-full py-3.5 text-sm font-bold mt-2">
                    {busy ? <Loader2 className="size-5 animate-spin" /> : null}
                    Submit Merchant Application <ArrowRight className="size-4" />
                  </Button>
                </form>
              </>
            )}

            <div className="mt-6 border-t border-border pt-5 text-center text-xs text-muted-foreground">
              Already have an account?{" "}
              <Link to="/login" className="font-bold text-primary hover:underline">
                Sign In to Client Portal
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
      <span className="text-xs font-semibold uppercase tracking-wider text-foreground">{label}</span>
      <div className="relative mt-1.5">
        {icon ? (
          <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground">
            {icon}
          </span>
        ) : null}
        <input
          type={type}
          required={required}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className={`w-full rounded-xl border border-input bg-white py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 transition-all ${
            icon ? "pl-10 pr-3.5" : "px-3.5"
          } ${mono ? "font-mono font-bold uppercase" : ""}`}
        />
      </div>
    </label>
  );
}
