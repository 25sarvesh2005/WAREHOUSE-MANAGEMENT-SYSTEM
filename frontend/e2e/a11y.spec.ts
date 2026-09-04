import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { injectAuthSession, setupStandardApiMocks } from "./helpers/auth";

const AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

interface ViolationSummary {
  id: string;
  impact: string;
  help: string;
  helpUrl: string;
  nodes: {
    target: string[];
    html: string;
  }[];
}

async function assertNoA11yViolations(page: Page, routeLabel: string): Promise<void> {
  const axeResults = await new AxeBuilder({ page })
    .withTags(AXE_TAGS)
    .disableRules(["color-contrast"])
    .analyze();

  const significantViolations = axeResults.violations.filter(
    (v) => v.impact === "critical" || v.impact === "serious"
  );

  if (significantViolations.length > 0) {
    const summaries: ViolationSummary[] = significantViolations.map((v) => ({
      id: v.id,
      impact: v.impact ?? "unknown",
      help: v.help,
      helpUrl: v.helpUrl,
      nodes: v.nodes.map((n) => ({
        target: n.target.map((t) => String(t)),
        html: n.html.slice(0, 160),
      })),
    }));

    const formattedOutput = summaries
      .map(
        (v) =>
          `[${v.impact.toUpperCase()}] Rule "${v.id}": ${v.help} (${v.helpUrl})\nAffected nodes:\n` +
          v.nodes.map((n) => `  - Target: ${n.target.join(" ")}\n    HTML: ${n.html}`).join("\n")
      )
      .join("\n\n");

    expect(
      significantViolations,
      `Accessibility violations (critical/serious) detected on route "${routeLabel}":\n\n${formattedOutput}`
    ).toEqual([]);
  }

  expect(significantViolations).toEqual([]);
}

test.describe("Public route accessibility audits", () => {
  test.beforeEach(async ({ page }) => {
    await setupStandardApiMocks(page);
  });


  test("Login page (/login) has zero critical or serious violations", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: /sign in/i, level: 1 })).toBeVisible();
    await assertNoA11yViolations(page, "/login");
  });

  test("Signup page (/signup) has zero critical or serious violations", async ({ page }) => {
    await page.goto("/signup");
    await expect(
      page.getByRole("heading", { name: /seller access request/i, level: 1 })
    ).toBeVisible();
    await assertNoA11yViolations(page, "/signup");
  });
});

const AUTHENTICATED_ROUTES: { path: string; headingRegex: RegExp }[] = [
  { path: "/", headingRegex: /welcome back/i },
  { path: "/inventory", headingRegex: /inventory/i },
  { path: "/orders", headingRegex: /orders/i },
  { path: "/pick-tasks", headingRegex: /Floor Picking & Packing Tasks|Pick Tasks/i },
  { path: "/shipments", headingRegex: /shipments/i },
  { path: "/receipts", headingRegex: /receipts/i },
  { path: "/returns", headingRegex: /returns/i },
  { path: "/transfers", headingRegex: /transfers/i },
  { path: "/migration", headingRegex: /migration/i },
  { path: "/ai-assistant", headingRegex: /copilot|assistant/i },
  { path: "/admin", headingRegex: /administration|admin/i },
];

test.describe("Authenticated operational route accessibility audits", () => {
  test.beforeEach(async ({ page }) => {
    await setupStandardApiMocks(page);
    await injectAuthSession(page);
  });

  for (const route of AUTHENTICATED_ROUTES) {
    test(`Route "${route.path}" has zero critical or serious violations`, async ({ page }) => {
      await page.goto(route.path);
      await expect(page.locator("#main-content")).toBeVisible();
      await expect(page.getByRole("heading", { name: route.headingRegex, level: 1 })).toBeVisible();
      await assertNoA11yViolations(page, route.path);
    });
  }
});

test.describe("Keyboard navigation and accessible names", () => {
  test.beforeEach(async ({ page }) => {
    await setupStandardApiMocks(page);
    await injectAuthSession(page);
  });

  test("Skip link moves keyboard focus to #main-content", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("#main-content")).toBeVisible();
    await page.locator("body").focus();
    await page.keyboard.press("Tab");
    const skipLink = page.getByRole("link", { name: "Skip to main content" });
    await expect(skipLink).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.locator("#main-content")).toBeFocused();
  });

  test("Route change moves focus to #main-content after navigation", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("#main-content")).toBeVisible();
    await page.locator("aside nav").getByRole("link", { name: "Inventory", exact: true }).click();
    await expect(page).toHaveURL(/\/inventory$/);
    await expect(page.getByRole("heading", { name: /inventory/i, level: 1 })).toBeVisible();
    await expect(page.locator("#main-content")).toBeFocused();
  });

  test("Operational scanner/search fields expose intended accessible names", async ({ page }) => {
    await page.goto("/inventory");
    await expect(
      page.getByRole("textbox", { name: "Search inventory by barcode, SKU, or product name" })
    ).toBeVisible();

    await page.goto("/orders");
    await expect(
      page.getByRole("textbox", { name: "Search orders by order number, customer, or seller" })
    ).toBeVisible();

    await page.goto("/shipments");
    await expect(
      page.getByRole("textbox", { name: "Search shipments by tracking number or carrier" })
    ).toBeVisible();

    await page.goto("/receipts");
    await expect(
      page.getByRole("textbox", { name: "Search receipts by tracking number or receipt" })
    ).toBeVisible();
  });
});
