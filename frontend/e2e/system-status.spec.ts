import { expect, test } from "@playwright/test";
import {
  injectAuthSession,
  MOCK_ADMIN_USER,
  setupStandardApiMocks,
} from "./helpers/auth";

test.describe("Truthful Operations Status Indicator", () => {
  test.beforeEach(async ({ page }) => {
    await setupStandardApiMocks(page);
  });

  test("healthy response displays truthful status without hardcoded SLA or uptime claims", async ({ page }) => {
    await page.route(/\/health\/status/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "HEALTHY",
          timestamp: "2026-09-03T12:00:00.000Z",
          service: "whitfield-core",
          version: "1.0.0",
          app_env: "production",
          database: {
            status: "connected",
            latency_ms: 14,
          },
          alembic_head: "head",
          ai: {
            enabled: true,
            provider: "google",
            model: "gemini-2.0-flash",
            status: "HEALTHY",
          },
          warnings: [],
        }),
      });
    });

    await injectAuthSession(page, MOCK_ADMIN_USER);
    await page.goto("/");

    const statusCard = page.locator('aside [role="status"]');
    await expect(statusCard).toBeVisible();
    await expect(statusCard).toHaveAttribute("aria-label", "System status: Operational");
    await expect(statusCard).toContainText("Operations service");
    await expect(statusCard).toContainText("Operational");
    await expect(statusCard).toContainText("Database connected · 14 ms");

    // Must not display hardcoded misleading strings
    const sidebar = page.locator("aside");
    await expect(sidebar).not.toContainText("ONLINE");
    await expect(sidebar).not.toContainText("Bicoastal 2-Day SLA");
    await expect(sidebar).not.toContainText("99.98%");
  });

  test("loading state displays checking and transitions cleanly upon resolution", async ({ page }) => {
    let resolveHealthPromise!: () => void;
    const healthGate = new Promise<void>((resolve) => {
      resolveHealthPromise = resolve;
    });

    await page.route(/\/health\/status/, async (route) => {
      await healthGate;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "HEALTHY",
          timestamp: "2026-09-03T12:00:00.000Z",
          service: "whitfield-core",
          version: "1.0.0",
          app_env: "production",
          database: {
            status: "connected",
            latency_ms: 8,
          },
          alembic_head: "head",
          ai: {
            enabled: true,
            provider: "google",
            model: "gemini-2.0-flash",
            status: "HEALTHY",
          },
          warnings: [],
        }),
      });
    });

    await injectAuthSession(page, MOCK_ADMIN_USER);
    await page.goto("/");

    const statusCard = page.locator('aside [role="status"]');
    await expect(statusCard).toBeVisible();
    await expect(statusCard).toHaveAttribute("aria-label", "System status: Checking");
    await expect(statusCard).toContainText("Checking");
    await expect(statusCard).toContainText("Checking live system health…");
    await expect(statusCard).not.toContainText("Operational");

    // Resolve network gate
    resolveHealthPromise();

    await expect(statusCard).toHaveAttribute("aria-label", "System status: Operational");
    await expect(statusCard).toContainText("Operational");
    await expect(statusCard).toContainText("Database connected · 8 ms");
  });

  test("degraded response shows warning count and attention guidance", async ({ page }) => {
    await page.route(/\/health\/status/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "DEGRADED",
          timestamp: "2026-09-03T12:00:00.000Z",
          service: "whitfield-core",
          version: "1.0.0",
          app_env: "production",
          database: {
            status: "disconnected",
            latency_ms: null,
          },
          alembic_head: "head",
          ai: {
            enabled: false,
            provider: "google",
            model: "gemini-2.0-flash",
            status: "UNHEALTHY",
          },
          warnings: ["Elevated asynchronous queue processing delay"],
        }),
      });
    });

    await injectAuthSession(page, MOCK_ADMIN_USER);
    await page.goto("/");

    const statusCard = page.locator('aside [role="status"]');
    await expect(statusCard).toBeVisible();
    await expect(statusCard).toHaveAttribute("aria-label", "System status: Degraded");
    await expect(statusCard).toContainText("Degraded");
    await expect(statusCard).toContainText("Some system checks need attention.");
    await expect(statusCard).toContainText("1 configuration warning");
    await expect(statusCard).not.toContainText("Operational");
  });

  test("unhealthy response shows unavailable and supporting alert", async ({ page }) => {
    await page.route(/\/health\/status/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "UNHEALTHY",
          timestamp: "2026-09-03T12:00:00.000Z",
          service: "whitfield-core",
          version: "1.0.0",
          app_env: "production",
          database: {
            status: "disconnected",
            latency_ms: null,
          },
          alembic_head: "head",
          ai: {
            enabled: false,
            provider: "google",
            model: "gemini-2.0-flash",
            status: "UNHEALTHY",
          },
          warnings: [],
        }),
      });
    });

    await injectAuthSession(page, MOCK_ADMIN_USER);
    await page.goto("/");

    const statusCard = page.locator('aside [role="status"]');
    await expect(statusCard).toBeVisible();
    await expect(statusCard).toHaveAttribute("aria-label", "System status: Unavailable");
    await expect(statusCard).toContainText("Unavailable");
    await expect(statusCard).toContainText("The operations service reported an unhealthy state.");
  });

  test("failed request shows retry button and recovers cleanly upon retry", async ({ page }) => {
    let shouldFail = true;
    await page.route(/\/health\/status/, async (route) => {
      if (shouldFail) {
        await route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({ detail: "Service Unavailable" }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            status: "HEALTHY",
            timestamp: "2026-09-03T12:00:00.000Z",
            service: "whitfield-core",
            version: "1.0.0",
            app_env: "production",
            database: {
              status: "connected",
              latency_ms: 11,
            },
            alembic_head: "head",
            ai: {
              enabled: true,
              provider: "google",
              model: "gemini-2.0-flash",
              status: "HEALTHY",
            },
            warnings: [],
          }),
        });
      }
    });

    await injectAuthSession(page, MOCK_ADMIN_USER);
    await page.goto("/");

    const statusCard = page.locator('aside [role="status"]');
    await expect(statusCard).toBeVisible();
    await expect(statusCard).toHaveAttribute("aria-label", "System status: Status unavailable");
    await expect(statusCard).toContainText("Status unavailable");
    await expect(statusCard).toContainText("Live health could not be verified.");

    // Raw HTTP error should not be rendered
    await expect(statusCard).not.toContainText("503");
    await expect(statusCard).not.toContainText("Service Unavailable");

    const retryButton = statusCard.getByRole("button", { name: "Retry status check" });
    await expect(retryButton).toBeVisible();

    // Allow retry request to succeed
    shouldFail = false;
    await retryButton.click();

    await expect(statusCard).toHaveAttribute("aria-label", "System status: Operational");
    await expect(statusCard).toContainText("Operational");
    await expect(statusCard).toContainText("Database connected · 11 ms");
  });

  test("renders valid timestamp with semantic time element and dateTime attribute", async ({ page }) => {
    const fixedIsoTime = "2026-09-03T15:30:00.000Z";
    await page.route(/\/health\/status/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "HEALTHY",
          timestamp: fixedIsoTime,
          service: "whitfield-core",
          version: "1.0.0",
          app_env: "production",
          database: {
            status: "connected",
            latency_ms: 5,
          },
          alembic_head: "head",
          ai: {
            enabled: true,
            provider: "google",
            model: "gemini-2.0-flash",
            status: "HEALTHY",
          },
          warnings: [],
        }),
      });
    });

    await injectAuthSession(page, MOCK_ADMIN_USER);
    await page.goto("/");

    const timeElement = page.locator('aside [role="status"] time');
    await expect(timeElement).toBeVisible();
    await expect(timeElement).toHaveAttribute("dateTime", fixedIsoTime);
  });

  test("mobile sheet displays truthful status card without horizontal overflow at 390x844", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.route(/\/health\/status/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "HEALTHY",
          timestamp: "2026-09-03T12:00:00.000Z",
          service: "whitfield-core",
          version: "1.0.0",
          app_env: "production",
          database: {
            status: "connected",
            latency_ms: 10,
          },
          alembic_head: "head",
          ai: {
            enabled: true,
            provider: "google",
            model: "gemini-2.0-flash",
            status: "HEALTHY",
          },
          warnings: [],
        }),
      });
    });

    await injectAuthSession(page, MOCK_ADMIN_USER);
    await page.goto("/");

    // Open mobile menu
    const menuBtn = page.getByRole("button", { name: "Open navigation" });
    await expect(menuBtn).toBeVisible();
    await menuBtn.click();

    const mobileDialog = page.getByRole("dialog");
    await expect(mobileDialog).toBeVisible();

    const mobileStatusCard = mobileDialog.locator('[role="status"]');
    await expect(mobileStatusCard).toBeVisible();
    await expect(mobileStatusCard).toContainText("Operational");
    await expect(mobileStatusCard).toContainText("Database connected · 10 ms");

    const hasHorizontalOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    );
    expect(hasHorizontalOverflow).toBe(false);
  });
});
