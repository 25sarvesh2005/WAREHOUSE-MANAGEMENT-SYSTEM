import { test, expect } from "@playwright/test";
import {
  clearAuthSession,
  injectAuthSession,
  MOCK_ADMIN_USER,
  MOCK_TOKENS,
  setupStandardApiMocks,
} from "./helpers/auth";

test.describe("Authentication Flows & Hydration", () => {
  test.beforeEach(async ({ page }) => {
    await clearAuthSession(page);
    await setupStandardApiMocks(page);
  });

  test("7.1 — Login initial state and branding without hydration error", async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto("/login");
    await expect(page.locator("#login-form")).toHaveAttribute("data-hydrated", "true");
    await expect(page.locator("#login-form")).not.toHaveAttribute("action", /^javascript:/i);
    const submitButton = page.locator("#login-submit-button");
    await expect(submitButton).toBeVisible();
    await expect(submitButton).toHaveAttribute("type", "submit");

    // Title and branding
    await expect(page).toHaveTitle(/Sign In.*Whitfield Logistics/i);
    await expect(page.locator("text=Whitfield Logistics").first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Sign in to Whitfield WMS" })).toBeVisible();

    // Inputs must start empty
    const emailInput = page.getByLabel("Work Email");
    const passwordInput = page.locator("#login-password");
    await expect(emailInput).toBeVisible();
    await expect(emailInput).toHaveValue("");
    await expect(passwordInput).toBeVisible();
    await expect(passwordInput).toHaveValue("");

    // Demo login controls must be absent
    await expect(page.getByText(/1-Click Quick Demo Login/i)).toBeHidden();
    await expect(page.getByRole("button", { name: /Quick Demo/i })).toHaveCount(0);

    // API Server Settings and Reset session must be absent
    await expect(page.getByText(/API Server Settings/i)).toBeHidden();
    await expect(page.getByText(/Reset session/i)).toBeHidden();

    // Unsupported hub/status marketing claims must be absent
    await expect(page.getByText(/Reno Hub/i)).toBeHidden();
    await expect(page.getByText(/Columbus Hub/i)).toBeHidden();
    await expect(page.getByText(/Enterprise Single Sign-On/i)).toBeHidden();

    const hydrationErrors = consoleErrors.filter(
      (msg) =>
        msg.includes("Hydration failed") ||
        msg.includes("server rendered HTML didn't match") ||
        msg.includes("hydration mismatch"),
    );
    expect(hydrationErrors).toEqual([]);
  });

  test("7.2 — Login keyboard submission with Enter key", async ({ page }) => {
    const loginRequests: Array<{ email: string; password: string }> = [];
    await page.route(/\/api\/v1\/auth\/login/, async (route) => {
      const postData = route.request().postDataJSON();
      loginRequests.push(postData);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_TOKENS),
      });
    });

    await page.goto("/login");
    await expect(page.locator("#login-form")).toHaveAttribute("data-hydrated", "true");
    const emailInput = page.getByLabel("Work Email");
    const passwordInput = page.locator("#login-password");

    await emailInput.fill("admin@whitfield.local");
    await passwordInput.fill("WhitfieldAdmin123!");
    await passwordInput.press("Enter");

    await page.waitForURL((url) => !url.pathname.includes("/login"));
    expect(loginRequests).toHaveLength(1);
    expect(loginRequests[0].email).toBe("admin@whitfield.local");
    expect(loginRequests[0].password).toBe("WhitfieldAdmin123!");
  });

  test("7.3 — Login validation, error semantics, and password toggle", async ({ page }) => {
    let loginRequestCount = 0;
    page.on("request", (req) => {
      if (req.method() === "POST" && /\/api\/v1\/auth\/login/.test(req.url())) {
        loginRequestCount++;
      }
    });

    await page.goto("/login");
    await expect(page.locator("#login-form")).toHaveAttribute("data-hydrated", "true");
    const emailInput = page.getByLabel("Work Email");
    const passwordInput = page.locator("#login-password");
    const submitButton = page.locator("#login-submit-button");

    // Invalid email validation marks email invalid but not password
    await emailInput.fill("invalid-email");
    await passwordInput.fill("validPassword123!");
    await submitButton.click();

    const errorMessage = page.locator("#login-error-message");
    await expect(errorMessage).toBeVisible();
    await expect(errorMessage).toHaveAttribute("role", "alert");
    await expect(errorMessage).toHaveAttribute("aria-live", "assertive");
    await expect(errorMessage).toContainText("Enter a valid email address.");
    await expect(emailInput).toHaveAttribute("aria-invalid", "true");
    await expect(emailInput).toHaveAttribute("aria-describedby", "login-error-message");
    await expect(passwordInput).not.toHaveAttribute("aria-invalid", "true");
    await expect(passwordInput).not.toHaveAttribute("aria-describedby", "login-error-message");
    expect(loginRequestCount).toBe(0);

    // Editing email clears its invalid state
    await emailInput.fill("admin@whitfield.local");
    await expect(emailInput).not.toHaveAttribute("aria-invalid", "true");

    // Short password validation marks password invalid but not email
    await passwordInput.fill("123");
    await submitButton.click();

    await expect(errorMessage).toBeVisible();
    await expect(errorMessage).toHaveAttribute("role", "alert");
    await expect(errorMessage).toHaveAttribute("aria-live", "assertive");
    await expect(errorMessage).toContainText("Password must be at least 8 characters.");
    await expect(passwordInput).toHaveAttribute("aria-invalid", "true");
    await expect(passwordInput).toHaveAttribute("aria-describedby", "login-error-message");
    await expect(emailInput).not.toHaveAttribute("aria-invalid", "true");
    await expect(emailInput).not.toHaveAttribute("aria-describedby", "login-error-message");
    expect(loginRequestCount).toBe(0);

    // Editing password clears its invalid state
    await passwordInput.fill("1234");
    await expect(passwordInput).not.toHaveAttribute("aria-invalid", "true");

    // Password visibility toggle accessibility & behavior
    const toggleButton = page.getByRole("button", { name: "Show password" });
    await expect(toggleButton).toBeVisible();
    await toggleButton.click();

    await expect(passwordInput).toHaveAttribute("type", "text");
    await expect(page.getByRole("button", { name: "Hide password" })).toBeVisible();
    expect(loginRequestCount).toBe(0);
  });

  test("7.4 — Seller-signup validation for required fields and password length", async ({ page }) => {
    let registrationRequestCount = 0;
    page.on("request", (req) => {
      if (req.method() === "POST" && /\/api\/v1\/auth\/register-seller/.test(req.url())) {
        registrationRequestCount++;
      }
    });

    await page.goto("/signup");
    await expect(page.locator("#signup-form")).toHaveAttribute("data-hydrated", "true");
    await expect(page.locator("#signup-form")).not.toHaveAttribute("action", /^javascript:/i);

    // Verify truthful page title and branding
    await expect(page).toHaveTitle(/Request Seller Access.*Whitfield Logistics/i);
    await expect(page.locator("text=Seller Access Request").first()).toBeVisible();

    // Verify old account/onboarding/application wording is absent
    await expect(page.getByText("Open Seller Account")).toHaveCount(0);
    await expect(page.getByText("Seller Account Onboarding")).toHaveCount(0);
    await expect(page.getByText("Seller Portal Registration")).toHaveCount(0);
    await expect(page.getByText("Submit Merchant Application")).toHaveCount(0);
    await expect(page.getByText("tenant setup")).toHaveCount(0);
    await expect(page.getByText("activate your account")).toHaveCount(0);

    // Verify all important fields are reachable by label
    const companyInput = page.getByLabel("Company / Brand Name");
    const sellerCodeInput = page.getByLabel("Seller Code (Optional)");
    const contactInput = page.getByLabel("Primary Contact Name");
    const emailInput = page.getByLabel("Work Email Address");
    const passwordInput = page.getByLabel("Account Password");
    const confirmInput = page.getByLabel("Confirm Password");
    const submitButton = page.locator("#signup-submit-button");

    await expect(companyInput).toBeVisible();
    await expect(sellerCodeInput).toBeVisible();
    await expect(contactInput).toBeVisible();
    await expect(emailInput).toBeVisible();
    await expect(passwordInput).toBeVisible();
    await expect(confirmInput).toBeVisible();
    await expect(submitButton).toHaveText(/Submit access request/);

    // Missing company name marks only company invalid, optional seller code remains valid
    await submitButton.click();
    const errorMessage = page.locator("#signup-error-message");
    await expect(errorMessage).toBeVisible();
    await expect(errorMessage).toHaveAttribute("role", "alert");
    await expect(errorMessage).toHaveAttribute("aria-live", "assertive");
    await expect(errorMessage).toContainText("Company or brand name is required.");
    await expect(companyInput).toHaveAttribute("aria-invalid", "true");
    await expect(companyInput).toHaveAttribute("aria-describedby", "signup-error-message");
    await expect(sellerCodeInput).not.toHaveAttribute("aria-invalid", "true");
    await expect(sellerCodeInput).not.toHaveAttribute("aria-describedby", "signup-error-message");
    expect(registrationRequestCount).toBe(0);

    // Rejection on 7-character password
    await companyInput.fill("Apex Apparel");
    await contactInput.fill("Alex Whitfield");
    await emailInput.fill("alex@company.com");
    await passwordInput.fill("Short1!");
    await confirmInput.fill("Short1!");
    await submitButton.click();

    await expect(errorMessage).toBeVisible();
    await expect(errorMessage).toHaveAttribute("role", "alert");
    await expect(errorMessage).toContainText("Password must be at least 8 characters.");
    await expect(passwordInput).toHaveAttribute("aria-invalid", "true");
    await expect(passwordInput).toHaveAttribute("aria-describedby", "signup-error-message");
    await expect(confirmInput).not.toHaveAttribute("aria-invalid", "true");
    await expect(sellerCodeInput).not.toHaveAttribute("aria-invalid", "true");
    expect(registrationRequestCount).toBe(0);

    // Rejection on mismatched password confirmation marks only confirmation invalid
    await passwordInput.fill("ValidPassword123!");
    await confirmInput.fill("DifferentPassword123!");
    await submitButton.click();

    await expect(errorMessage).toContainText("Passwords do not match.");
    await expect(confirmInput).toHaveAttribute("aria-invalid", "true");
    await expect(confirmInput).toHaveAttribute("aria-describedby", "signup-error-message");
    await expect(passwordInput).not.toHaveAttribute("aria-invalid", "true");
    await expect(passwordInput).not.toHaveAttribute("aria-describedby", "signup-error-message");
    await expect(sellerCodeInput).not.toHaveAttribute("aria-invalid", "true");
    await expect(companyInput).not.toHaveAttribute("aria-invalid", "true");
    expect(registrationRequestCount).toBe(0);
  });

  test("7.5 — Successful seller registration request with pending review notice", async ({
    page,
  }) => {
    let registrationPayload: {
      company_name?: string;
      email?: string;
      name?: string;
      password?: string;
      seller_code?: string;
    } | null = null;

    await page.route(/\/api\/v1\/auth\/register-seller/, async (route) => {
      registrationPayload = route.request().postDataJSON();
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          id: "00000000-0000-0000-0000-000000000099",
          email: "alex@company.com",
          name: "Alex Whitfield",
          role: "SELLER",
          status: "PENDING_APPROVAL",
        }),
      });
    });

    await page.goto("/signup");
    await expect(page.locator("#signup-form")).toHaveAttribute("data-hydrated", "true");
    await page.getByLabel("Company / Brand Name").fill("Apex Apparel LLC");
    await page.getByLabel("Seller Code (Optional)").fill("APEX");
    await page.getByLabel("Primary Contact Name").fill("Alex Whitfield");
    await page.getByLabel("Work Email Address").fill("alex@company.com");
    await page.getByLabel("Account Password").fill("SecurePassword123!");
    await page.getByLabel("Confirm Password").fill("SecurePassword123!");

    await page.locator("#signup-submit-button").click();

    // Verify submission payload
    expect(registrationPayload).not.toBeNull();
    expect(registrationPayload!.company_name).toBe("Apex Apparel LLC");
    expect(registrationPayload!.seller_code).toBe("APEX");
    expect(registrationPayload!.name).toBe("Alex Whitfield");
    expect(registrationPayload!.email).toBe("alex@company.com");
    expect(registrationPayload!.password).toBe("SecurePassword123!");

    // Verify truthful post-submission message
    await expect(page.getByRole("heading", { name: "Request submitted" })).toBeVisible();
    await expect(page.getByText(/pending administrator review/i)).toBeVisible();
    await expect(page.getByRole("button", { name: "Go to sign in" })).toBeVisible();

    // No false claims of immediate activation
    await expect(page.getByText(/account is active/i)).toHaveCount(0);
    await expect(page.getByText(/immediate access/i)).toHaveCount(0);
  });

  test("7.6 — Mobile narrow viewport usability at 360px width", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });

    // 1. Check Login page
    await page.goto("/login");
    await expect(page.locator("#login-form")).toHaveAttribute("data-hydrated", "true");
    const loginHeading = page.getByRole("heading", { name: "Sign in to Whitfield WMS" });
    await expect(loginHeading).toBeVisible();

    const hasNoLoginOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    );
    expect(hasNoLoginOverflow).toBe(true);

    const loginFormBox = await page.locator("#login-form").boundingBox();
    const loginContextBox = await page
      .getByRole("heading", { name: "Warehouse work starts with the right access." })
      .boundingBox();
    expect(loginFormBox).not.toBeNull();
    expect(loginContextBox).not.toBeNull();
    // Form appears before contextual panel
    expect(loginFormBox!.y).toBeLessThan(loginContextBox!.y);

    const loginSubmitBox = await page.locator("#login-submit-button").boundingBox();
    expect(loginSubmitBox).not.toBeNull();
    expect(loginSubmitBox!.x).toBeGreaterThanOrEqual(0);
    expect(loginSubmitBox!.x + loginSubmitBox!.width).toBeLessThanOrEqual(360);

    // 2. Check Signup page
    await page.goto("/signup");
    await expect(page.locator("#signup-form")).toHaveAttribute("data-hydrated", "true");
    const signupHeading = page.getByRole("heading", { name: "Create seller access request" });
    await expect(signupHeading).toBeVisible();

    const hasNoSignupOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    );
    expect(hasNoSignupOverflow).toBe(true);

    const signupFormBox = await page.locator("#signup-form").boundingBox();
    const signupContextBox = await page
      .getByRole("heading", { name: "Request access to Whitfield fulfillment." })
      .boundingBox();
    expect(signupFormBox).not.toBeNull();
    expect(signupContextBox).not.toBeNull();
    // Form appears before contextual panel
    expect(signupFormBox!.y).toBeLessThan(signupContextBox!.y);

    const signupSubmitBox = await page.locator("#signup-submit-button").boundingBox();
    expect(signupSubmitBox).not.toBeNull();
    expect(signupSubmitBox!.x).toBeGreaterThanOrEqual(0);
    expect(signupSubmitBox!.x + signupSubmitBox!.width).toBeLessThanOrEqual(360);
  });

  test("successful sign-in redirects to authenticated dashboard without hydration error", async ({
    page,
  }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto("/login");
    await expect(page.locator("#login-form")).toHaveAttribute("data-hydrated", "true");
    const submitButton = page.locator("#login-submit-button");
    await expect(submitButton).toBeVisible();

    const emailInput = page.getByLabel("Work Email");
    const passwordInput = page.locator("#login-password");

    await emailInput.fill("admin@whitfield.local");
    await passwordInput.fill("WhitfieldAdmin123!");
    await submitButton.click();

    await page.waitForURL((url) => !url.pathname.includes("/login"));
    await expect(page.locator("text=Whitfield Logistics").first()).toBeVisible();
    await expect(page.locator("text=System Admin").first()).toBeVisible();

    const hydrationErrors = consoleErrors.filter(
      (msg) =>
        msg.includes("Hydration failed") ||
        msg.includes("server rendered HTML didn't match") ||
        msg.includes("hydration mismatch"),
    );
    expect(hydrationErrors).toEqual([]);
  });

  test("authenticated direct navigation to /inventory survives initial hydration without error", async ({
    page,
  }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        consoleErrors.push(msg.text());
      }
    });

    await injectAuthSession(page);
    await page.goto("/inventory");

    await expect(page).toHaveURL(/.*\/inventory/);
    await expect(page.locator("h1")).toContainText(/Inventory|Balances/);
    await expect(page.locator("text=System Admin").first()).toBeVisible();

    const hydrationErrors = consoleErrors.filter(
      (msg) =>
        msg.includes("Hydration failed") ||
        msg.includes("server rendered HTML didn't match") ||
        msg.includes("hydration mismatch"),
    );
    expect(hydrationErrors).toEqual([]);
  });

  test("unauthenticated access to a protected route redirects to /login", async ({ page }) => {
    await clearAuthSession(page);
    await page.goto("/orders");

    await page.waitForURL("**/login");
    await expect(page.locator("#login-submit-button")).toBeVisible();
  });

  test("sign-out clears session and redirects to login", async ({ page }) => {
    await injectAuthSession(page);
    await page.goto("/");

    await expect(page.locator("text=System Admin").first()).toBeVisible();

    const signOutBtn = page.locator('button[aria-label="Sign out"]');
    await expect(signOutBtn).toBeVisible();
    await signOutBtn.click();

    await page.waitForURL("**/login");
    await expect(page.locator("#login-submit-button")).toBeVisible();
  });

  test("explicit 401 from /auth/me clears session and redirects to /login", async ({ page }) => {
    await injectAuthSession(page);

    await page.route(/\/api\/v1\/auth\/me/, async (route) => {
      await route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Invalid or expired token", code: "UNAUTHORIZED" }),
      });
    });

    await page.goto("/inventory");
    await page.waitForURL("**/login");
    await expect(page.locator("#login-submit-button")).toBeVisible();
  });

  test("temporary network failure from /auth/me does not clear stored session", async ({ page }) => {
    await injectAuthSession(page);

    await page.route(/\/api\/v1\/auth\/me/, async (route) => {
      await route.abort("failed");
    });

    await page.goto("/inventory");
    await expect(page).toHaveURL(/.*\/inventory/);
    await expect(page.locator("h1")).toContainText(/Inventory|Balances/);
  });

  test("unauthenticated visit to root / redirects to /login without promotional landing content", async ({
    page,
  }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto("/");
    await page.waitForURL("**/login");

    expect(page.url()).toContain("/login");
    await expect(page.getByRole("heading", { name: "Sign in to Whitfield WMS" })).toBeVisible();
    await expect(page.getByRole("button", { name: /Sign in/i })).toBeVisible();

    await expect(page.getByText(/Nationwide Fulfillment/i)).toHaveCount(0);
    await expect(page.getByText(/2-Day delivery/i)).toHaveCount(0);
    await expect(page.getByText(/Next-Generation Fulfillment/i)).toHaveCount(0);
    await expect(page.getByText(/SAMPLE_TRACKING_DATA/i)).toHaveCount(0);

    const hydrationErrors = consoleErrors.filter(
      (msg) =>
        msg.includes("Hydration failed") ||
        msg.includes("server rendered HTML didn't match") ||
        msg.includes("Minified React error #418") ||
        msg.includes("Minified React error #423") ||
        msg.includes("Minified React error #425"),
    );
    expect(hydrationErrors).toHaveLength(0);
  });
});
