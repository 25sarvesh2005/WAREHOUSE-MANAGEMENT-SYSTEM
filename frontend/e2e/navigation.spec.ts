import { test, expect } from "@playwright/test";
import {
  injectAuthSession,
  setupStandardApiMocks,
  MOCK_ADMIN_USER,
} from "./helpers/auth";

test.describe("App Shell & Sidebar Navigation", () => {
  test.beforeEach(async ({ page }) => {
    await setupStandardApiMocks(page);
  });

  test("Administrator sees all 11 navigation items and 6 group headings", async ({ page }) => {
    await injectAuthSession(page, MOCK_ADMIN_USER);
    await page.goto("/");

    // Branding & identity
    await expect(page.locator("text=Whitfield Logistics").first()).toBeVisible();
    await expect(page.locator("text=System Admin").first()).toBeVisible();

    // Group labels
    const nav = page.locator("aside nav");
    await expect(nav.locator("text=OVERVIEW")).toBeVisible();
    await expect(nav.locator("text=INBOUND")).toBeVisible();
    await expect(nav.locator("text=INVENTORY CONTROL")).toBeVisible();
    await expect(nav.locator("text=FULFILLMENT")).toBeVisible();
    await expect(nav.locator("text=INTELLIGENCE")).toBeVisible();
    await expect(nav.locator("text=ADMINISTRATION")).toBeVisible();

    // All 11 navigation items
    await expect(nav.locator('a[href="/"]')).toContainText("Dashboard");
    await expect(nav.locator('a[href="/receipts"]')).toContainText("Receiving");
    await expect(nav.locator('a[href="/returns"]')).toContainText("Returns");
    await expect(nav.locator('a[href="/inventory"]')).toContainText("Inventory");
    await expect(nav.locator('a[href="/transfers"]')).toContainText("Transfers");
    await expect(nav.locator('a[href="/orders"]')).toContainText("Orders");
    await expect(nav.locator('a[href="/pick-tasks"]')).toContainText("Pick Tasks");
    await expect(nav.locator('a[href="/shipments"]')).toContainText("Shipments");
    await expect(nav.locator('a[href="/ai-assistant"]')).toContainText("AI Assistant");
    await expect(nav.locator('a[href="/migration"]')).toContainText("Inventory Migration");
    await expect(nav.locator('a[href="/admin"]')).toContainText("Admin");
  });

  test("Receiver sees only authorized inbound/inventory items without empty groups", async ({ page }) => {
    const receiverUser = {
      ...MOCK_ADMIN_USER,
      role: "RECEIVER" as const,
      name: "Receiving Clerk",
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

    const nav = page.locator("aside nav");
    await expect(nav.locator('a[href="/"]')).toBeVisible();
    await expect(nav.locator('a[href="/receipts"]')).toBeVisible();
    await expect(nav.locator('a[href="/returns"]')).toBeVisible();
    await expect(nav.locator('a[href="/inventory"]')).toBeVisible();
    await expect(nav.locator('a[href="/ai-assistant"]')).toBeVisible();

    // Unauthorized links should not exist
    await expect(nav.locator('a[href="/orders"]')).toHaveCount(0);
    await expect(nav.locator('a[href="/pick-tasks"]')).toHaveCount(0);
    await expect(nav.locator('a[href="/shipments"]')).toHaveCount(0);
    await expect(nav.locator('a[href="/transfers"]')).toHaveCount(0);
    await expect(nav.locator('a[href="/migration"]')).toHaveCount(0);
    await expect(nav.locator('a[href="/admin"]')).toHaveCount(0);

    // Empty group labels should not be rendered
    await expect(nav.locator("text=FULFILLMENT")).toHaveCount(0);
    await expect(nav.locator("text=ADMINISTRATION")).toHaveCount(0);
  });

  test("Picker/Packer sees only fulfillment and authorized items", async ({ page }) => {
    const pickerUser = {
      ...MOCK_ADMIN_USER,
      role: "PICKER_PACKER" as const,
      name: "Floor Picker",
    };
    await page.route(/\/api\/v1\/auth\/me/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(pickerUser),
      });
    });
    await injectAuthSession(page, pickerUser);
    await page.goto("/");

    const nav = page.locator("aside nav");
    await expect(nav.locator('a[href="/"]')).toBeVisible();
    await expect(nav.locator('a[href="/orders"]')).toBeVisible();
    await expect(nav.locator('a[href="/pick-tasks"]')).toBeVisible();
    await expect(nav.locator('a[href="/shipments"]')).toBeVisible();
    await expect(nav.locator('a[href="/ai-assistant"]')).toBeVisible();

    // Unauthorized links
    await expect(nav.locator('a[href="/receipts"]')).toHaveCount(0);
    await expect(nav.locator('a[href="/returns"]')).toHaveCount(0);
    await expect(nav.locator('a[href="/inventory"]')).toHaveCount(0);
    await expect(nav.locator('a[href="/transfers"]')).toHaveCount(0);
    await expect(nav.locator('a[href="/migration"]')).toHaveCount(0);
    await expect(nav.locator('a[href="/admin"]')).toHaveCount(0);

    // Empty groups
    await expect(nav.locator("text=INBOUND")).toHaveCount(0);
    await expect(nav.locator("text=INVENTORY CONTROL")).toHaveCount(0);
    await expect(nav.locator("text=ADMINISTRATION")).toHaveCount(0);
  });

  test("Seller sees only seller-authorized routes", async ({ page }) => {
    const sellerUser = {
      ...MOCK_ADMIN_USER,
      role: "SELLER" as const,
      name: "Merchant Seller",
    };
    await page.route(/\/api\/v1\/auth\/me/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(sellerUser),
      });
    });
    await injectAuthSession(page, sellerUser);
    await page.goto("/");

    const nav = page.locator("aside nav");
    await expect(nav.locator('a[href="/"]')).toBeVisible();
    await expect(nav.locator('a[href="/inventory"]')).toBeVisible();
    await expect(nav.locator('a[href="/orders"]')).toBeVisible();
    await expect(nav.locator('a[href="/shipments"]')).toBeVisible();
    await expect(nav.locator('a[href="/returns"]')).toBeVisible();
    await expect(nav.locator('a[href="/ai-assistant"]')).toBeVisible();

    // Unauthorized links
    await expect(nav.locator('a[href="/receipts"]')).toHaveCount(0);
    await expect(nav.locator('a[href="/pick-tasks"]')).toHaveCount(0);
    await expect(nav.locator('a[href="/transfers"]')).toHaveCount(0);
    await expect(nav.locator('a[href="/migration"]')).toHaveCount(0);
    await expect(nav.locator('a[href="/admin"]')).toHaveCount(0);
  });

  test("header duplication controls are removed and search has accessible label", async ({ page }) => {
    await injectAuthSession(page, MOCK_ADMIN_USER);
    await page.goto("/");

    const header = page.locator("header");

    // Bell, header AI Copilot, and duplicate facility badges must be absent
    await expect(header.locator("button:has(svg.lucide-bell)")).toHaveCount(0);
    await expect(header.locator('a:has-text("AI Copilot")')).toHaveCount(0);
    await expect(header.locator('text="RNO Reno"')).toHaveCount(0);
    await expect(header.locator('text="CMH Columbus"')).toHaveCount(0);

    // Search input has accessible label
    const searchInput = header.locator('input[aria-label="Search warehouse records"]');
    await expect(searchInput).toBeVisible();
    await expect(searchInput).toHaveAttribute(
      "placeholder",
      "Search Orders (ORD-), Receipts (REC-), Transfers (TRF-), or SKUs...",
    );
  });

  test("skip to main content link exists and targets #main-content", async ({ page }) => {
    await injectAuthSession(page, MOCK_ADMIN_USER);
    await page.goto("/");

    const skipLink = page.locator('a[href="#main-content"]');
    await expect(skipLink).toBeAttached();
    await expect(skipLink).toHaveText("Skip to main content");

    const mainContent = page.locator("main#main-content");
    await expect(mainContent).toBeVisible();
  });

  test("mobile navigation works via Radix Sheet at 390x844", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await injectAuthSession(page, MOCK_ADMIN_USER);
    await page.goto("/");

    // Desktop sidebar hidden
    await expect(page.locator("aside")).toBeHidden();

    // Menu button visible
    const menuBtn = page.locator('button[aria-label="Open navigation"]');
    await expect(menuBtn).toBeVisible();
    await expect(menuBtn).toHaveAttribute("aria-controls", "mobile-navigation");
    await expect(menuBtn).toHaveAttribute("aria-expanded", "false");

    // 1. Open the mobile navigation
    await menuBtn.click();
    await expect(menuBtn).toHaveAttribute("aria-expanded", "true");

    // 2. Verify the open panel is exposed as a dialog
    const dialog = page.getByRole("dialog", { name: "Navigation Menu" });
    await expect(dialog).toBeVisible();

    // 3. Verify its accessible name is "Navigation Menu"
    const sheet = page.locator("#mobile-navigation");
    await expect(sheet).toHaveAttribute("role", "dialog");

    // 4. Verify an authorized navigation link has a rendered height of at least 44px
    const inventoryLink = sheet.locator('a[href="/inventory"]');
    await expect(inventoryLink).toBeVisible();
    const linkBox = await inventoryLink.boundingBox();
    expect(linkBox).not.toBeNull();
    expect(linkBox!.height).toBeGreaterThanOrEqual(44);

    // 5. Press Escape
    await page.keyboard.press("Escape");

    // 6. Verify the navigation Sheet is closed
    await expect(sheet).toBeHidden();

    // 7. Verify keyboard focus returns to the "Open navigation" button
    await expect(menuBtn).toBeFocused();

    // 8. Reopen the Sheet
    await menuBtn.click();
    await expect(sheet).toBeVisible();

    // 9. Select the Inventory route
    await sheet.locator('a[href="/inventory"]').click();

    // 10. Verify navigation succeeds
    await expect(page).toHaveURL(/.*\/inventory/);

    // 11. Verify the Sheet closes after route selection
    await expect(sheet).toBeHidden();

    // 12. Retain the horizontal-overflow check
    const hasHorizontalScroll = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    );
    expect(hasHorizontalScroll).toBe(false);
  });

  test("warehouse handheld viewport fits cleanly at 360x800", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await injectAuthSession(page, MOCK_ADMIN_USER);
    await page.goto("/");

    const menuBtn = page.locator('button[aria-label="Open navigation"]');
    await expect(menuBtn).toBeVisible();

    const searchInput = page.locator('input[aria-label="Search warehouse records"]');
    await expect(searchInput).toBeVisible();

    // Header does not overflow
    const hasHorizontalScroll = await page.evaluate(
      () => document.documentElement.scrollWidth > window.innerWidth,
    );
    expect(hasHorizontalScroll).toBe(false);
  });

  test("navigates cleanly between operational pages without errors", async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        consoleErrors.push(msg.text());
      }
    });

    await injectAuthSession(page, MOCK_ADMIN_USER);
    await page.goto("/");

    // 1. Inventory
    await page.locator('aside nav a[href="/inventory"]').click();
    await expect(page).toHaveURL(/.*\/inventory/);
    await expect(page.locator("h1")).toContainText(/Inventory|Balances/);

    // 2. Receipts
    await page.locator('aside nav a[href="/receipts"]').click();
    await expect(page).toHaveURL(/.*\/receipts/);
    await expect(page.locator("h1")).toContainText(/Receiving|Receipts/);

    // 3. Orders
    await page.locator('aside nav a[href="/orders"]').click();
    await expect(page).toHaveURL(/.*\/orders/);
    await expect(page.locator("h1")).toContainText(/Orders/);

    // 4. Transfers
    await page.locator('aside nav a[href="/transfers"]').click();
    await expect(page).toHaveURL(/.*\/transfers/);
    await expect(page.locator("h1")).toContainText(/Warehouse Transfers|Transfers/);

    // 5. Returns
    await page.locator('aside nav a[href="/returns"]').click();
    await expect(page).toHaveURL(/.*\/returns/);
    await expect(page.locator("h1")).toContainText(/Customer Returns|Returns/);

    // 6. Migration
    await page.locator('aside nav a[href="/migration"]').click();
    await expect(page).toHaveURL(/.*\/migration/);
    await expect(page.locator("h1")).toContainText(/Opening Inventory Migration/);

    // 7. AI Assistant
    await page.locator('aside nav a[href="/ai-assistant"]').click();
    await expect(page).toHaveURL(/.*\/ai-assistant/);
    await expect(page.locator("h1")).toContainText(/AI Assistant/);

    // 8. Admin Panel
    await page.locator('aside nav a[href="/admin"]').click();
    await expect(page).toHaveURL(/.*\/admin/);
    await expect(page.locator("h1")).toContainText(/Admin & Staff Hierarchy|Admin/);

    const hydrationErrors = consoleErrors.filter(
      (msg) =>
        msg.includes("Hydration failed") ||
        msg.includes("server rendered HTML didn't match") ||
        msg.includes("hydration mismatch"),
    );
    expect(hydrationErrors).toEqual([]);
  });
});
