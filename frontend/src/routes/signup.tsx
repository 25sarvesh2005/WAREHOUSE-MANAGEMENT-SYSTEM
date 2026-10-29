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
              Seller Access Request
            </span>
          </span>
        </Link>

        <div className="mt-8 grid items-start gap-7 lg:grid-cols-[1fr_1.05fr]">
          {/* Form section - First in DOM for mobile accessibility */}
          <section className="card-surface animate-rise p-6 sm:p-8 lg:order-2 rounded-xl">
            {submitted ? (
              <div className="py-6 text-center">
                <div className="mx-auto flex size-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
                  <CheckCircle2 className="size-6" />
                </div>
                <h1 className="mt-4 text-xl font-bold tracking-tight text-slate-900">
                  Request submitted
                </h1>
                <p className="mx-auto mt-2 max-w-md text-xs leading-relaxed text-slate-500">
                  Your seller access request for <strong>{companyName}</strong> was received and is
                  pending administrator review. You can sign in after the account is approved.
                </p>
                <div className="mt-6 flex flex-col gap-2.5 sm:flex-row sm:justify-center">
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
                <p className="text-[11px] font-semibold uppercase tracking-wider text-primary">
                  Seller Access Request
                </p>
                <h1 className="mt-1 text-2xl font-bold tracking-tight text-slate-900">
                  Create seller access request
                </h1>
                <p className="mt-1 text-xs text-slate-500">
                  Complete the details below to submit your request for administrator review. Submission does not grant immediate access.
                </p>

                {error ? (
                  <div
                    id="signup-error-message"
                    role="alert"
                    aria-live="assertive"
                    className="mt-4 rounded-lg border border-rose-200 bg-rose-50/80 px-3.5 py-2.5 text-xs font-semibold text-rose-700"
                  >
                    {error}
                  </div>
                ) : null}

                <form
                  id="signup-form"
                  data-hydrated={mounted ? "true" : "false"}
                  onSubmit={handleSubmit}
                  noValidate
                  className="mt-5 space-y-3.5"
                >
                  <div className="grid gap-3.5 sm:grid-cols-2">
                    <div>
                      <label
                        htmlFor="signup-company-name"
                        className="block text-xs font-semibold text-slate-700 uppercase tracking-wider"
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
                          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-xs outline-none placeholder:text-slate-400 transition-colors focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:opacity-60"
                        />
                      </div>
                    </div>

                    <div>
                      <label
                        htmlFor="signup-seller-code"
                        className="block text-xs font-semibold text-slate-700 uppercase tracking-wider"
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
                          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 font-mono text-sm font-semibold uppercase text-slate-900 shadow-xs outline-none placeholder:font-sans placeholder:font-normal placeholder:text-slate-400 transition-colors focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:opacity-60"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="grid gap-3.5 sm:grid-cols-2">
                    <div>
                      <label
                        htmlFor="signup-contact-name"
                        className="block text-xs font-semibold text-slate-700 uppercase tracking-wider"
                      >
                        Primary Contact Name
                      </label>
                      <div className="relative mt-1.5">
                        <User className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
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
                          className="w-full rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-3.5 text-sm text-slate-900 shadow-xs outline-none placeholder:text-slate-400 transition-colors focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:opacity-60"
                        />
                      </div>
                    </div>

                    <div>
                      <label
                        htmlFor="signup-email"
                        className="block text-xs font-semibold text-slate-700 uppercase tracking-wider"
                      >
                        Work Email Address
                      </label>
                      <div className="relative mt-1.5">
                        <Mail className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
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
                          className="w-full rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-3.5 text-sm text-slate-900 shadow-xs outline-none placeholder:text-slate-400 transition-colors focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:opacity-60"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="grid gap-3.5 sm:grid-cols-2">
                    <div>
                      <label
                        htmlFor="signup-password"
                        className="block text-xs font-semibold text-slate-700 uppercase tracking-wider"
                      >
                        Account Password
                      </label>
                      <div className="relative mt-1.5">
                        <Lock className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
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
                          className="w-full rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-3.5 text-sm text-slate-900 shadow-xs outline-none placeholder:text-slate-400 transition-colors focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:opacity-60"
                        />
                      </div>
                      <p className="mt-1 text-[11px] text-slate-400">
                        Use at least 8 characters.
                      </p>
                    </div>

                    <div>
                      <label
                        htmlFor="signup-confirm-password"
                        className="block text-xs font-semibold text-slate-700 uppercase tracking-wider"
                      >
                        Confirm Password
                      </label>
                      <div className="relative mt-1.5">
                        <Lock className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-400" />
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
                          className="w-full rounded-lg border border-slate-300 bg-white py-2 pl-9 pr-3.5 text-sm text-slate-900 shadow-xs outline-none placeholder:text-slate-400 transition-colors focus:border-primary focus:ring-2 focus:ring-primary/15 disabled:opacity-60"
                        />
                      </div>
                    </div>
                  </div>

                  <Button
                    id="signup-submit-button"
                    type="submit"
                    disabled={busy}
                    className="w-full py-2.5 text-sm font-semibold mt-1"
                  >
                    {busy ? <Loader2 className="size-4 animate-spin" /> : null}
                    Submit access request
                  </Button>
                </form>
              </>
            )}

            <div className="mt-5 border-t border-slate-100 pt-4 text-center text-xs text-slate-500">
              Already approved?{" "}
              <Link to="/login" className="font-semibold text-primary hover:underline">
                Sign in to the portal
              </Link>
            </div>
          </section>

          {/* Context section - Second in DOM, lg:order-1 on desktop */}
          <section className="card-surface animate-rise p-7 sm:p-8 lg:order-1 rounded-xl">
            <span className="inline-flex items-center gap-1.5 rounded-md bg-blue-50 px-2.5 py-1 text-xs font-semibold text-primary border border-blue-200/80">
              <ShieldCheck className="size-3.5" />
              Seller account request
            </span>

            <h2 className="mt-4 text-xl font-bold tracking-tight text-slate-900 sm:text-2xl">
              Request access to Whitfield fulfillment.
            </h2>

            <p className="mt-3 text-xs leading-relaxed text-slate-500">
              Submit your organization and primary-contact details for administrator review.
            </p>

            <div className="mt-6 space-y-3">
              <div className="rounded-lg bg-slate-50 p-3.5 border border-slate-100">
                <p className="text-xs font-bold text-slate-800">Review required</p>
                <p className="mt-0.5 text-xs text-slate-500">
                  Seller access remains pending until an administrator approves the account.
                </p>
              </div>
              <div className="rounded-lg bg-slate-50 p-3.5 border border-slate-100">
                <p className="text-xs font-bold text-slate-800">Tenant-scoped access</p>
                <p className="mt-0.5 text-xs text-slate-500">
                  An approved seller account is limited to its assigned seller data.
                </p>
              </div>
              <div className="rounded-lg bg-slate-50 p-3.5 border border-slate-100">
                <p className="text-xs font-bold text-slate-800">Operational visibility</p>
                <p className="mt-0.5 text-xs text-slate-500">
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
