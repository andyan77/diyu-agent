import { test, expect } from "@playwright/test";
import { loginAndSetToken } from "../../helpers/auth";

/**
 * SSE streaming e2e test -- Phase 2 soft gate (p2-streaming).
 *
 * Verifies the chat page renders, accepts input, and displays
 * a streaming response with the streaming indicator.
 *
 * Uses real backend (FastAPI + PostgreSQL + LLM API).
 * No mocks -- auth via seeded dev user (dev@diyu.ai / devpass123).
 */

test.describe("Chat Streaming", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate first so sessionStorage is on the correct origin
    await page.goto("/chat");
    // Login via real backend API and inject token
    await loginAndSetToken(page);
    // Reload to pick up the token
    await page.reload();
  });

  test("sends message and shows streaming indicator then completes", async ({
    page,
  }) => {
    // Chat page should render with empty state
    await expect(page.getByTestId("empty-state")).toBeVisible();
    await expect(page.getByTestId("message-input")).toBeVisible();

    // Create a new conversation
    await page.getByTestId("new-conversation").click();

    // Input should now be enabled
    const input = page.getByTestId("message-input");
    await expect(input).toBeEnabled();

    // Type and send a message
    await input.fill("Hello, streaming test");
    await page.getByTestId("send-button").click();

    // User message should appear
    const userMessage = page.locator('[data-role="user"]');
    await expect(userMessage).toBeVisible();
    await expect(userMessage.getByTestId("message-content")).toContainText(
      "Hello, streaming test",
    );

    // Streaming indicator should appear on assistant message
    const streamingIndicator = page.getByTestId("streaming-indicator");
    await expect(streamingIndicator).toBeVisible({ timeout: 5000 });

    // After streaming completes, indicator disappears and content appears
    // LLM response may take up to 30s
    await expect(streamingIndicator).toBeHidden({ timeout: 30000 });

    const assistantMessage = page.locator('[data-role="assistant"]');
    await expect(assistantMessage).toBeVisible();
    await expect(
      assistantMessage.getByTestId("message-content"),
    ).not.toBeEmpty();
  });

  test("chat page has accessible input elements", async ({ page }) => {
    // Input should have aria-label
    const input = page.getByLabel("Message input");
    await expect(input).toBeVisible();

    // Send button should have aria-label
    const sendButton = page.getByLabel("Send message");
    await expect(sendButton).toBeVisible();
  });
});
