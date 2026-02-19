import { test, expect } from "@playwright/test";

/**
 * Cross-layer FE E2E: Memory context panel (XF2-2 partial).
 *
 * Phase 2 soft gate (TASK-INT-P2-FE).
 * Requires running backend + frontend with memory data seeded.
 *
 * Covers:
 *   XF2-2 (partial): Memory panel renders context items from MemoryCore
 */

test.describe("Cross-layer: Memory Context Panel", () => {
  test.skip(
    !process.env.E2E_BACKEND_URL,
    "Requires E2E_BACKEND_URL; soft gate in Phase 2",
  );

  test("XF2-2: memory panel renders in chat view", async ({ page }) => {
    await page.goto("/chat");

    const memoryPanel = page.getByTestId("memory-panel");
    await expect(memoryPanel).toBeVisible({ timeout: 5000 });
  });

  test("XF2-2: memory items display after conversation", async ({ page }) => {
    await page.goto("/chat");

    // Send a message to trigger memory write
    const input = page.getByTestId("message-input");
    await input.fill("Remember this for memory panel test");
    await page.getByTestId("send-button").click();

    // Wait for response completion
    const assistantMessage = page.locator('[data-role="assistant"]');
    await expect(assistantMessage).toBeVisible({ timeout: 10000 });

    // Memory panel should show updated context
    const memoryPanel = page.getByTestId("memory-panel");
    const memoryItems = memoryPanel.getByTestId("memory-item");
    await expect(memoryItems.first()).toBeVisible({ timeout: 5000 });
  });

  test("XF2-2: memory panel supports expand/collapse", async ({ page }) => {
    await page.goto("/chat");

    const toggle = page.getByTestId("memory-panel-toggle");
    await expect(toggle).toBeVisible();

    // Collapse
    await toggle.click();
    const memoryPanel = page.getByTestId("memory-panel");
    await expect(memoryPanel).toBeHidden();

    // Expand
    await toggle.click();
    await expect(memoryPanel).toBeVisible();
  });
});
