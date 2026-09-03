import { expect, test } from "@playwright/test";
import {
  injectAuthSession,
  MOCK_ADMIN_USER,
  setupStandardApiMocks,
} from "./helpers/auth";

test.describe("Standardized Dialogs & Confirmations", () => {
  test.beforeEach(async ({ page }) => {
    await setupStandardApiMocks(page);
  });

  test("Test A — Form Dialog Semantics and Keyboard Escape", async ({ page }) => {
    await injectAuthSession(page, MOCK_ADMIN_USER);
    await page.goto("/orders");

    const newOrderButton = page.getByRole("button", { name: /New Customer Order/i });
    await expect(newOrderButton).toBeVisible();
    await newOrderButton.focus();
    await newOrderButton.click();

    // 1. There is exactly one visible role="dialog".
    const dialogs = page.getByRole("dialog");
    await expect(dialogs).toHaveCount(1);
    const dialog = dialogs.first();
    await expect(dialog).toBeVisible();

    await expect(page.getByRole("heading", { name: "Create Customer Order" })).toBeVisible();
    await expect(dialog.getByText(/Seller Account/i)).toBeVisible();
    await expect(dialog.getByPlaceholder(/SO-2026-9041/i)).toBeVisible();

    // 2. After opening, document.activeElement is contained inside the dialog.
    const isFocusInside = await dialog.evaluate((element) =>
      element.contains(document.activeElement),
    );
    expect(isFocusInside).toBe(true);

    // 3. Press Escape.
    await page.keyboard.press("Escape");
    await expect(dialog).toBeHidden();

    // 4. After Escape closes the dialog, the original “New Customer Order” trigger is focused again.
    await expect(newOrderButton).toBeFocused();
  });

  test("Test B — Confirmation Dialog Semantics and Cancellation", async ({ page }) => {
    await injectAuthSession(page, MOCK_ADMIN_USER);
    await page.goto("/orders");

    // 1. Track POST requests whose URL targets: /api/v1/orders/{id}/cancel
    let cancelRequestCount = 0;
    page.on("request", (req) => {
      if (req.method() === "POST" && /\/api\/v1\/orders\/[^/]+\/cancel/.test(req.url())) {
        cancelRequestCount++;
      }
    });

    const cancelOrderButton = page.getByRole("button", { name: "Cancel Order" });
    await expect(cancelOrderButton).toBeVisible();
    await cancelOrderButton.click();

    const alertDialog = page.getByRole("alertdialog");
    await expect(alertDialog).toBeVisible();

    // 3. Assert the exact title “Cancel order?”.
    await expect(alertDialog.getByRole("heading", { name: "Cancel order?" })).toBeVisible();

    // 4. Assert record identifier ORD-2026-0001.
    await expect(alertDialog).toContainText("ORD-2026-0001");

    // 5. Click “Keep order”.
    const keepOrderButton = alertDialog.getByRole("button", { name: "Keep order" });
    await expect(keepOrderButton).toBeVisible();
    await keepOrderButton.click();

    // 6. Assert the dialog closes.
    await expect(alertDialog).toBeHidden();

    // 7. Assert the cancellation request count equals zero.
    expect(cancelRequestCount).toBe(0);
  });

  test("Test C — Narrow Viewport Dialog Usability", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 800 });
    await injectAuthSession(page, MOCK_ADMIN_USER);
    await page.goto("/pick-tasks");

    const generateButton = page.getByRole("button", { name: /Generate Pick Task/i });
    await expect(generateButton).toBeVisible();
    await generateButton.click();

    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect(page.getByRole("heading", { name: "Generate Pick Task" })).toBeVisible();

    const hasNoDocumentOverflow = await page.evaluate(
      () =>
        document.documentElement.scrollWidth <=
        document.documentElement.clientWidth,
    );
    expect(hasNoDocumentOverflow).toBe(true);

    const box = await dialog.boundingBox();
    expect(box).not.toBeNull();
    expect(box!.x).toBeGreaterThanOrEqual(0);
    expect(box!.x + box!.width).toBeLessThanOrEqual(360);

    const closeButton = dialog.getByRole("button", { name: "Close dialog" });
    await expect(closeButton).toBeVisible();
    await closeButton.click();

    await expect(dialog).toBeHidden();
  });

  test("Test D — Keyboard Escape Must Not Execute Confirmation", async ({ page }) => {
    await injectAuthSession(page, MOCK_ADMIN_USER);
    await page.goto("/orders");

    // 1. Create its own cancellation-request counter before opening the confirmation.
    let cancelRequestCount = 0;
    page.on("request", (req) => {
      if (req.method() === "POST" && /\/api\/v1\/orders\/[^/]+\/cancel/.test(req.url())) {
        cancelRequestCount++;
      }
    });

    // 2. Open the order cancellation alert dialog.
    const cancelOrderButton = page.getByRole("button", { name: "Cancel Order" });
    await expect(cancelOrderButton).toBeVisible();
    await cancelOrderButton.click();

    const alertDialog = page.getByRole("alertdialog");
    await expect(alertDialog).toBeVisible();

    // 3. Press Escape.
    await page.keyboard.press("Escape");

    // 4. Assert that the dialog closes.
    await expect(alertDialog).toBeHidden();

    // 5. Assert the cancellation request count equals zero.
    expect(cancelRequestCount).toBe(0);

    // 6. Assert focus returns to the Cancel Order trigger.
    await expect(cancelOrderButton).toBeFocused();
  });
});
