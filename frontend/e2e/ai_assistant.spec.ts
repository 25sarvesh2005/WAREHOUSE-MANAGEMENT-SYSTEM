import { test, expect } from "@playwright/test";
import { injectAuthSession, setupStandardApiMocks } from "./helpers/auth";

test.describe("AI Assistant Interface", () => {
  test.beforeEach(async ({ page }) => {
    await setupStandardApiMocks(page);
    await injectAuthSession(page);
  });

  test("renders AI assistant with safety banner and mode tabs", async ({ page }) => {
    await page.goto("/ai-assistant");

    // Safety banner
    await expect(page.locator("#ai-safety-notice")).toBeVisible();
    await expect(page.locator("#ai-safety-notice")).toContainText(
      "AI is strictly read-only and draft-only",
    );

    // Mode tabs
    await expect(page.locator("#ai-tab-inventory-availability")).toBeVisible();
    await expect(page.locator("#ai-tab-ledger-explanation")).toBeVisible();
    await expect(page.locator("#ai-tab-exceptions-summary")).toBeVisible();
    await expect(page.locator("#ai-tab-draft-recommendation")).toBeVisible();
    await expect(page.locator("#ai-tab-order")).toBeVisible();
    await expect(page.locator("#ai-tab-receipt")).toBeVisible();
    await expect(page.locator("#ai-tab-transfer")).toBeVisible();
    await expect(page.locator("#ai-tab-shipment")).toBeVisible();
    await expect(page.locator("#ai-tab-return")).toBeVisible();
  });

  test("submits inventory availability query and renders response with feedback widget", async ({
    page,
  }) => {
    await page.goto("/ai-assistant");

    // Fill SKU
    const skuInput = page.locator("#ai-sku-input");
    await skuInput.fill("SKU-TEST-001");

    // Submit
    const askBtn = page.locator("#ai-ask-button");
    await expect(askBtn).toBeEnabled();
    await askBtn.click();

    // Verify AI response rendering
    await expect(
      page.locator("text=SKU-TEST-001 currently has 150 units available at RENO").first(),
    ).toBeVisible();

    // Verify Provider and Safety badges
    await expect(page.locator("text=Gemini AI model").first()).toBeVisible();
    await expect(page.locator("text=Read-only verified").first()).toBeVisible();

    // Verify Feedback buttons exist
    await expect(page.locator("button:has-text('Yes')").first()).toBeVisible();
    await expect(page.locator("button:has-text('No')").first()).toBeVisible();
  });

  test("switches to exceptions summary mode and draft recommendation mode", async ({ page }) => {
    await page.goto("/ai-assistant");

    // Exceptions summary mode
    await page.locator("#ai-tab-exceptions-summary").click();
    await expect(page.locator("#ai-ask-button")).toContainText(/Ask AI Assistant|Processing/);

    // Draft recommendation mode
    await page.locator("#ai-tab-draft-recommendation").click();
    await expect(page.locator("#ai-rec-type")).toBeVisible();
    await expect(page.locator("#ai-target-type")).toBeVisible();
    await expect(page.locator("#ai-ask-button")).toContainText(
      /Generate Draft Recommendation|Processing/,
    );
  });
});
