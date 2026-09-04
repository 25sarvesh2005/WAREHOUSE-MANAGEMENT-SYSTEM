import { test, expect } from "@playwright/test";
import {
  clearAuthSession,
  injectAuthSession,
  MOCK_ADMIN_USER,
  setupStandardApiMocks,
} from "./helpers/auth";

test.describe("Operational Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await clearAuthSession(page);
    await setupStandardApiMocks(page);
  });

  test("Test A — Manager data is truthful", async ({ page }) => {
    await injectAuthSession(page, MOCK_ADMIN_USER);
    await page.goto("/");

    const main = page.locator("main");

    // Heading, identity and formatted role
    await expect(main.getByText("Operations overview")).toBeVisible();
    await expect(main.getByRole("heading", { name: /Welcome back, System/i })).toBeVisible();
    await expect(main.getByText("Signed in as Administrator")).toBeVisible();

    // "Needs attention" must appear before "Open work"
    const needsAttentionHeading = main.getByRole("heading", { name: "Needs attention" });
    const openWorkHeading = main.getByRole("heading", { name: "Open work" });
    await expect(needsAttentionHeading).toBeVisible();
    await expect(openWorkHeading).toBeVisible();

    const attentionBox = await needsAttentionHeading.boundingBox();
    const workBox = await openWorkHeading.boundingBox();
    expect(attentionBox).not.toBeNull();
    expect(workBox).not.toBeNull();
    expect(attentionBox!.y).toBeLessThan(workBox!.y);

    // Verify all three exception counts equal 1
    const shortPickCard = main.locator('a[href="/pick-tasks"]', { hasText: "Short-pick exceptions" });
    await expect(shortPickCard).toBeVisible();
    await expect(shortPickCard).toContainText("1");

    const transferDiscrepancyCard = main.locator('a[href="/transfers"]', { hasText: "Transfer discrepancies" });
    await expect(transferDiscrepancyCard).toBeVisible();
    await expect(transferDiscrepancyCard).toContainText("1");

    const unidentifiedReturnCard = main.locator('a[href="/returns"]', { hasText: "Unidentified returns" });
    await expect(unidentifiedReturnCard).toBeVisible();
    await expect(unidentifiedReturnCard).toContainText("1");

    // Nonzero exception data does not show the empty-success message
    await expect(main.getByText("No active manager exceptions were reported.")).toHaveCount(0);

    // Verify open-work values are 3, 4, 2, and 1
    const openReceiptsCard = main.locator('a[href="/receipts"]', { hasText: "Open receipts" });
    await expect(openReceiptsCard).toBeVisible();
    await expect(openReceiptsCard).toContainText("3");

    const pendingPicksCard = main.locator('a[href="/pick-tasks"]', { hasText: "Pending pick tasks" });
    await expect(pendingPicksCard).toBeVisible();
    await expect(pendingPicksCard).toContainText("4");

    const activeTransfersCard = main.locator('a[href="/transfers"]', { hasText: "Active transfers" });
    await expect(activeTransfersCard).toBeVisible();
    await expect(activeTransfersCard).toContainText("2");

    const uninspectedReturnsCard = main.locator('a[href="/returns"]', { hasText: "Returns awaiting inspection" });
    await expect(uninspectedReturnsCard).toBeVisible();
    await expect(uninspectedReturnsCard).toContainText("1");

    // Verify inventory values
    const availableCard = main.locator('a[href="/inventory"]', { hasText: "Available" });
    await expect(availableCard).toBeVisible();
    await expect(availableCard).toContainText("12,500");

    const reservedCard = main.locator('a[href="/inventory"]', { hasText: "Reserved" });
    await expect(reservedCard).toBeVisible();
    await expect(reservedCard).toContainText("860");

    const controlledCard = main.locator('a[href="/inventory"]', { hasText: "Controlled" });
    await expect(controlledCard).toBeVisible();
    await expect(controlledCard).toContainText("25");

    const inTransitCard = main.locator('a[href="/inventory"]', { hasText: "In transit" });
    await expect(inTransitCard).toBeVisible();
    await expect(inTransitCard).toContainText("240");

    // Verify links lead to their specified routes
    await expect(shortPickCard).toHaveAttribute("href", "/pick-tasks");
    await expect(transferDiscrepancyCard).toHaveAttribute("href", "/transfers");
    await expect(unidentifiedReturnCard).toHaveAttribute("href", "/returns");
    await expect(openReceiptsCard).toHaveAttribute("href", "/receipts");
    await expect(pendingPicksCard).toHaveAttribute("href", "/pick-tasks");
    await expect(activeTransfersCard).toHaveAttribute("href", "/transfers");
    await expect(uninspectedReturnsCard).toHaveAttribute("href", "/returns");
    await expect(availableCard).toHaveAttribute("href", "/inventory");
    await expect(reservedCard).toHaveAttribute("href", "/inventory");
    await expect(controlledCard).toHaveAttribute("href", "/inventory");
    await expect(inTransitCard).toHaveAttribute("href", "/inventory");

    // Verify old claims and fake wording are absent
    await expect(main.getByText(/bicoastal/i)).toHaveCount(0);
    await expect(main.getByText(/reno/i)).toHaveCount(0);
    await expect(main.getByText(/columbus/i)).toHaveCount(0);
    await expect(main.getByText(/command center/i)).toHaveCount(0);
    await expect(main.getByText(/live real-time/i)).toHaveCount(0);
    await expect(main.getByText(/real-time/i)).toHaveCount(0);
    await expect(main.getByText(/100%/i)).toHaveCount(0);
    await expect(main.getByText(/sla/i)).toHaveCount(0);
    await expect(main.getByText(/uptime/i)).toHaveCount(0);
    await expect(main.getByText(/option board/i)).toHaveCount(0);
  });

  test("Test B — Initial loading is not a fake zero state and zero exceptions show cards with empty notice", async ({
    page,
  }) => {
    let resolveDashboard!: () => void;
    const dashboardPromise = new Promise<void>((resolve) => {
      resolveDashboard = resolve;
    });

    let resolveExceptions!: () => void;
    const exceptionsPromise = new Promise<void>((resolve) => {
      resolveExceptions = resolve;
    });

    await page.route(/\/api\/v1\/manager\/dashboard/, async (route) => {
      await dashboardPromise;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          balances_by_state: { AVAILABLE: 100 },
          open_receipts_count: 5,
          pending_pick_tasks_count: 2,
          active_transfers_count: 1,
          uninspected_returns_count: 0,
        }),
      });
    });

    await page.route(/\/api\/v1\/manager\/exceptions/, async (route) => {
      await exceptionsPromise;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          short_pick_exceptions: [],
          transfer_discrepancies: [],
          unidentified_returns: [],
        }),
      });
    });

    await injectAuthSession(page, MOCK_ADMIN_USER);
    await page.goto("/");

    const main = page.locator("main");

    // Before releasing responses: verify Loading operational overview...
    await expect(main.getByText("Loading operational overview...")).toBeVisible();

    // Verify manager metric groups and cards are not shown while loading
    await expect(main.getByRole("heading", { name: "Needs attention" })).toHaveCount(0);
    await expect(main.getByRole("heading", { name: "Open work" })).toHaveCount(0);
    await expect(main.getByRole("heading", { name: "Inventory by state" })).toHaveCount(0);
    await expect(main.getByText("Short-pick exceptions")).toHaveCount(0);
    await expect(main.getByText("Transfer discrepancies")).toHaveCount(0);
    await expect(main.getByText("Unidentified returns")).toHaveCount(0);

    // Verify no empty-success message is shown while loading
    await expect(main.getByText("No active manager exceptions were reported.")).toHaveCount(0);

    // Release the routes
    resolveDashboard();
    resolveExceptions();

    // Verify real data appears afterward
    await expect(main.getByRole("heading", { name: "Needs attention" })).toBeVisible();
    await expect(main.getByRole("heading", { name: "Open work" })).toBeVisible();
    await expect(main.getByRole("heading", { name: "Inventory by state" })).toBeVisible();
    await expect(main.getByText("Loading operational overview...")).toHaveCount(0);

    // Zero-exception success shows all three category cards with 0
    const shortPickCard = main.locator('a[href="/pick-tasks"]', { hasText: "Short-pick exceptions" });
    await expect(shortPickCard).toBeVisible();
    await expect(shortPickCard).toContainText("0");

    const transferDiscrepancyCard = main.locator('a[href="/transfers"]', { hasText: "Transfer discrepancies" });
    await expect(transferDiscrepancyCard).toBeVisible();
    await expect(transferDiscrepancyCard).toContainText("0");

    const unidentifiedReturnCard = main.locator('a[href="/returns"]', { hasText: "Unidentified returns" });
    await expect(unidentifiedReturnCard).toBeVisible();
    await expect(unidentifiedReturnCard).toContainText("0");

    // Zero-exception success additionally shows the empty-success message
    await expect(main.getByText("No active manager exceptions were reported.")).toBeVisible();
  });

  test("Test C — Error and retry with default React Query retries", async ({ page }) => {
    let dashboardRequestCount = 0;
    let allowSuccessfulResponse = false;

    await page.route(/\/api\/v1\/manager\/dashboard/, async (route) => {
      dashboardRequestCount++;
      if (!allowSuccessfulResponse) {
        await route.fulfill({
          status: 500,
          contentType: "application/json",
          body: JSON.stringify({ detail: "Database connection failed unexpectedly in internal cluster worker." }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            balances_by_state: {
              AVAILABLE: 12500,
              RESERVED: 860,
              DAMAGED: 12,
              QUARANTINED: 8,
              RETURN_INSPECTION: 5,
              IN_TRANSIT: 240,
            },
            open_receipts_count: 3,
            pending_pick_tasks_count: 4,
            active_transfers_count: 2,
            uninspected_returns_count: 1,
          }),
        });
      }
    });

    await injectAuthSession(page, MOCK_ADMIN_USER);
    await page.goto("/");

    const main = page.locator("main");

    // Wait using a web-first assertion until the safe dashboard error appears
    // (default React Query retries before settling into error)
    await expect(main.getByText("The operational overview could not be loaded.")).toBeVisible({
      timeout: 15000,
    });

    // Default retry behavior is not disabled: automatic retries finished before error state settled
    expect(dashboardRequestCount).toBeGreaterThan(1);

    // Verify raw server text is not visible
    await expect(main.getByText(/Database connection failed unexpectedly/i)).toHaveCount(0);

    // Verify Retry button is present
    const retryButton = main.getByRole("button", { name: "Retry" });
    await expect(retryButton).toBeVisible();

    // Set the flag to true and click the visible Retry button
    allowSuccessfulResponse = true;
    const countBeforeManualRetry = dashboardRequestCount;
    await retryButton.click();

    // Verify successful dashboard data appears after manual retry
    await expect(main.getByRole("heading", { name: "Open work" })).toBeVisible();
    await expect(main.getByText("The operational overview could not be loaded.")).toHaveCount(0);
    expect(dashboardRequestCount).toBeGreaterThan(countBeforeManualRetry);
  });

  test("Static scan — Dashboard does not mutate global query configuration", async () => {
    const fs = await import("node:fs");
    const path = await import("node:path");
    const { fileURLToPath } = await import("node:url");
    const currentDir = path.dirname(fileURLToPath(import.meta.url));
    const dashboardSource = fs.readFileSync(
      path.resolve(currentDir, "../src/components/Dashboard.tsx"),
      "utf-8",
    );

    expect(dashboardSource).not.toContain("useQueryClient");
    expect(dashboardSource).not.toContain("setQueryDefaults");
  });

  test("Test D — Seller permissions and request safety", async ({ page }) => {
    let managerDashboardCalls = 0;
    let managerExceptionsCalls = 0;

    page.on("request", (req) => {
      if (req.url().includes("/api/v1/manager/dashboard")) {
        managerDashboardCalls++;
      }
      if (req.url().includes("/api/v1/manager/exceptions")) {
        managerExceptionsCalls++;
      }
    });

    const sellerUser = {
      ...MOCK_ADMIN_USER,
      id: "00000000-0000-0000-0000-000000000099",
      email: "seller@whitfield.local",
      name: "Apex Seller",
      role: "SELLER" as const,
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

    const main = page.locator("main");

    // Header check
    await expect(main.getByText("Operations overview")).toBeVisible();
    await expect(main.getByText("Signed in as Seller")).toBeVisible();

    // Verify neither manager endpoint was requested
    expect(managerDashboardCalls).toBe(0);
    expect(managerExceptionsCalls).toBe(0);

    // Section-scoped locator for dashboard workflows
    const workflowSection = main.locator("section", {
      has: page.getByRole("heading", { name: "Available workflows" }),
    });

    // Seller sees Inventory, Orders, Shipments, and Returns workflows
    await expect(workflowSection.locator('a[href="/inventory"]')).toBeVisible();
    await expect(workflowSection.locator('a[href="/orders"]')).toBeVisible();
    await expect(workflowSection.locator('a[href="/shipments"]')).toBeVisible();
    await expect(workflowSection.locator('a[href="/returns"]')).toBeVisible();

    // Seller does not see Receipts, Pick tasks, Migration, Admin, or manager exception queues
    await expect(workflowSection.locator('a[href="/receipts"]')).toHaveCount(0);
    await expect(workflowSection.locator('a[href="/pick-tasks"]')).toHaveCount(0);
    await expect(workflowSection.locator('a[href="/migration"]')).toHaveCount(0);
    await expect(workflowSection.locator('a[href="/admin"]')).toHaveCount(0);
    await expect(main.getByRole("heading", { name: "Needs attention" })).toHaveCount(0);
    await expect(main.getByRole("heading", { name: "Open work" })).toHaveCount(0);
    await expect(main.getByRole("heading", { name: "Inventory by state" })).toHaveCount(0);
  });

  test("Test E — Receiver or Picker permissions", async ({ page }) => {
    let managerDashboardCalls = 0;
    let managerExceptionsCalls = 0;

    page.on("request", (req) => {
      if (req.url().includes("/api/v1/manager/dashboard")) {
        managerDashboardCalls++;
      }
      if (req.url().includes("/api/v1/manager/exceptions")) {
        managerExceptionsCalls++;
      }
    });

    const receiverUser = {
      ...MOCK_ADMIN_USER,
      id: "00000000-0000-0000-0000-000000000098",
      email: "receiver@whitfield.local",
      name: "Riley Receiver",
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

    const main = page.locator("main");
    await expect(main.getByText("Signed in as Receiver")).toBeVisible();

    expect(managerDashboardCalls).toBe(0);
    expect(managerExceptionsCalls).toBe(0);

    const workflowSection = main.locator("section", {
      has: page.getByRole("heading", { name: "Available workflows" }),
    });

    // Receiver sees receipts, inventory, returns
    await expect(workflowSection.locator('a[href="/receipts"]')).toBeVisible();
    await expect(workflowSection.locator('a[href="/inventory"]')).toBeVisible();
    await expect(workflowSection.locator('a[href="/returns"]')).toBeVisible();

    // Receiver does not see orders, pick tasks, shipments, admin, migration
    await expect(workflowSection.locator('a[href="/orders"]')).toHaveCount(0);
    await expect(workflowSection.locator('a[href="/pick-tasks"]')).toHaveCount(0);
    await expect(workflowSection.locator('a[href="/shipments"]')).toHaveCount(0);
    await expect(workflowSection.locator('a[href="/admin"]')).toHaveCount(0);
    await expect(workflowSection.locator('a[href="/migration"]')).toHaveCount(0);
    await expect(main.getByRole("heading", { name: "Needs attention" })).toHaveCount(0);
  });

  test("Test F — Mobile layout at 360px viewport", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await injectAuthSession(page, MOCK_ADMIN_USER);
    await page.goto("/");

    const main = page.locator("main");
    const heading = main.getByRole("heading", { name: /Welcome back/i });
    await expect(heading).toBeVisible();

    // Verify no document-level horizontal overflow
    const hasNoOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    );
    expect(hasNoOverflow).toBe(true);

    // Primary content is usable
    await expect(main.getByRole("heading", { name: "Needs attention" })).toBeVisible();
    await expect(main.getByRole("heading", { name: "Open work" })).toBeVisible();

    // Metric and workflow cards stay within the 360px viewport width
    const cards = main.locator("section a");
    const count = await cards.count();
    expect(count).toBeGreaterThan(0);

    for (let i = 0; i < Math.min(count, 5); i++) {
      const box = await cards.nth(i).boundingBox();
      expect(box).not.toBeNull();
      expect(box!.x).toBeGreaterThanOrEqual(0);
      expect(box!.x + box!.width).toBeLessThanOrEqual(360);
    }
  });
});
