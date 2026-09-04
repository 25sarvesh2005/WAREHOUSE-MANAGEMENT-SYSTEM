import { test, expect } from "@playwright/test";
import { injectAuthSession, setupStandardApiMocks } from "./helpers/auth";

test.describe("AI Assistant Interface", () => {
  test.beforeEach(async ({ page }) => {
    await setupStandardApiMocks(page);
    await injectAuthSession(page);
  });

  test("renders AI safety messaging and read-only guardrails", async ({ page }) => {
    await page.goto("/ai-assistant");

    await expect(page.getByText("Read-Only Guard Active")).toBeVisible();
    await expect(page.getByText("Read-Only Safe")).toBeVisible();
    await expect(page.getByText("AI cannot mutate stock or finalize shipments")).toBeVisible();
  });

  test("exposes inquiry domains with selected state via aria-pressed", async ({ page }) => {
    await page.goto("/ai-assistant");

    const domainGroup = page.getByRole("group", { name: /inquiry domain/i });
    await expect(domainGroup).toBeVisible();

    const inventoryBtn = page.getByRole("button", { name: "Inventory & Stock" });
    const trackingBtn = page.getByRole("button", { name: "Track & Trace" });
    const exceptionsBtn = page.getByRole("button", { name: "Facility Exceptions" });
    const rebalanceBtn = page.getByRole("button", { name: "Smart Rebalance" });

    await expect(inventoryBtn).toBeVisible();
    await expect(trackingBtn).toBeVisible();
    await expect(exceptionsBtn).toBeVisible();
    await expect(rebalanceBtn).toBeVisible();

    // Initially Inventory & Stock is selected
    await expect(inventoryBtn).toHaveAttribute("aria-pressed", "true");
    await expect(trackingBtn).toHaveAttribute("aria-pressed", "false");
    await expect(exceptionsBtn).toHaveAttribute("aria-pressed", "false");
    await expect(rebalanceBtn).toHaveAttribute("aria-pressed", "false");

    // Switch to Track & Trace
    await trackingBtn.click();
    await expect(trackingBtn).toHaveAttribute("aria-pressed", "true");
    await expect(inventoryBtn).toHaveAttribute("aria-pressed", "false");
  });

  test("submits inventory availability query and renders response with feedback widget", async ({
    page,
  }) => {
    await page.goto("/ai-assistant");

    // Locate textbox by its accessible name
    const queryInput = page.getByRole("textbox", {
      name: /AI Warehouse Copilot & Stock Inquiry/i,
    });
    await expect(queryInput).toBeVisible();
    await queryInput.fill("SKU-TEST-001");

    // Submit
    const askButton = page.getByRole("button", { name: /Ask AI/i });
    await expect(askButton).toBeEnabled();
    await askButton.click();

    // Verify mocked availability response
    await expect(
      page.getByText("SKU-TEST-001 currently has 150 units available at RENO"),
    ).toBeVisible();

    // Verify Google Gemini provider and Read-Only Verified safety badges
    await expect(page.getByText("Google Gemini")).toBeVisible();
    await expect(page.getByText("Read-Only Verified")).toBeVisible();

    // Verify Yes and No feedback buttons
    await expect(page.getByRole("button", { name: "Yes" })).toBeVisible();
    await expect(page.getByRole("button", { name: "No" })).toBeVisible();
  });

  test("switches inquiry domains and updates inquiry context", async ({ page }) => {
    await page.goto("/ai-assistant");

    // Switch to Facility Exceptions
    const exceptionsBtn = page.getByRole("button", { name: "Facility Exceptions" });
    await exceptionsBtn.click();
    await expect(exceptionsBtn).toHaveAttribute("aria-pressed", "true");
    await expect(
      page.getByRole("textbox", { name: /Summarize Operational Exceptions/i }),
    ).toBeVisible();

    // Switch to Smart Rebalance
    const rebalanceBtn = page.getByRole("button", { name: "Smart Rebalance" });
    await rebalanceBtn.click();
    await expect(rebalanceBtn).toHaveAttribute("aria-pressed", "true");
    await expect(
      page.getByRole("textbox", { name: /Generate Bicoastal Rebalance Draft/i }),
    ).toBeVisible();
  });

  test("submits smart rebalance draft with empty query and confirms draft-only safety", async ({
    page,
  }) => {
    let inventoryMutationAttempted = false;
    page.on("request", (req) => {
      const url = req.url();
      const method = req.method();
      if (
        method === "POST" &&
        (url.includes("/api/v1/inventory") ||
          url.includes("/api/v1/transfers") ||
          url.includes("/api/v1/adjustments"))
      ) {
        inventoryMutationAttempted = true;
      }
    });

    await page.goto("/ai-assistant");

    // Switch to Smart Rebalance
    await page.getByRole("button", { name: "Smart Rebalance" }).click();

    const queryInput = page.getByRole("textbox", {
      name: /Generate Bicoastal Rebalance Draft/i,
    });
    await expect(queryInput).toBeVisible();
    await expect(queryInput).toHaveValue("");

    // Submit with empty query
    const askButton = page.getByRole("button", { name: /Ask AI/i });
    await expect(askButton).toBeEnabled();
    await askButton.click();

    // Draft ID and recommendation summary appear
    await expect(page.getByText("DRF-2026-0001")).toBeVisible();
    await expect(
      page.getByText(
        "Suggested transfer of 50 units of SKU-AURA-ANC100 from Reno to Columbus to balance stock velocity.",
      ),
    ).toBeVisible();

    // UI confirms human approval is required
    await expect(page.getByText("PENDING APPROVAL")).toBeVisible();
    await expect(
      page.getByText(/This draft is saved in staging and ready for manager review/i),
    ).toBeVisible();

    // Confirm no direct inventory mutation occurred
    expect(inventoryMutationAttempted).toBe(false);
  });
});
