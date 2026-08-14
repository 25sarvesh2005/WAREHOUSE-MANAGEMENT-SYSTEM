import { test, expect } from "@playwright/test";
import { injectAuthSession, setupStandardApiMocks } from "./helpers/auth";

test.describe("Warehouse Operational Pages", () => {
  test.beforeEach(async ({ page }) => {
    await setupStandardApiMocks(page);
    await injectAuthSession(page);
  });

  test("loads inventory page with balance metrics and table rows", async ({ page }) => {
    await page.goto("/inventory");

    await expect(page.locator("h1")).toContainText(/Inventory|Balances/);
    await expect(page.locator("text=SKU-TEST-001").first()).toBeVisible();
    await expect(page.locator("text=RENO").first()).toBeVisible();
  });

  test("loads receipts page and displays staged receipts list", async ({ page }) => {
    await page.goto("/receipts");

    await expect(page.locator("h1")).toContainText(/Inbound Receipts|Receipts/);
    await expect(page.locator("text=REC-2026-0001").first()).toBeVisible();
    await expect(page.locator("text=ALPHA").first()).toBeVisible();
  });

  test("loads orders page and displays order list", async ({ page }) => {
    await page.goto("/orders");

    await expect(page.locator("h1")).toContainText(/Orders/);
    await expect(page.locator("text=ORD-2026-0001").first()).toBeVisible();
    await expect(page.locator("text=Reno, NV").first()).toBeVisible();
  });

  test("loads transfers page with origin and destination warehouses", async ({ page }) => {
    await page.goto("/transfers");

    await expect(page.locator("h1")).toContainText(/Transfers/);
    await expect(page.locator("text=TRN-2026-0001").first()).toBeVisible();
    await expect(page.locator("text=RENO").first()).toBeVisible();
  });

  test("loads returns page with RMA records", async ({ page }) => {
    await page.goto("/returns");

    await expect(page.locator("h1")).toContainText(/Returns/);
    await expect(page.locator("text=RMA-2026-0001").first()).toBeVisible();
  });

  test("loads migration panel and displays staged/applied batches", async ({ page }) => {
    await page.goto("/migration");

    await expect(page.locator("text=MIG-20260814-001").first()).toBeVisible();
    await expect(page.locator("text=APPLIED").first()).toBeVisible();
  });
});
