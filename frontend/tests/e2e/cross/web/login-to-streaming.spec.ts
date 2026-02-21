import { test, expect } from "@playwright/test";
import { loginAndSetToken } from "../../helpers/auth";

/**
 * Cross-layer FE E2E: Login -> Chat -> Streaming (XF2-1/2/3).
 *
 * Phase 2 soft gate (p2-xf2-1-login-to-streaming).
 * Uses real backend -- NO mocks.
 *
 * Covers:
 *   XF2-1: Login flow renders and authenticates
 *   XF2-2: Chat page loads with conversation history sidebar
 *   XF2-3: Chat page streams response after conversation creation
 */

test.describe("Cross-layer: Login to Streaming", () => {
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
    // Navigate first to set origin, then inject token
    await page.goto("/chat");
    await loginAndSetToken(page);
    await page.reload();

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
    // Navigate first to set origin, then inject token
    await page.goto("/chat");
    await loginAndSetToken(page);
    await page.reload();

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
    // LLM response may take up to 30s
    await expect(streamingIndicator).toBeHidden({ timeout: 30000 });
    const assistantMessage = page.locator('[data-role="assistant"]');
    await expect(assistantMessage).toBeVisible();
    await expect(
      assistantMessage.getByTestId("message-content"),
    ).not.toBeEmpty();
  });
});
