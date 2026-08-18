import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { injectAuthSession, setupStandardApiMocks } from "./helpers/auth";

test.describe("Accessibility (A11y) Audits across Core Routes", () => {
  test("Landing and Login pages should not have critical a11y violations", async ({ page }) => {
    await setupStandardApiMocks(page);

    // 1. Landing page unauthenticated
    await page.goto("/");
    const landingResults = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .disableRules(["color-contrast"]) // Avoid strict color contrast failures in dark/light preview themes
      .analyze();
    expect(landingResults.violations.filter((v) => v.impact === "critical")).toEqual([]);

    // 2. Login page
    await page.goto("/login");
    const loginResults = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa"])
      .disableRules(["color-contrast"])
      .analyze();
    expect(loginResults.violations.filter((v) => v.impact === "critical")).toEqual([]);
  });

  test("Authenticated Operational Views should satisfy basic a11y standards", async ({ page }) => {
    await setupStandardApiMocks(page);
    await injectAuthSession(page);

    const routesToTest = [
      "/",
      "/inventory",
      "/orders",
      "/receipts",
      "/transfers",
      "/returns",
      "/migration",
      "/ai-assistant",
      "/admin",
    ];

    for (const route of routesToTest) {
      await page.goto(route);
      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa"])
        .disableRules(["color-contrast"])
        .analyze();

      const criticalViolations = results.violations.filter((v) => v.impact === "critical");
      if (criticalViolations.length > 0) {
        console.warn(`[A11y Warning] Route ${route} has ${criticalViolations.length} critical issues`);
      }
      expect(criticalViolations).toEqual([]);
    }
  });
});
