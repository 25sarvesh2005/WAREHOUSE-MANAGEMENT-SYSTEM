import { test, expect } from "@playwright/test";
import { clearAuthSession, injectAuthSession, setupStandardApiMocks } from "./helpers/auth";

test.describe("Authentication Flows & Hydration", () => {
  test.beforeEach(async ({ page }) => {
    await clearAuthSession(page);
    await setupStandardApiMocks(page);
  });

  test("renders sign-in page with required branding and inputs without hydration error", async ({
    page,
  }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        consoleErrors.push(msg.text());
      }
    });

    await page.goto("/login");
    await expect(page.locator("#login-submit-button")).toBeVisible();

    // Title and branding
    await expect(page).toHaveTitle(/Sign In.*Whitfield Logistics/);
    await expect(page.locator("text=Whitfield Logistics").first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Sign In" })).toBeVisible();

    // Inputs & buttons
    const emailInput = page.getByLabel("Work Email");
    const passwordInput = page.locator("#login-password");
    await expect(emailInput).toBeVisible();
    await expect(passwordInput).toBeVisible();
    await expect(page.locator("#login-submit-button")).toContainText("Sign In");

    const hydrationErrors = consoleErrors.filter(
      (msg) =>
        msg.includes("Hydration failed") ||
        msg.includes("server rendered HTML didn't match") ||
        msg.includes("hydration mismatch"),
    );
    expect(hydrationErrors).toEqual([]);
  });

  test("validates short password input", async ({ page }) => {
    await page.goto("/login");
    await expect(page.locator("#login-submit-button")).toBeVisible();
    await page.waitForTimeout(300);

    const emailInput = page.getByLabel("Work Email");
    const passwordInput = page.locator("#login-password");
    const submitButton = page.locator("#login-submit-button");

    await emailInput.fill("admin@whitfield.local");
    await passwordInput.fill("123");
    await submitButton.click();

    await expect(page.locator("#login-error-message")).toContainText(
      "Password must be at least 8 characters.",
    );
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
    await expect(page.locator("#login-submit-button")).toBeVisible();
    await page.waitForTimeout(300);

    const emailInput = page.getByLabel("Work Email");
    const passwordInput = page.locator("#login-password");
    const submitButton = page.locator("#login-submit-button");

    await emailInput.fill("admin@whitfield.local");
    await passwordInput.fill("WhitfieldAdmin123!");
    await submitButton.click();

    // After sign-in, user is redirected to dashboard
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

    // Click sign-out button
    const signOutBtn = page.locator('button[aria-label="Sign out"]');
    await expect(signOutBtn).toBeVisible();
    await signOutBtn.click();

    // Should redirect back to /login
    await page.waitForURL("**/login");
    await expect(page.locator("#login-submit-button")).toBeVisible();
  });

  test("explicit 401 from /auth/me clears session and redirects to /login", async ({ page }) => {
    await injectAuthSession(page);

    // Override /auth/me to return 401 Unauthorized
    await page.route(/\/api\/v1\/auth\/me/, async (route) => {
      await route.fulfill({
        status: 401,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Invalid or expired token", code: "UNAUTHORIZED" }),
      });
    });

    await page.goto("/inventory");

    // Must clear session and redirect to /login
    await page.waitForURL("**/login");
    await expect(page.locator("#login-submit-button")).toBeVisible();
  });

  test("temporary network failure from /auth/me does not clear stored session", async ({ page }) => {
    await injectAuthSession(page);

    // Override /auth/me to simulate network disconnection / 503
    await page.route(/\/api\/v1\/auth\/me/, async (route) => {
      await route.abort("failed");
    });

    await page.goto("/inventory");

    // Stored user remains authenticated on the page
    await expect(page).toHaveURL(/.*\/inventory/);
    await expect(page.locator("h1")).toContainText(/Inventory|Balances/);
  });
});
