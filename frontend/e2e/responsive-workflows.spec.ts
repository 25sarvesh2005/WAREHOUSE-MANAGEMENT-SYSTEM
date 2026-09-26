import { test, expect } from "@playwright/test";
import { injectAuthSession, setupStandardApiMocks } from "./helpers/auth";

const MOBILE_VIEWPORT = { width: 360, height: 800 };
const DESKTOP_VIEWPORT = { width: 1280, height: 900 };

test.describe("Responsive Workflows — Mobile Handheld (360x800)", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(MOBILE_VIEWPORT);
    await setupStandardApiMocks(page);
    await injectAuthSession(page);
  });

  test("Orders: mobile card list is visible, desktop table is hidden, no horizontal overflow", async ({ page }) => {
    await page.goto("/orders");

    await expect(page.getByTestId("orders-mobile-list")).toBeVisible();
    await expect(page.getByTestId("orders-desktop-table")).toBeHidden();
    await expect(page.getByTestId("orders-mobile-list").getByText("ORD-2026-0001")).toBeVisible();

    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(scrollWidth).toBeLessThanOrEqual(MOBILE_VIEWPORT.width);
  });

  test("Inventory: balance cards and movement wrapper render responsively without horizontal overflow", async ({ page }) => {
    await page.goto("/inventory");

    await expect(page.getByTestId("inventory-balances-mobile-list")).toBeVisible();
    await expect(page.getByTestId("inventory-balances-desktop-table")).toBeHidden();
    await expect(page.getByTestId("inventory-balances-mobile-list").getByText("SKU-TEST-001")).toBeVisible();

    // With standard mock, movements is empty; verify empty state is visible
    await expect(page.getByText("No ledger movements recorded yet")).toBeVisible();
    await expect(page.getByTestId("inventory-movements-desktop-table")).toBeHidden();

    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(scrollWidth).toBeLessThanOrEqual(MOBILE_VIEWPORT.width);
  });

  test("Pick Tasks: mobile card list is visible, desktop table is hidden, no horizontal overflow", async ({ page }) => {
    await page.goto("/pick-tasks");

    await expect(page.getByTestId("pick-tasks-mobile-list")).toBeVisible();
    await expect(page.getByTestId("pick-tasks-desktop-table")).toBeHidden();
    await expect(page.getByTestId("pick-tasks-mobile-list").getByText("TASK-00000000")).toBeVisible();

    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(scrollWidth).toBeLessThanOrEqual(MOBILE_VIEWPORT.width);
  });

  test("Shipments: mobile card list is visible, desktop table is hidden, no horizontal overflow", async ({ page }) => {
    await page.goto("/shipments");

    await expect(page.getByTestId("shipments-mobile-list")).toBeVisible();
    await expect(page.getByTestId("shipments-desktop-table")).toBeHidden();
    await expect(page.getByTestId("shipments-mobile-list").getByText("SHIP-00000000")).toBeVisible();

    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(scrollWidth).toBeLessThanOrEqual(MOBILE_VIEWPORT.width);
  });

  test("Receipts: mobile card list is visible, desktop table is hidden, no horizontal overflow", async ({ page }) => {
    await page.goto("/receipts");

    await expect(page.getByTestId("receipts-mobile-list")).toBeVisible();
    await expect(page.getByTestId("receipts-desktop-table")).toBeHidden();
    await expect(page.getByTestId("receipts-mobile-list").getByText("REC-2026-0001")).toBeVisible();

    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(scrollWidth).toBeLessThanOrEqual(MOBILE_VIEWPORT.width);
  });

  test("Returns: mobile card list is visible, desktop table is hidden, no horizontal overflow", async ({ page }) => {
    await page.goto("/returns");

    await expect(page.getByTestId("returns-mobile-list")).toBeVisible();
    await expect(page.getByTestId("returns-desktop-table")).toBeHidden();
    await expect(page.getByTestId("returns-mobile-list").getByText("RMA-2026-0001")).toBeVisible();

    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(scrollWidth).toBeLessThanOrEqual(MOBILE_VIEWPORT.width);
  });

  test("Transfers: mobile card list is visible, desktop table is hidden, no horizontal overflow", async ({ page }) => {
    await page.goto("/transfers");

    await expect(page.getByTestId("transfers-mobile-list")).toBeVisible();
    await expect(page.getByTestId("transfers-desktop-table")).toBeHidden();
    await expect(page.getByTestId("transfers-mobile-list").getByText("TRN-2026-0001")).toBeVisible();

    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(scrollWidth).toBeLessThanOrEqual(MOBILE_VIEWPORT.width);
  });
});

test.describe("Responsive Workflows — Mobile Actions", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(MOBILE_VIEWPORT);
    await setupStandardApiMocks(page);
    await injectAuthSession(page);
  });

  test("Orders: clicking 'View order' exposes selected-order detail panel", async ({ page }) => {
    await page.goto("/orders");

    const viewButton = page.getByTestId("orders-mobile-list").getByRole("button", { name: "View order" }).first();
    await expect(viewButton).toBeVisible();
    await viewButton.click();

    await expect(page.getByText("Selected Order")).toBeVisible();
    await expect(page.getByRole("heading", { name: /ORD-2026-0001/ })).toBeVisible();
  });

  test("Pick Tasks: clicking 'Pick lines' exposes active pick-station panel", async ({ page }) => {
    await page.goto("/pick-tasks");

    const pickLinesButton = page.getByTestId("pick-tasks-mobile-list").getByRole("button", { name: "Pick lines" }).first();
    await expect(pickLinesButton).toBeVisible();
    await pickLinesButton.click();

    await expect(page.getByText("Active Floor Pick Station")).toBeVisible();
    await expect(page.getByText("Pick Verification Items")).toBeVisible();
  });

  test("Receipts: mobile detail link has correct destination", async ({ page }) => {
    await page.goto("/receipts");

    const detailLink = page.getByTestId("receipts-mobile-list").getByRole("link", { name: /Scan Line Items|View Details/ }).first();
    await expect(detailLink).toBeVisible();
    await expect(detailLink).toHaveAttribute("href", "/receipts/00000000-0000-0000-0000-000000000010");
  });

  test("Returns: mobile detail link has correct destination", async ({ page }) => {
    await page.goto("/returns");

    const detailLink = page.getByTestId("returns-mobile-list").getByRole("link", { name: "Inspect & Dispose" }).first();
    await expect(detailLink).toBeVisible();
    await expect(detailLink).toHaveAttribute("href", "/returns/00000000-0000-0000-0000-000000000060");
  });

  test("Transfers: permitted action button is visible and has minimum 44px height", async ({ page }) => {
    // Override standard mock to provide an actionable transfer (APPROVED -> Dispatch)
    await page.route(/\/api\/v1\/transfers/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          total: 1,
          items: [
            {
              id: "00000000-0000-0000-0000-000000000050",
              transfer_number: "TRN-2026-0001",
              origin_warehouse_code: "RENO",
              origin_warehouse_id: "00000000-0000-0000-0000-000000000002",
              destination_warehouse_code: "DAL",
              destination_warehouse_id: "00000000-0000-0000-0000-000000000003",
              seller_id: "00000000-0000-0000-0000-000000000004",
              status: "APPROVED",
              lines: [],
              created_at: new Date().toISOString(),
            },
          ],
        }),
      });
    });

    await page.goto("/transfers");
    const dispatchButton = page.getByTestId("transfers-mobile-list").getByRole("button", { name: "Dispatch" });
    await expect(dispatchButton).toBeVisible();

    const box = await dispatchButton.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.height).toBeGreaterThanOrEqual(44);
  });

  test("Shipments and inventory do not receive invented row actions", async ({ page }) => {
    await page.goto("/shipments");
    await expect(page.getByTestId("shipments-mobile-list")).toBeVisible();
    await expect(page.getByTestId("shipments-mobile-list").getByRole("button")).toHaveCount(0);
    await expect(page.getByTestId("shipments-mobile-list").getByRole("link")).toHaveCount(0);

    await page.goto("/inventory");
    await expect(page.getByTestId("inventory-balances-mobile-list")).toBeVisible();
    await expect(page.getByTestId("inventory-balances-mobile-list").getByRole("button")).toHaveCount(0);
    await expect(page.getByTestId("inventory-balances-mobile-list").getByRole("link")).toHaveCount(0);
  });
});

test.describe("Responsive Workflows — Desktop Tables Preservation (1280x900)", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(DESKTOP_VIEWPORT);
    await setupStandardApiMocks(page);
    await injectAuthSession(page);
  });

  test("Orders: desktop table visible with headings, mobile list hidden", async ({ page }) => {
    await page.goto("/orders");

    await expect(page.getByTestId("orders-desktop-table")).toBeVisible();
    await expect(page.getByTestId("orders-mobile-list")).toBeHidden();
    await expect(page.getByRole("columnheader", { name: "Order Number" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Customer Destination" })).toBeVisible();
    await expect(page.getByTestId("orders-desktop-table").getByText("ORD-2026-0001")).toBeVisible();
  });

  test("Inventory: desktop tables visible with headings, mobile lists hidden", async ({ page }) => {
    await page.goto("/inventory");

    await expect(page.getByTestId("inventory-balances-desktop-table")).toBeVisible();
    await expect(page.getByTestId("inventory-balances-mobile-list")).toBeHidden();
    await expect(page.getByRole("columnheader", { name: "Product SKU" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Warehouse Facility" })).toBeVisible();
    await expect(page.getByTestId("inventory-balances-desktop-table").getByText("SKU-TEST-001")).toBeVisible();
  });

  test("Pick Tasks: desktop table visible with headings, mobile list hidden", async ({ page }) => {
    await page.goto("/pick-tasks");

    await expect(page.getByTestId("pick-tasks-desktop-table")).toBeVisible();
    await expect(page.getByTestId("pick-tasks-mobile-list")).toBeHidden();
    await expect(page.getByRole("columnheader", { name: "Pick Task ID" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Order Reference" })).toBeVisible();
    await expect(page.getByTestId("pick-tasks-desktop-table").getByText("TASK-00000000")).toBeVisible();
  });

  test("Shipments: desktop table visible with headings, mobile list hidden", async ({ page }) => {
    await page.goto("/shipments");

    await expect(page.getByTestId("shipments-desktop-table")).toBeVisible();
    await expect(page.getByTestId("shipments-mobile-list")).toBeHidden();
    await expect(page.getByRole("columnheader", { name: "Shipment ID" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Carrier" })).toBeVisible();
    await expect(page.getByTestId("shipments-desktop-table").getByText("SHIP-00000000")).toBeVisible();
  });

  test("Receipts: desktop table visible with headings, mobile list hidden", async ({ page }) => {
    await page.goto("/receipts");

    await expect(page.getByTestId("receipts-desktop-table")).toBeVisible();
    await expect(page.getByTestId("receipts-mobile-list")).toBeHidden();
    await expect(page.getByRole("columnheader", { name: "Receipt Reference" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Warehouse Dock" })).toBeVisible();
    await expect(page.getByTestId("receipts-desktop-table").getByText("REC-2026-0001")).toBeVisible();
  });

  test("Returns: desktop table visible with headings, mobile list hidden", async ({ page }) => {
    await page.goto("/returns");

    await expect(page.getByTestId("returns-desktop-table")).toBeVisible();
    await expect(page.getByTestId("returns-mobile-list")).toBeHidden();
    await expect(page.getByRole("columnheader", { name: "RMA / Return ID" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Facility" })).toBeVisible();
    await expect(page.getByTestId("returns-desktop-table").getByText("RMA-2026-0001")).toBeVisible();
  });

  test("Transfers: desktop table visible with headings, mobile list hidden", async ({ page }) => {
    await page.goto("/transfers");

    await expect(page.getByTestId("transfers-desktop-table")).toBeVisible();
    await expect(page.getByTestId("transfers-mobile-list")).toBeHidden();
    await expect(page.getByRole("columnheader", { name: "Transfer ID" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Route" })).toBeVisible();
    await expect(page.getByTestId("transfers-desktop-table").getByText("TRN-2026-0001")).toBeVisible();
  });
});

test.describe("Responsive Workflows — Filter and Control Layout (360px)", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(MOBILE_VIEWPORT);
    await setupStandardApiMocks(page);
    await injectAuthSession(page);
  });

  test("Orders: search and sort stay inside viewport", async ({ page }) => {
    await page.goto("/orders");

    const searchInput = page.locator("input[placeholder*='Search order']");
    await expect(searchInput).toBeVisible();
    const searchBox = await searchInput.boundingBox();
    expect(searchBox).not.toBeNull();
    expect(searchBox!.x + searchBox!.width).toBeLessThanOrEqual(MOBILE_VIEWPORT.width);

    const sortSelect = page.locator("select:has(option[value='priority'])");
    await expect(sortSelect).toBeVisible();
    const sortBox = await sortSelect.boundingBox();
    expect(sortBox).not.toBeNull();
    expect(sortBox!.x + sortBox!.width).toBeLessThanOrEqual(MOBILE_VIEWPORT.width);
  });

  test("Inventory: search, facility, seller, and state filters stay inside viewport", async ({ page }) => {
    await page.goto("/inventory");

    const searchInput = page.locator("input[placeholder*='Scan barcode']");
    await expect(searchInput).toBeVisible();
    const searchBox = await searchInput.boundingBox();
    expect(searchBox).not.toBeNull();
    expect(searchBox!.x + searchBox!.width).toBeLessThanOrEqual(MOBILE_VIEWPORT.width);

    const facilitySelect = page.locator("select:has(option[value='ALL'])").first();
    await expect(facilitySelect).toBeVisible();
    const facilityBox = await facilitySelect.boundingBox();
    expect(facilityBox).not.toBeNull();
    expect(facilityBox!.x).toBeGreaterThanOrEqual(0);
    expect(facilityBox!.x + facilityBox!.width).toBeLessThanOrEqual(MOBILE_VIEWPORT.width);
    expect(facilityBox!.height).toBeGreaterThanOrEqual(44);

    const sellerSelect = page.getByLabel("Seller:");
    await expect(sellerSelect).toBeVisible();
    const sellerBox = await sellerSelect.boundingBox();
    expect(sellerBox).not.toBeNull();
    expect(sellerBox!.x).toBeGreaterThanOrEqual(0);
    expect(sellerBox!.x + sellerBox!.width).toBeLessThanOrEqual(
      MOBILE_VIEWPORT.width,
    );
    expect(sellerBox!.height).toBeGreaterThanOrEqual(44);

    const stateFilterButton = page.locator("button:has-text('AVAILABLE')");
    await expect(stateFilterButton).toBeVisible();
    const stateBox = await stateFilterButton.boundingBox();
    expect(stateBox).not.toBeNull();
    expect(stateBox!.x).toBeGreaterThanOrEqual(0);
    expect(stateBox!.x + stateBox!.width).toBeLessThanOrEqual(MOBILE_VIEWPORT.width);
    expect(stateBox!.height).toBeGreaterThanOrEqual(44);
  });

  test("Receipts: PageHeader actions and search stay inside viewport", async ({ page }) => {
    await page.goto("/receipts");

    const voiceButton = page.getByRole("button", { name: "Voice AI Intake" });
    await expect(voiceButton).toBeVisible();
    const voiceBox = await voiceButton.boundingBox();
    expect(voiceBox).not.toBeNull();
    expect(voiceBox!.x + voiceBox!.width).toBeLessThanOrEqual(MOBILE_VIEWPORT.width);

    const newReceiptButton = page.getByRole("button", { name: "New Inbound Receipt" });
    await expect(newReceiptButton).toBeVisible();
    const newReceiptBox = await newReceiptButton.boundingBox();
    expect(newReceiptBox).not.toBeNull();
    expect(newReceiptBox!.x + newReceiptBox!.width).toBeLessThanOrEqual(MOBILE_VIEWPORT.width);

    const searchInput = page.locator("input[placeholder*='Scan tracking']");
    await expect(searchInput).toBeVisible();
    const searchBox = await searchInput.boundingBox();
    expect(searchBox).not.toBeNull();
    expect(searchBox!.x + searchBox!.width).toBeLessThanOrEqual(MOBILE_VIEWPORT.width);
  });

  test("Transfers, returns, and shipments search inputs stay inside viewport", async ({ page }) => {
    await page.goto("/transfers");
    const transferSearch = page.locator("#transfer-search");
    await expect(transferSearch).toBeVisible();
    const transferBox = await transferSearch.boundingBox();
    expect(transferBox).not.toBeNull();
    expect(transferBox!.x + transferBox!.width).toBeLessThanOrEqual(MOBILE_VIEWPORT.width);

    await page.goto("/returns");
    const returnSearch = page.locator("#return-search");
    await expect(returnSearch).toBeVisible();
    const returnBox = await returnSearch.boundingBox();
    expect(returnBox).not.toBeNull();
    expect(returnBox!.x + returnBox!.width).toBeLessThanOrEqual(MOBILE_VIEWPORT.width);

    await page.goto("/shipments");
    const shipmentSearch = page.locator("input[placeholder*='Search carrier tracking']");
    await expect(shipmentSearch).toBeVisible();
    const shipmentBox = await shipmentSearch.boundingBox();
    expect(shipmentBox).not.toBeNull();
    expect(shipmentBox!.x + shipmentBox!.width).toBeLessThanOrEqual(MOBILE_VIEWPORT.width);
  });
});
