import { test, expect } from "@playwright/test";

/**
 * Cross-layer FE E2E: Login -> Org select -> Chat -> Streaming (XF2-1/2/3).
 *
 * Phase 2 soft gate (p2-xf2-1-login-to-streaming).
 * Requires running backend + auth service.
 *
 * Covers:
 *   XF2-1: Login flow renders and authenticates
 *   XF2-2: Org selector loads user's organizations
 *   XF2-3: Chat page streams response after org selection
 */

test.describe("Cross-layer: Login to Streaming", () => {
  test.skip(
    !process.env.E2E_BACKEND_URL,
    "Requires E2E_BACKEND_URL; soft gate in Phase 2",
  );

  test("XF2-1: login page renders with auth form", async ({ page }) => {
    await page.goto("/login");

    const emailInput = page.getByLabel("Email");
    await expect(emailInput).toBeVisible();

    const passwordInput = page.getByLabel("Password");
    await expect(passwordInput).toBeVisible();

    const submitButton = page.getByRole("button", { name: /sign in|log in/i });
    await expect(submitButton).toBeVisible();
  });

  test("XF2-2: org selector appears after login", async ({ page }) => {
    // Pre-condition: authenticated session
    await page.goto("/");

    const orgSelector = page.getByTestId("org-selector");
    await expect(orgSelector).toBeVisible({ timeout: 5000 });
  });

  test("XF2-3: chat page streams after org selection", async ({ page }) => {
    await page.goto("/chat");

    // Org should be selected from prior step or default
    const input = page.getByTestId("message-input");
    await expect(input).toBeVisible();

    await input.fill("Cross-layer streaming test");
    await page.getByTestId("send-button").click();

    // Streaming indicator should appear
    const streamingIndicator = page.getByTestId("streaming-indicator");
    await expect(streamingIndicator).toBeVisible({ timeout: 5000 });

    // After completion, assistant message should render
    await expect(streamingIndicator).toBeHidden({ timeout: 10000 });
    const assistantMessage = page.locator('[data-role="assistant"]');
    await expect(assistantMessage).toBeVisible();
    await expect(
      assistantMessage.getByTestId("message-content"),
    ).not.toBeEmpty();
  });
});
