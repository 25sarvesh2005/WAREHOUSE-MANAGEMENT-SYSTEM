import { test, expect } from "@playwright/test";
import { injectAuthSession, setupStandardApiMocks } from "./helpers/auth";

test.describe("App Shell & Sidebar Navigation", () => {
  test.beforeEach(async ({ page }) => {
    await setupStandardApiMocks(page);
    await injectAuthSession(page);
  });

  test("loads authenticated dashboard and renders role-scoped sidebar links", async ({ page }) => {
    await page.goto("/");

    // App shell header & sidebar
    await expect(page.locator("text=Whitfield Ops").first()).toBeVisible();
    await expect(page.locator("text=System Admin").first()).toBeVisible();

    // Verify primary navigation links exist
    const nav = page.locator("nav");
    await expect(nav.locator('a[href="/"]')).toBeVisible();
    await expect(nav.locator('a[href="/inventory"]')).toBeVisible();
    await expect(nav.locator('a[href="/receipts"]')).toBeVisible();
    await expect(nav.locator('a[href="/orders"]')).toBeVisible();
    await expect(nav.locator('a[href="/pick-tasks"]')).toBeVisible();
    await expect(nav.locator('a[href="/shipments"]')).toBeVisible();
    await expect(nav.locator('a[href="/transfers"]')).toBeVisible();
    await expect(nav.locator('a[href="/returns"]')).toBeVisible();
    await expect(nav.locator('a[href="/migration"]')).toBeVisible();
    await expect(nav.locator('a[href="/ai-assistant"]')).toBeVisible();
    await expect(nav.locator('a[href="/admin"]')).toBeVisible();
  });

  test("navigates cleanly between operational pages without errors", async ({ page }) => {
    await page.goto("/");

    // 1. Inventory
    await page.locator('nav a[href="/inventory"]').click();
    await expect(page).toHaveURL(/.*\/inventory/);
    await expect(page.locator("h1")).toContainText(/Inventory|Balances/);

    // 2. Receipts
    await page.locator('nav a[href="/receipts"]').click();
    await expect(page).toHaveURL(/.*\/receipts/);
    await expect(page.locator("h1")).toContainText(/Inbound Receipts|Receipts/);

    // 3. Orders
    await page.locator('nav a[href="/orders"]').click();
    await expect(page).toHaveURL(/.*\/orders/);
    await expect(page.locator("h1")).toContainText(/Orders/);

    // 4. Transfers
    await page.locator('nav a[href="/transfers"]').click();
    await expect(page).toHaveURL(/.*\/transfers/);
    await expect(page.locator("h1")).toContainText(/Warehouse Transfers|Transfers/);

    // 5. Returns
    await page.locator('nav a[href="/returns"]').click();
    await expect(page).toHaveURL(/.*\/returns/);
    await expect(page.locator("h1")).toContainText(/Customer Returns|Returns/);

    // 6. Migration
    await page.locator('nav a[href="/migration"]').click();
    await expect(page).toHaveURL(/.*\/migration/);
    await expect(page.locator("h1")).toContainText(/Opening Inventory Migration/);

    // 7. AI Assistant
    await page.locator('nav a[href="/ai-assistant"]').click();
    await expect(page).toHaveURL(/.*\/ai-assistant/);
    await expect(page.locator("h1")).toContainText(/AI Assistant/);

    // 8. Admin Panel
    await page.locator('nav a[href="/admin"]').click();
    await expect(page).toHaveURL(/.*\/admin/);
    await expect(page.locator("h1")).toContainText(/Admin & Staff Hierarchy|Admin/);
  });
});
