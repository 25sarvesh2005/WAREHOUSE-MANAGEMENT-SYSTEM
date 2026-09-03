import { expect, test } from "@playwright/test";
import {
  injectAuthSession,
  MOCK_ADMIN_USER,
  setupStandardApiMocks,
} from "./helpers/auth";

test.describe("Global Search & URL Filter State", () => {
  test.beforeEach(async ({ page }) => {
    await setupStandardApiMocks(page);
  });

  test("order search routes to /orders with q and filters orders list", async ({ page }) => {
    await injectAuthSession(page, MOCK_ADMIN_USER);
    await page.goto("/");

    const searchInput = page.locator('input[aria-label="Search warehouse records"]');
    await searchInput.fill("ORD-2026-0001");
    await searchInput.press("Enter");

    await expect(page).toHaveURL(/.*\/orders\?q=ORD-2026-0001/);

    const pageSearchInput = page.locator('input[placeholder*="Search order"]');
    await expect(pageSearchInput).toHaveValue("ORD-2026-0001");

    await expect(page.locator("table")).toContainText("ORD-2026-0001");
  });

  test("receipt search routes to /receipts with q and filters receipts list", async ({ page }) => {
    await injectAuthSession(page, MOCK_ADMIN_USER);
    await page.goto("/");

    const searchInput = page.locator('input[aria-label="Search warehouse records"]');
    await searchInput.fill("REC-2026-0001");
    await searchInput.press("Enter");

    await expect(page).toHaveURL(/.*\/receipts\?q=REC-2026-0001/);

    const pageSearchInput = page.locator('input[placeholder*="Scan tracking"]');
    await expect(pageSearchInput).toHaveValue("REC-2026-0001");

    await expect(page.locator("table")).toContainText("REC-2026-0001");
  });

  test("inventory search routes to /inventory with q and filters inventory balances", async ({ page }) => {
    await injectAuthSession(page, MOCK_ADMIN_USER);
    await page.goto("/");

    const searchInput = page.locator('input[aria-label="Search warehouse records"]');
    await searchInput.fill("SKU-TEST-001");
    await searchInput.press("Enter");

    await expect(page).toHaveURL(/.*\/inventory\?q=SKU-TEST-001/);

    const pageSearchInput = page.locator('input[placeholder*="Scan barcode"]');
    await expect(pageSearchInput).toHaveValue("SKU-TEST-001");

    await expect(page.locator("table")).toContainText("SKU-TEST-001");
  });

  test("transfer search routes to /transfers with TRN- and retains query", async ({ page }) => {
    await injectAuthSession(page, MOCK_ADMIN_USER);
    await page.goto("/");

    const searchInput = page.locator('input[aria-label="Search warehouse records"]');
    await searchInput.fill("TRN-2026-0001");
    await searchInput.press("Enter");

    await expect(page).toHaveURL(/.*\/transfers\?q=TRN-2026-0001/);

    const pageSearchInput = page.getByRole("searchbox", { name: "Search transfers" });
    await expect(pageSearchInput).toBeVisible();
    await expect(pageSearchInput).toHaveValue("TRN-2026-0001");

    await expect(page.locator("table")).toBeVisible();
    await expect(page.locator("table")).toContainText("TRF-00000000");
  });

  test("return search routes to /returns with RMA- and retains query", async ({ page }) => {
    await injectAuthSession(page, MOCK_ADMIN_USER);
    await page.goto("/");

    const searchInput = page.locator('input[aria-label="Search warehouse records"]');
    await searchInput.fill("RMA-2026-0001");
    await searchInput.press("Enter");

    await expect(page).toHaveURL(/.*\/returns\?q=RMA-2026-0001/);

    const pageSearchInput = page.getByRole("searchbox", { name: "Search returns" });
    await expect(pageSearchInput).toBeVisible();
    await expect(pageSearchInput).toHaveValue("RMA-2026-0001");

    await expect(page.locator("table")).toContainText("RMA-2026-0001");
  });

  test("case-insensitive prefix classification preserves user-entered casing", async ({ page }) => {
    await injectAuthSession(page, MOCK_ADMIN_USER);
    await page.goto("/");

    const searchInput = page.locator('input[aria-label="Search warehouse records"]');
    await searchInput.fill("ord-2026-0001");
    await searchInput.press("Enter");

    await expect(page).toHaveURL(/.*\/orders\?q=ord-2026-0001/);
    await expect(page.locator("table")).toContainText("ORD-2026-0001");
  });

  test("unsupported query displays error toast and does not clear input or navigate", async ({ page }) => {
    await injectAuthSession(page, MOCK_ADMIN_USER);
    await page.goto("/");

    const searchInput = page.locator('input[aria-label="Search warehouse records"]');
    await searchInput.fill("UNKNOWN-123");
    await searchInput.press("Enter");

    await expect(page).toHaveURL(/\/$/);
    await expect(searchInput).toHaveValue("UNKNOWN-123");
    await expect(page.locator('[data-sonner-toast][data-type="error"]')).toContainText("Search format not recognized");
  });

  test("empty query does not navigate or trigger errors", async ({ page }) => {
    await injectAuthSession(page, MOCK_ADMIN_USER);
    await page.goto("/");

    const searchInput = page.locator('input[aria-label="Search warehouse records"]');
    await searchInput.fill("   ");
    await searchInput.press("Enter");

    await expect(page).toHaveURL(/\/$/);
    await expect(page.locator('[data-sonner-toast]')).toBeHidden();
  });

  test("permission safety prevents search navigation and alerts unauthorized users", async ({ page }) => {
    const receiverUser = {
      ...MOCK_ADMIN_USER,
      id: "00000000-0000-0000-0000-000000000008",
      role: "RECEIVER" as const,
    };
    await page.route(/\/api\/v1\/auth\/me/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(receiverUser),
      });
    });

    await injectAuthSession(page, receiverUser);
    await page.goto("/");

    const searchInput = page.locator('input[aria-label="Search warehouse records"]');
    await searchInput.fill("ORD-2026-0001");
    await searchInput.press("Enter");

    await expect(page).not.toHaveURL(/.*\/orders/);
    await expect(searchInput).toHaveValue("ORD-2026-0001");
    await expect(page.locator('[data-sonner-toast][data-type="error"]')).toContainText("You do not have access to search Orders.");
  });

  test("direct URL and reload preserves search filter", async ({ page }) => {
    await injectAuthSession(page, MOCK_ADMIN_USER);
    await page.goto("/orders?q=ORD-2026-0001");

    const pageSearchInput = page.locator('input[placeholder*="Search order"]');
    await expect(pageSearchInput).toHaveValue("ORD-2026-0001");
    await expect(page.locator("table")).toContainText("ORD-2026-0001");

    await page.reload();

    await expect(page).toHaveURL(/.*\/orders\?q=ORD-2026-0001/);
    await expect(pageSearchInput).toHaveValue("ORD-2026-0001");
    await expect(page.locator("table")).toContainText("ORD-2026-0001");
  });

  test("clearing destination search removes q from URL", async ({ page }) => {
    await injectAuthSession(page, MOCK_ADMIN_USER);
    await page.goto("/orders?q=ORD-2026-0001");

    const pageSearchInput = page.locator('input[placeholder*="Search order"]');
    await expect(pageSearchInput).toHaveValue("ORD-2026-0001");

    await pageSearchInput.fill("");

    await expect(page).toHaveURL(/\/orders$/);
    await expect(page.locator("table")).toContainText("ORD-2026-0001");
  });

  test("no-result state appears when search query has no matching records", async ({ page }) => {
    await injectAuthSession(page, MOCK_ADMIN_USER);

    await page.goto("/transfers?q=TRN-NONEXISTENT");
    await expect(page.getByText("No transfers match this search")).toBeVisible();
    await expect(page.getByText("Clear or adjust the search query to see other transfers.")).toBeVisible();

    await page.goto("/returns?q=RMA-NONEXISTENT");
    await expect(page.getByText("No returns match this search")).toBeVisible();
    await expect(page.getByText("Clear or adjust the search query to see other returns.")).toBeVisible();
  });

  test("responsive behavior at 360x800 has no horizontal overflow", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await injectAuthSession(page, MOCK_ADMIN_USER);

    await page.goto("/transfers");
    const transferInput = page.getByRole("searchbox", { name: "Search transfers" });
    await expect(transferInput).toBeVisible();
    const transferBox = await transferInput.boundingBox();
    expect(transferBox).not.toBeNull();
    expect(transferBox!.height).toBeGreaterThanOrEqual(44);
    const transfersOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    );
    expect(transfersOverflow).toBe(false);

    await page.goto("/returns");
    const returnInput = page.getByRole("searchbox", { name: "Search returns" });
    await expect(returnInput).toBeVisible();
    const returnBox = await returnInput.boundingBox();
    expect(returnBox).not.toBeNull();
    expect(returnBox!.height).toBeGreaterThanOrEqual(44);
    const returnsOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    );
    expect(returnsOverflow).toBe(false);
  });
});
