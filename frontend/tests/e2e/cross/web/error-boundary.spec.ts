import { test, expect } from "@playwright/test";

/**
 * Cross-layer FE E2E: Error boundary closed loop (X2-6).
 *
 * Phase 2 soft gate (p2-x2-6-fe-error-boundary).
 * Requires running backend that can simulate error responses.
 *
 * Covers:
 *   X2-6: FE error boundary catches backend errors and renders fallback UI
 */

test.describe("Cross-layer: FE Error Boundary", () => {
  test.skip(
    !process.env.E2E_BACKEND_URL,
    "Requires E2E_BACKEND_URL; soft gate in Phase 2",
  );

  test("X2-6: backend error triggers error boundary UI", async ({ page }) => {
    // Intercept API to simulate 500 error
    await page.route("**/api/v1/chat/**", (route) =>
      route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ error: "Internal Server Error" }),
      }),
    );

    await page.goto("/chat");

    const input = page.getByTestId("message-input");
    await expect(input).toBeVisible();

    await input.fill("Trigger error boundary test");
    await page.getByTestId("send-button").click();

    // Error UI should render (toast, inline error, or error boundary)
    const errorIndicator = page.getByTestId("error-message");
    await expect(errorIndicator).toBeVisible({ timeout: 5000 });
  });

  test("X2-6: error boundary allows retry", async ({ page }) => {
    let requestCount = 0;

    await page.route("**/api/v1/chat/**", (route) => {
      requestCount++;
      if (requestCount <= 1) {
        return route.fulfill({
          status: 500,
          contentType: "application/json",
          body: JSON.stringify({ error: "Internal Server Error" }),
        });
      }
      // Second request succeeds
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ message: "Recovery successful" }),
      });
    });

    await page.goto("/chat");

    const input = page.getByTestId("message-input");
    await input.fill("Error then retry test");
    await page.getByTestId("send-button").click();

    // Error appears first
    const errorIndicator = page.getByTestId("error-message");
    await expect(errorIndicator).toBeVisible({ timeout: 5000 });

    // Retry button should be available
    const retryButton = page.getByRole("button", { name: /retry/i });
    await expect(retryButton).toBeVisible();
    await retryButton.click();

    // After retry, error should disappear
    await expect(errorIndicator).toBeHidden({ timeout: 5000 });
  });
});
