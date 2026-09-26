import { test, expect } from "@playwright/test";
import { injectAuthSession, setupStandardApiMocks } from "./helpers/auth";

const MOBILE_VIEWPORT = { width: 360, height: 800 };
const DESKTOP_VIEWPORT = { width: 1280, height: 900 };

test.describe("Queue Controls — Transfers Queue", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(DESKTOP_VIEWPORT);
    await setupStandardApiMocks(page);
    await injectAuthSession(page);
  });

  test("Transfers: server pagination navigates between pages and updates controls", async ({ page }) => {
    await page.goto("/transfers");

    const paginationNav = page.getByRole("navigation", { name: "transfers pagination" });
    await expect(paginationNav).toBeVisible();

    const statusText = paginationNav.getByRole("status");
    await expect(statusText).toContainText("Showing 1–25 of 30 transfers");

    const prevButton = paginationNav.getByRole("button", { name: "Go to previous page of transfers" });
    const nextButton = paginationNav.getByRole("button", { name: "Go to next page of transfers" });

    await expect(prevButton).toBeDisabled();
    await expect(nextButton).toBeEnabled();

    // Verify first page contains TRN-2026-0001
    await expect(page.getByTestId("transfers-desktop-table").getByText("TRN-2026-0001")).toBeVisible();

    // Advance to page 2
    await nextButton.click();
    await expect(page).toHaveURL(/.*\/transfers.*page=2/);

    await expect(statusText).toContainText("Showing 26–30 of 30 transfers");
    await expect(prevButton).toBeEnabled();
    await expect(nextButton).toBeDisabled();

    // Verify page 2 contains TRN-2026-0026 and not TRN-2026-0001
    await expect(page.getByTestId("transfers-desktop-table").getByText("TRN-2026-0026")).toBeVisible();
    await expect(page.getByTestId("transfers-desktop-table").getByText("TRN-2026-0001")).toHaveCount(0);

    // Return to page 1
    await prevButton.click();
    await expect(statusText).toContainText("Showing 1–25 of 30 transfers");
    await expect(prevButton).toBeDisabled();
    await expect(nextButton).toBeEnabled();
  });

  test("Transfers: search reduces results to one item hiding pagination, and clearing restores pagination", async ({ page }) => {
    await page.goto("/transfers");

    // Initially 30 items: pagination is visible
    const paginationNav = page.getByRole("navigation", { name: "transfers pagination" });
    await expect(paginationNav).toBeVisible();
    await expect(paginationNav.getByRole("status")).toContainText("Showing 1–25 of 30 transfers");

    const searchInput = page.locator("#transfer-search");
    await searchInput.fill("TRN-2026-0003");

    await expect(page).toHaveURL(/.*\/transfers.*q=TRN-2026-0003/);
    await expect(page.getByTestId("transfers-desktop-table").getByText("TRN-2026-0003")).toBeVisible();

    // With only 1 item, pagination is absent
    await expect(page.getByRole("navigation", { name: "transfers pagination" })).toHaveCount(0);

    // Clear filters button resets state and restores pagination
    const clearButton = page.getByRole("button", { name: "Clear all filters" });
    await expect(clearButton).toBeVisible();
    await clearButton.click();

    await expect(page).toHaveURL(/.*\/transfers\/?$/);
    await expect(paginationNav).toBeVisible();
    await expect(paginationNav.getByRole("status")).toContainText("Showing 1–25 of 30 transfers");
  });

  test("Transfers: direct URL navigation survives and populates filters", async ({ page }) => {
    await page.goto("/transfers?q=TRN-2026-0002");

    const searchInput = page.locator("#transfer-search");
    await expect(searchInput).toHaveValue("TRN-2026-0002");
    await expect(page.getByTestId("transfers-desktop-table").getByText("TRN-2026-0002")).toBeVisible();

    // 1 item result: pagination absent
    await expect(page.getByRole("navigation", { name: "transfers pagination" })).toHaveCount(0);
  });

  test("Transfers: status options exactly cover the eight valid transfer statuses", async ({ page }) => {
    await page.goto("/transfers");

    const select = page.locator("#transfer-status-filter");
    await expect(select).toBeVisible();
    const options = select.locator("option");
    await expect(options).toHaveCount(9);

    const values = await options.evaluateAll((opts) => opts.map((o) => (o as HTMLOptionElement).value));
    const statusValues = values.filter(Boolean);

    expect(statusValues).toEqual([
      "DRAFT",
      "PENDING_APPROVAL",
      "APPROVED",
      "DISPATCHED",
      "PARTIALLY_RECEIVED",
      "RECEIVED",
      "DISCREPANCY_REVIEW",
      "CANCELLED",
    ]);
  });

  test("Transfers: direct navigation to an unknown status does not retain or send that status", async ({ page }) => {
    let sentStatus: string | null = null;
    page.on("request", (req) => {
      if (req.url().includes("/api/v1/transfers")) {
        const url = new URL(req.url());
        if (url.searchParams.has("status")) {
          sentStatus = url.searchParams.get("status");
        }
      }
    });

    await page.goto("/transfers?status=UNKNOWN_BOGUS_STATUS");

    // The unknown status should not be selected in the filter
    const statusSelect = page.locator("#transfer-status-filter");
    await expect(statusSelect).toHaveValue("");

    // The unknown status should not remain active in the URL
    await expect(page).not.toHaveURL(/status=UNKNOWN_BOGUS_STATUS/);

    // The API request should not have received the unknown status
    expect(sentStatus).toBeNull();
  });

  test("Transfers: direct navigation to page=99 normalizes to last valid page and displays truthful records and counts", async ({ page }) => {
    await page.goto("/transfers?page=99");

    // Normalized to last valid page (page 2 for 30 records at 25 per page)
    await expect(page).toHaveURL(/.*\/transfers.*page=2/);

    // Records from page 2 are displayed
    await expect(page.getByTestId("transfers-desktop-table").getByText("TRN-2026-0026")).toBeVisible();
    await expect(page.getByTestId("transfers-desktop-table").getByText("TRN-2026-0001")).toHaveCount(0);

    // Truthful pagination counts are shown, never impossible ranges like 2451–30
    const paginationNav = page.getByRole("navigation", { name: "transfers pagination" });
    await expect(paginationNav).toBeVisible();
    await expect(paginationNav.getByRole("status")).toContainText("Showing 26–30 of 30 transfers");
    await expect(paginationNav.getByText("Page 2 of 2")).toBeVisible();
  });

  test("Transfers: direct navigation to page=99 with zero records normalizes to page 1 without page parameter", async ({ page }) => {
    await page.goto("/transfers?page=99&q=NO_SUCH_TRANSFER_EXISTS");

    // Normalizes to page 1 with no page parameter, preserving search query
    await expect(page).toHaveURL(/.*\/transfers\?q=NO_SUCH_TRANSFER_EXISTS$/);
    await expect(page.getByText("No transfers match this search")).toBeVisible();
    await expect(page.getByRole("navigation", { name: "transfers pagination" })).toHaveCount(0);
  });

  test("Transfers: deliberate pagination creates browser history and Back button returns to page 1", async ({ page }) => {
    await page.goto("/transfers");

    const paginationNav = page.getByRole("navigation", { name: "transfers pagination" });
    await expect(paginationNav).toBeVisible();
    await expect(paginationNav.getByRole("status")).toContainText("Showing 1–25 of 30 transfers");

    const nextButton = paginationNav.getByRole("button", { name: "Go to next page of transfers" });
    await nextButton.click();

    await expect(page).toHaveURL(/.*\/transfers.*page=2/);
    await expect(paginationNav.getByRole("status")).toContainText("Showing 26–30 of 30 transfers");
    await expect(page.getByTestId("transfers-desktop-table").getByText("TRN-2026-0026")).toBeVisible();

    // Browser back returns to page 1
    await page.goBack();
    await expect(page).not.toHaveURL(/page=2/);
    await expect(paginationNav.getByRole("status")).toContainText("Showing 1–25 of 30 transfers");
    await expect(page.getByTestId("transfers-desktop-table").getByText("TRN-2026-0001")).toBeVisible();
  });

  test("Transfers: mobile handheld viewport stacks filters and allows pagination without horizontal overflow", async ({ page }) => {
    await page.setViewportSize(MOBILE_VIEWPORT);
    await page.goto("/transfers");

    await expect(page.getByTestId("transfers-mobile-list")).toBeVisible();
    await expect(page.getByTestId("transfers-desktop-table")).toBeHidden();

    const paginationNav = page.getByRole("navigation", { name: "transfers pagination" });
    await expect(paginationNav).toBeVisible();
    await expect(paginationNav.getByRole("status")).toContainText("Showing 1–25 of 30 transfers");

    const nextButton = paginationNav.getByRole("button", { name: "Go to next page of transfers" });
    await nextButton.click();
    await expect(paginationNav.getByRole("status")).toContainText("Showing 26–30 of 30 transfers");

    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(scrollWidth).toBeLessThanOrEqual(MOBILE_VIEWPORT.width);
  });
});

test.describe("Queue Controls — Returns Queue", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(DESKTOP_VIEWPORT);
    await setupStandardApiMocks(page);
    await injectAuthSession(page);
  });

  test("Returns: server pagination navigates between pages and updates controls", async ({ page }) => {
    await page.goto("/returns");

    const paginationNav = page.getByRole("navigation", { name: "returns pagination" });
    await expect(paginationNav).toBeVisible();

    const statusText = paginationNav.getByRole("status");
    await expect(statusText).toContainText("Showing 1–25 of 30 returns");

    const prevButton = paginationNav.getByRole("button", { name: "Go to previous page of returns" });
    const nextButton = paginationNav.getByRole("button", { name: "Go to next page of returns" });

    await expect(prevButton).toBeDisabled();
    await expect(nextButton).toBeEnabled();

    // Verify first page contains RMA-2026-0001
    await expect(page.getByTestId("returns-desktop-table").getByText("RMA-2026-0001")).toBeVisible();

    // Advance to page 2
    await nextButton.click();
    await expect(page).toHaveURL(/.*\/returns.*page=2/);

    await expect(statusText).toContainText("Showing 26–30 of 30 returns");
    await expect(prevButton).toBeEnabled();
    await expect(nextButton).toBeDisabled();

    // Verify page 2 contains RMA-2026-0026
    await expect(page.getByTestId("returns-desktop-table").getByText("RMA-2026-0026")).toBeVisible();
    await expect(page.getByTestId("returns-desktop-table").getByText("RMA-2026-0001")).toHaveCount(0);

    // Return to page 1
    await prevButton.click();
    await expect(statusText).toContainText("Showing 1–25 of 30 returns");
  });

  test("Returns: search reduces results to one item hiding pagination, and clearing restores pagination", async ({ page }) => {
    await page.goto("/returns");

    // Initially 30 items: pagination is visible
    const paginationNav = page.getByRole("navigation", { name: "returns pagination" });
    await expect(paginationNav).toBeVisible();
    await expect(paginationNav.getByRole("status")).toContainText("Showing 1–25 of 30 returns");

    const searchInput = page.locator("#return-search");
    await searchInput.fill("RMA-2026-0004");

    await expect(page).toHaveURL(/.*\/returns.*q=RMA-2026-0004/);
    await expect(page.getByTestId("returns-desktop-table").getByText("RMA-2026-0004")).toBeVisible();

    // With only 1 item, pagination is absent
    await expect(page.getByRole("navigation", { name: "returns pagination" })).toHaveCount(0);

    // Clear filters button resets state and restores pagination
    const clearButton = page.getByRole("button", { name: "Clear all filters" });
    await expect(clearButton).toBeVisible();
    await clearButton.click();

    await expect(page).toHaveURL(/.*\/returns\/?$/);
    await expect(paginationNav).toBeVisible();
    await expect(paginationNav.getByRole("status")).toContainText("Showing 1–25 of 30 returns");
  });

  test("Returns: direct URL navigation survives and populates filters", async ({ page }) => {
    await page.goto("/returns?q=RMA-2026-0003");

    const searchInput = page.locator("#return-search");
    await expect(searchInput).toHaveValue("RMA-2026-0003");
    await expect(page.getByTestId("returns-desktop-table").getByText("RMA-2026-0003")).toBeVisible();

    // 1 item result: pagination absent
    await expect(page.getByRole("navigation", { name: "returns pagination" })).toHaveCount(0);
  });

  test("Returns: status options exactly cover the seven valid return statuses and exclude CANCELLED", async ({ page }) => {
    await page.goto("/returns");

    const select = page.locator("#return-status-filter");
    await expect(select).toBeVisible();
    const options = select.locator("option");
    await expect(options).toHaveCount(8);

    const values = await options.evaluateAll((opts) => opts.map((o) => (o as HTMLOptionElement).value));
    const statusValues = values.filter(Boolean);

    expect(statusValues).toEqual([
      "EXPECTED",
      "RECEIVED",
      "INSPECTION",
      "PARTIALLY_DISPOSED",
      "COMPLETED",
      "REJECTED",
      "UNIDENTIFIED",
    ]);
    expect(values).not.toContain("CANCELLED");
  });

  test("Returns: direct navigation to an unknown status does not retain or send that status", async ({ page }) => {
    let sentStatus: string | null = null;
    page.on("request", (req) => {
      if (req.url().includes("/api/v1/returns")) {
        const url = new URL(req.url());
        if (url.searchParams.has("status")) {
          sentStatus = url.searchParams.get("status");
        }
      }
    });

    // CANCELLED is an invalid status for returns
    await page.goto("/returns?status=CANCELLED");

    // The invalid status should not be selected in the filter
    const statusSelect = page.locator("#return-status-filter");
    await expect(statusSelect).toHaveValue("");

    // The invalid status should not remain active in the URL
    await expect(page).not.toHaveURL(/status=CANCELLED/);

    // The API request should not have received the invalid status
    expect(sentStatus).toBeNull();
  });

  test("Returns: direct navigation to page=99 normalizes to last valid page and displays truthful records and counts", async ({ page }) => {
    await page.goto("/returns?page=99");

    // Normalized to last valid page (page 2 for 30 records at 25 per page)
    await expect(page).toHaveURL(/.*\/returns.*page=2/);

    // Records from page 2 are displayed
    await expect(page.getByTestId("returns-desktop-table").getByText("RMA-2026-0026")).toBeVisible();
    await expect(page.getByTestId("returns-desktop-table").getByText("RMA-2026-0001")).toHaveCount(0);

    // Truthful pagination counts are shown, never impossible ranges like 2451–30
    const paginationNav = page.getByRole("navigation", { name: "returns pagination" });
    await expect(paginationNav).toBeVisible();
    await expect(paginationNav.getByRole("status")).toContainText("Showing 26–30 of 30 returns");
    await expect(paginationNav.getByText("Page 2 of 2")).toBeVisible();
  });

  test("Returns: direct navigation to page=99 with zero records normalizes to page 1 without page parameter", async ({ page }) => {
    await page.goto("/returns?page=99&q=NO_SUCH_RETURN_EXISTS");

    // Normalizes to page 1 with no page parameter, preserving search query
    await expect(page).toHaveURL(/.*\/returns\?q=NO_SUCH_RETURN_EXISTS$/);
    await expect(page.getByText("No returns match this search")).toBeVisible();
    await expect(page.getByRole("navigation", { name: "returns pagination" })).toHaveCount(0);
  });

  test("Returns: deliberate pagination creates browser history and Back button returns to page 1", async ({ page }) => {
    await page.goto("/returns");

    const paginationNav = page.getByRole("navigation", { name: "returns pagination" });
    await expect(paginationNav).toBeVisible();
    await expect(paginationNav.getByRole("status")).toContainText("Showing 1–25 of 30 returns");

    const nextButton = paginationNav.getByRole("button", { name: "Go to next page of returns" });
    await nextButton.click();

    await expect(page).toHaveURL(/.*\/returns.*page=2/);
    await expect(paginationNav.getByRole("status")).toContainText("Showing 26–30 of 30 returns");
    await expect(page.getByTestId("returns-desktop-table").getByText("RMA-2026-0026")).toBeVisible();

    // Browser back returns to page 1
    await page.goBack();
    await expect(page).not.toHaveURL(/page=2/);
    await expect(paginationNav.getByRole("status")).toContainText("Showing 1–25 of 30 returns");
    await expect(page.getByTestId("returns-desktop-table").getByText("RMA-2026-0001")).toBeVisible();
  });

  test("Returns: mobile handheld viewport stacks filters and allows pagination without horizontal overflow", async ({ page }) => {
    await page.setViewportSize(MOBILE_VIEWPORT);
    await page.goto("/returns");

    await expect(page.getByTestId("returns-mobile-list")).toBeVisible();
    await expect(page.getByTestId("returns-desktop-table")).toBeHidden();

    const paginationNav = page.getByRole("navigation", { name: "returns pagination" });
    await expect(paginationNav).toBeVisible();
    await expect(paginationNav.getByRole("status")).toContainText("Showing 1–25 of 30 returns");

    const nextButton = paginationNav.getByRole("button", { name: "Go to next page of returns" });
    await nextButton.click();
    await expect(paginationNav.getByRole("status")).toContainText("Showing 26–30 of 30 returns");

    const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
    expect(scrollWidth).toBeLessThanOrEqual(MOBILE_VIEWPORT.width);
  });
});

test.describe("Queue Controls — Accessibility", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(DESKTOP_VIEWPORT);
    await setupStandardApiMocks(page);
    await injectAuthSession(page);
  });

  test("Transfers: filter controls and pagination have accessible names and labels", async ({ page }) => {
    await page.goto("/transfers");

    await expect(page.getByRole("searchbox", { name: "Search transfers" })).toBeVisible();
    await expect(page.getByRole("combobox", { name: "Filter by origin facility" })).toBeVisible();
    await expect(page.getByRole("combobox", { name: "Filter by destination facility" })).toBeVisible();
    await expect(page.getByRole("combobox", { name: "Filter by seller tenant" })).toBeVisible();
    await expect(page.getByRole("combobox", { name: "Filter by status" })).toBeVisible();

    const prevButton = page.getByRole("button", { name: "Go to previous page of transfers" });
    const nextButton = page.getByRole("button", { name: "Go to next page of transfers" });

    const prevBox = await prevButton.boundingBox();
    const nextBox = await nextButton.boundingBox();

    expect(prevBox?.height).toBeGreaterThanOrEqual(44);
    expect(nextBox?.height).toBeGreaterThanOrEqual(44);
  });

  test("Returns: filter controls and pagination have accessible names and labels", async ({ page }) => {
    await page.goto("/returns");

    await expect(page.getByRole("searchbox", { name: "Search returns" })).toBeVisible();
    await expect(page.getByRole("combobox", { name: "Filter by facility" })).toBeVisible();
    await expect(page.getByRole("combobox", { name: "Filter by seller tenant" })).toBeVisible();
    await expect(page.getByRole("combobox", { name: "Filter by status" })).toBeVisible();

    const prevButton = page.getByRole("button", { name: "Go to previous page of returns" });
    const nextButton = page.getByRole("button", { name: "Go to next page of returns" });

    const prevBox = await prevButton.boundingBox();
    const nextBox = await nextButton.boundingBox();

    expect(prevBox?.height).toBeGreaterThanOrEqual(44);
    expect(nextBox?.height).toBeGreaterThanOrEqual(44);
  });
});
