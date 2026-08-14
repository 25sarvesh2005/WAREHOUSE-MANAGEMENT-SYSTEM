import { test, expect } from "@playwright/test";
import { injectAuthSession, setupStandardApiMocks } from "./helpers/auth";

test.describe("Admin Console, AI Audit & Controlled Launch", () => {
  test.beforeEach(async ({ page }) => {
    await setupStandardApiMocks(page);
    await injectAuthSession(page);
  });

  test("loads admin panel with all tab options", async ({ page }) => {
    await page.goto("/admin");

    await expect(page.locator("h1")).toContainText("Admin & Staff Hierarchy");

    // Check all admin tabs exist
    await expect(page.locator("text=Users & Staff Hierarchy").first()).toBeVisible();
    await expect(page.locator("text=Pending Sellers").first()).toBeVisible();
    await expect(page.locator("text=Sellers").first()).toBeVisible();
    await expect(page.locator("text=Warehouses").first()).toBeVisible();
    await expect(page.locator("text=Products").first()).toBeVisible();
    await expect(page.locator("text=AI Audit & Provider Health").first()).toBeVisible();
    await expect(page.locator("text=Controlled Launch & Health").first()).toBeVisible();
    await expect(page.locator("text=Migration").first()).toBeVisible();
  });

  test("loads AI Audit & Provider Health panel with engine status and audit log", async ({
    page,
  }) => {
    await page.goto("/admin");

    // Click AI Audit tab
    await page.locator("text=AI Audit & Provider Health").first().click();

    // Verify Provider Engine & Readiness cards
    await expect(page.locator("text=Provider Engine").first()).toBeVisible();
    await expect(page.locator("text=Google Gemini").first()).toBeVisible();
    await expect(page.locator("text=Operational & Healthy").first()).toBeVisible();

    // Verify AI Interaction Audit Log table
    await expect(page.locator("text=AI Interaction Audit Log").first()).toBeVisible();
    await expect(
      page.locator("text=Check availability for SKU-TEST-001 in RENO").first(),
    ).toBeVisible();

    // Click view detail button
    const viewDetailBtn = page.locator("button:has-text('View Detail')").first();
    await expect(viewDetailBtn).toBeVisible();
    await viewDetailBtn.click();

    // Verify Detail modal appears
    await expect(page.locator("text=AI Interaction Audit Detail").first()).toBeVisible();
    await expect(page.locator("text=Sanitized Prompt Excerpt").first()).toBeVisible();
  });

  test("loads Controlled Launch panel with diagnostics, checklist and evidence export", async ({
    page,
  }) => {
    await page.goto("/admin");

    // Click Controlled Launch tab
    await page.locator("text=Controlled Launch & Health").first().click();

    // Verify diagnostics cards
    await expect(page.locator("text=Database Status").first()).toBeVisible();
    await expect(page.locator("text=Connected").first()).toBeVisible();
    await expect(page.locator("text=Alembic Revision").first()).toBeVisible();
    await expect(page.locator("text=c1f2e3d4a5b6").first()).toBeVisible();

    // Verify Pre-Launch Verification Checklist
    await expect(page.locator("text=Pre-Launch Verification Checklist").first()).toBeVisible();
    await expect(page.locator("text=1. Alembic Schema Revision Applied").first()).toBeVisible();
    await expect(
      page.locator("text=2. Authentication & JWT Hardening Verified").first(),
    ).toBeVisible();

    // Verify Export Launch Evidence button exists and is clickable
    const exportBtn = page.locator("button:has-text('Export Launch Evidence')").first();
    await expect(exportBtn).toBeVisible();
  });
});
