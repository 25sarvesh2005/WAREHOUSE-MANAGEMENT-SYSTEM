import { test, expect } from "@playwright/test";
import { clearAuthSession, setupStandardApiMocks } from "./helpers/auth";

test.describe("Authentication Flows", () => {
  test.beforeEach(async ({ page }) => {
    await clearAuthSession(page);
    await setupStandardApiMocks(page);
  });

  test("renders sign-in page with required branding and inputs", async ({ page }) => {
    await page.goto("/login");
    await expect(page.locator("#login-submit-button")).toBeVisible();

    // Title and branding
    await expect(page).toHaveTitle(/Sign In \| Whitfield Ops/);
    await expect(page.locator("text=Whitfield Ops").first()).toBeVisible();
    await expect(page.locator("h1")).toContainText("Sign in");

    // Inputs & buttons
    await expect(page.locator("#login-email")).toBeVisible();
    await expect(page.locator("#login-password")).toBeVisible();
    await expect(page.locator("#login-submit-button")).toContainText("Sign In");
  });

  test("validates short password input", async ({ page }) => {
    await page.goto("/login");
    await expect(page.locator("#login-submit-button")).toBeVisible();
    await page.waitForTimeout(300);

    const emailInput = page.locator("#login-email");
    const passwordInput = page.locator("#login-password");
    const submitButton = page.locator("#login-submit-button");

    await emailInput.fill("admin@whitfield.local");
    await passwordInput.fill("123");
    await submitButton.click();

    await expect(page.locator("#login-error-message")).toContainText(
      "Password must be at least 8 characters.",
    );
  });

  test("successful sign-in redirects to authenticated dashboard", async ({ page }) => {
    await page.goto("/login");
    await expect(page.locator("#login-submit-button")).toBeVisible();
    await page.waitForTimeout(300);

    const emailInput = page.locator("#login-email");
    const passwordInput = page.locator("#login-password");
    const submitButton = page.locator("#login-submit-button");

    await emailInput.fill("admin@whitfield.local");
    await passwordInput.fill("WhitfieldAdmin123!");
    await submitButton.click();

    // After sign-in, user is redirected to dashboard
    await page.waitForURL((url) => !url.pathname.includes("/login"));
    await expect(page.locator("text=Whitfield Ops").first()).toBeVisible();
    await expect(page.locator("text=System Admin").first()).toBeVisible();
  });

  test("sign-out clears session and redirects to login", async ({ page }) => {
    // Start by logging in
    await page.goto("/login");
    await expect(page.locator("#login-submit-button")).toBeVisible();
    await page.waitForTimeout(300);

    await page.locator("#login-email").fill("admin@whitfield.local");
    await page.locator("#login-password").fill("WhitfieldAdmin123!");
    await page.locator("#login-submit-button").click();

    await page.waitForURL((url) => !url.pathname.includes("/login"));

    // Click sign-out button
    const signOutBtn = page.locator('button[aria-label="Sign out"]');
    await expect(signOutBtn).toBeVisible();
    await signOutBtn.click();

    // Should redirect back to /login
    await page.waitForURL("**/login");
    await expect(page.locator("h1")).toContainText("Sign in");
  });
});
