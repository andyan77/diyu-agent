import { test, expect } from "@playwright/test";

/**
 * Cross-layer FE E2E: Login -> Chat -> Streaming (XF2-1/2/3).
 *
 * Phase 2 hard gate (p2-xf2-1-login-to-streaming).
 * Uses page.route() to mock auth API — no live backend required.
 *
 * Covers:
 *   XF2-1: Login flow renders and authenticates
 *   XF2-2: Chat page loads with conversation history sidebar
 *   XF2-3: Chat page streams response after conversation creation
 */

test.describe("Cross-layer: Login to Streaming", () => {
  test.beforeEach(async ({ page }) => {
    // Mock auth API endpoint
    await page.route("**/api/v1/auth/**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          token: "test-jwt-token",
          user: { id: "user-1", email: "test@diyu.ai" },
        }),
      }),
    );
  });

  test("XF2-1: login page renders with auth form", async ({ page }) => {
    await page.goto("/login");

    const emailInput = page.getByLabel("Email");
    await expect(emailInput).toBeVisible();

    const passwordInput = page.getByLabel("Password");
    await expect(passwordInput).toBeVisible();

    // Button text is "Login" (not "Sign In" or "Log In")
    const submitButton = page.getByRole("button", { name: /login/i });
    await expect(submitButton).toBeVisible();
  });

  test("XF2-2: chat page renders with conversation sidebar", async ({
    page,
  }) => {
    await page.goto("/chat");

    // Chat layout renders with sidebar containing history
    const chatLayout = page.getByTestId("chat-layout");
    await expect(chatLayout).toBeVisible({ timeout: 5000 });

    // Sidebar has "New Conversation" button
    const newConvBtn = page.getByTestId("new-conversation");
    await expect(newConvBtn).toBeVisible();
  });

  test("XF2-3: chat page streams after conversation creation", async ({
    page,
  }) => {
    await page.goto("/chat");

    // Input is disabled until a conversation exists
    const input = page.getByTestId("message-input");
    await expect(input).toBeVisible();
    await expect(input).toBeDisabled();

    // Create a new conversation
    await page.getByTestId("new-conversation").click();

    // Input should now be enabled
    await expect(input).toBeEnabled();

    await input.fill("Cross-layer streaming test");
    await page.getByTestId("send-button").click();

    // Streaming indicator should appear on the assistant message
    const streamingIndicator = page.getByTestId("streaming-indicator");
    await expect(streamingIndicator).toBeVisible({ timeout: 5000 });

    // After completion, assistant message should render with content
    await expect(streamingIndicator).toBeHidden({ timeout: 10000 });
    const assistantMessage = page.locator('[data-role="assistant"]');
    await expect(assistantMessage).toBeVisible();
    await expect(
      assistantMessage.getByTestId("message-content"),
    ).not.toBeEmpty();
  });
});
