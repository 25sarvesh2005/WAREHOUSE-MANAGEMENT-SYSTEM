import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import {
  ArrowRight,
  CheckCircle2,
  Loader2,
  Lock,
  Mail,
  ShieldCheck,
  User,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui-kit";
import { registerSellerPublicApi } from "@/lib/api-services";
import { useAuth } from "@/lib/auth";

export const Route = createFileRoute("/signup")({
  head: () => ({
    meta: [
      { title: "Request Seller Access | Whitfield Logistics" },
      {
        name: "description",
        content: "Request seller access to the Whitfield fulfillment portal.",
      },
    ],
  }),
  component: SignupPage,
});

type SignupField = "company" | "name" | "email" | "password" | "confirmPassword";

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
  const [invalidField, setInvalidField] = useState<SignupField | null>(null);
  const [submitted, setSubmitted] = useState(false);
  const [busy, setBusy] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (ready && currentUser) navigate({ to: "/" });
  }, [ready, currentUser, navigate]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (busy) return;
    setError(null);
    setInvalidField(null);

    if (!companyName.trim()) {
      setError("Company or brand name is required.");
      setInvalidField("company");
      return;
    }
    if (!name.trim()) {
      setError("Please enter your contact name.");
      setInvalidField("name");
      return;
    }
    if (!email.includes("@")) {
      setError("Please enter a valid work email address.");
      setInvalidField("email");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      setInvalidField("password");
      return;
    }
    if (password.length > 128) {
      setError("Password cannot exceed 128 characters.");
      setInvalidField("password");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      setInvalidField("confirmPassword");
      return;
    }

    setBusy(true);
    try {
      await registerSellerPublicApi({
        name: name.trim(),
        email: email.trim(),
        password,
        company_name: companyName.trim(),
        ...(sellerCode.trim() ? { seller_code: sellerCode.trim().toUpperCase() } : {}),
      });
      setSubmitted(true);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Registration request failed. Please try again.",
      );
      setInvalidField(null);
    } finally {
      setBusy(false);
    }
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
              Seller Access Request
            </span>
          </span>
        </Link>

        <div className="mt-8 grid items-start gap-8 lg:grid-cols-[1fr_1.05fr]">
          {/* Form section - First in DOM for mobile accessibility */}
          <section className="card-surface animate-rise p-6 sm:p-10 lg:order-2">
            {submitted ? (
              <div className="py-6 text-center">
                <div className="mx-auto flex size-16 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
                  <CheckCircle2 className="size-8" />
                </div>
                <h1 className="mt-4 text-2xl font-bold tracking-tight text-foreground">
                  Request submitted
                </h1>
                <p className="mx-auto mt-3 max-w-md text-sm leading-relaxed text-muted-foreground">
                  Your seller access request for <strong>{companyName}</strong> was received and is
                  pending administrator review. You can sign in after the account is approved.
                </p>
                <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:justify-center">
                  <Link to="/login">
                    <Button variant="outline" className="w-full sm:w-auto">
                      Go to sign in
                    </Button>
                  </Link>
                  <Link to="/login">
                    <Button className="w-full sm:w-auto">
                      Return to sign in <ArrowRight className="size-4" />
                    </Button>
                  </Link>
                </div>
              </div>
            ) : (
              <>
                <p className="text-xs font-bold uppercase tracking-wider text-primary">
                  Seller Access Request
                </p>
                <h1 className="mt-1 text-2xl font-bold tracking-tight text-foreground">
                  Create seller access request
                </h1>
                <p className="mt-1 text-xs text-muted-foreground">
                  Complete the details below to submit your request for administrator review. Submission does not grant immediate access.
                </p>

                {error ? (
                  <div
                    id="signup-error-message"
                    role="alert"
                    aria-live="assertive"
                    className="mt-5 rounded-xl border border-status-red/30 bg-status-red/5 px-4 py-3 text-xs font-semibold text-status-red"
                  >
                    {error}
                  </div>
                ) : null}

                <form
                  id="signup-form"
                  data-hydrated={mounted ? "true" : "false"}
                  onSubmit={handleSubmit}
                  noValidate
                  className="mt-6 space-y-4"
                >
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <label
                        htmlFor="signup-company-name"
                        className="block text-xs font-semibold uppercase tracking-wider text-foreground"
                      >
                        Company / Brand Name
                      </label>
                      <div className="relative mt-1.5">
                        <input
                          id="signup-company-name"
                          name="company_name"
                          type="text"
                          autoComplete="organization"
                          required
                          disabled={busy}
                          value={companyName}
                          onChange={(e) => {
                            setCompanyName(e.target.value);
                            if (invalidField === "company") {
                              setInvalidField(null);
                            }
                          }}
                          aria-describedby={invalidField === "company" ? "signup-error-message" : undefined}
                          aria-invalid={invalidField === "company"}
                          placeholder="Apex Apparel LLC"
                          className="w-full rounded-xl border border-input bg-white px-3.5 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 transition-all disabled:opacity-60"
                        />
                      </div>
                    </div>

                    <div>
                      <label
                        htmlFor="signup-seller-code"
                        className="block text-xs font-semibold uppercase tracking-wider text-foreground"
                      >
                        Seller Code (Optional)
                      </label>
                      <div className="relative mt-1.5">
                        <input
                          id="signup-seller-code"
                          name="seller_code"
                          type="text"
                          autoComplete="off"
                          disabled={busy}
                          value={sellerCode}
                          onChange={(e) => setSellerCode(e.target.value.toUpperCase())}
                          aria-invalid={false}
                          placeholder="APEX"
                          className="w-full rounded-xl border border-input bg-white px-3.5 py-2.5 font-mono text-sm font-bold uppercase outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 transition-all disabled:opacity-60"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <label
                        htmlFor="signup-contact-name"
                        className="block text-xs font-semibold uppercase tracking-wider text-foreground"
                      >
                        Primary Contact Name
                      </label>
                      <div className="relative mt-1.5">
                        <User className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                        <input
                          id="signup-contact-name"
                          name="name"
                          type="text"
                          autoComplete="name"
                          required
                          disabled={busy}
                          value={name}
                          onChange={(e) => {
                            setName(e.target.value);
                            if (invalidField === "name") {
                              setInvalidField(null);
                            }
                          }}
                          aria-describedby={invalidField === "name" ? "signup-error-message" : undefined}
                          aria-invalid={invalidField === "name"}
                          placeholder="Alex Whitfield"
                          className="w-full rounded-xl border border-input bg-white py-2.5 pl-10 pr-3.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 transition-all disabled:opacity-60"
                        />
                      </div>
                    </div>

                    <div>
                      <label
                        htmlFor="signup-email"
                        className="block text-xs font-semibold uppercase tracking-wider text-foreground"
                      >
                        Work Email Address
                      </label>
                      <div className="relative mt-1.5">
                        <Mail className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                        <input
                          id="signup-email"
                          name="email"
                          type="email"
                          autoComplete="email"
                          required
                          disabled={busy}
                          value={email}
                          onChange={(e) => {
                            setEmail(e.target.value);
                            if (invalidField === "email") {
                              setInvalidField(null);
                            }
                          }}
                          aria-describedby={invalidField === "email" ? "signup-error-message" : undefined}
                          aria-invalid={invalidField === "email"}
                          placeholder="alex@company.com"
                          className="w-full rounded-xl border border-input bg-white py-2.5 pl-10 pr-3.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 transition-all disabled:opacity-60"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <label
                        htmlFor="signup-password"
                        className="block text-xs font-semibold uppercase tracking-wider text-foreground"
                      >
                        Account Password
                      </label>
                      <div className="relative mt-1.5">
                        <Lock className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                        <input
                          id="signup-password"
                          name="password"
                          type="password"
                          autoComplete="new-password"
                          minLength={8}
                          maxLength={128}
                          required
                          disabled={busy}
                          value={password}
                          onChange={(e) => {
                            setPassword(e.target.value);
                            if (invalidField === "password") {
                              setInvalidField(null);
                            }
                          }}
                          aria-describedby={invalidField === "password" ? "signup-error-message" : undefined}
                          aria-invalid={invalidField === "password"}
                          placeholder="••••••••"
                          className="w-full rounded-xl border border-input bg-white py-2.5 pl-10 pr-3.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 transition-all disabled:opacity-60"
                        />
                      </div>
                      <p className="mt-1 text-[11px] text-muted-foreground">
                        Use at least 8 characters.
                      </p>
                    </div>

                    <div>
                      <label
                        htmlFor="signup-confirm-password"
                        className="block text-xs font-semibold uppercase tracking-wider text-foreground"
                      >
                        Confirm Password
                      </label>
                      <div className="relative mt-1.5">
                        <Lock className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                        <input
                          id="signup-confirm-password"
                          name="confirm_password"
                          type="password"
                          autoComplete="new-password"
                          minLength={8}
                          maxLength={128}
                          required
                          disabled={busy}
                          value={confirmPassword}
                          onChange={(e) => {
                            setConfirmPassword(e.target.value);
                            if (invalidField === "confirmPassword") {
                              setInvalidField(null);
                            }
                          }}
                          aria-describedby={invalidField === "confirmPassword" ? "signup-error-message" : undefined}
                          aria-invalid={invalidField === "confirmPassword"}
                          placeholder="••••••••"
                          className="w-full rounded-xl border border-input bg-white py-2.5 pl-10 pr-3.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 transition-all disabled:opacity-60"
                        />
                      </div>
                    </div>
                  </div>

                  <Button
                    id="signup-submit-button"
                    type="submit"
                    disabled={busy}
                    className="w-full py-3.5 text-sm font-bold mt-2"
                  >
                    {busy ? <Loader2 className="size-4 animate-spin" /> : null}
                    Submit access request
                  </Button>
                </form>
              </>
            )}

            <div className="mt-6 border-t border-border pt-5 text-center text-xs text-muted-foreground">
              Already approved?{" "}
              <Link to="/login" className="font-bold text-primary hover:underline">
                Sign in to the portal
              </Link>
            </div>
          </section>

          {/* Context section - Second in DOM, lg:order-1 on desktop */}
          <section className="card-surface animate-rise p-8 sm:p-10 lg:order-1">
            <span className="inline-flex items-center gap-2 rounded-full bg-primary-tint px-3.5 py-1.5 text-xs font-semibold text-primary">
              <ShieldCheck className="size-4" />
              Seller account request
            </span>

            <h2 className="mt-5 text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
              Request access to Whitfield fulfillment.
            </h2>

            <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
              Submit your organization and primary-contact details for administrator review.
            </p>

            <div className="mt-8 space-y-4">
              <div className="rounded-2xl bg-muted/60 p-4 border border-border/60">
                <p className="text-xs font-bold text-foreground">Review required</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Seller access remains pending until an administrator approves the account.
                </p>
              </div>
              <div className="rounded-2xl bg-muted/60 p-4 border border-border/60">
                <p className="text-xs font-bold text-foreground">Tenant-scoped access</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  An approved seller account is limited to its assigned seller data.
                </p>
              </div>
              <div className="rounded-2xl bg-muted/60 p-4 border border-border/60">
                <p className="text-xs font-bold text-foreground">Operational visibility</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  After activation, the account can access the workflows permitted for the seller role.
                </p>
              </div>
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}
