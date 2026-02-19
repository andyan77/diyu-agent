import { test, expect, type Page } from "@playwright/test";

/**
 * Cross-layer FE E2E: Memory context panel (XF2-2 partial).
 *
 * Phase 2 hard gate (TASK-INT-P2-FE).
 * Tests the MemoryPanel component integration with chat page.
 *
 * Covers:
 *   XF2-2 (partial): Memory panel renders and supports keyboard toggle
 *
 * Architecture: MemoryPanel is a controlled component rendered in ChatPage.
 * Default state is closed (isOpen=false). Toggle via Cmd+Shift+M keyboard
 * shortcut or programmatic toggle. When open, shows memory items with filter
 * and delete. Close button has data-testid="close-memory-panel".
 */

/**
 * Press Ctrl+Shift+M and wait for the memory panel to appear.
 *
 * The keyboard shortcut is registered via useEffect; under parallel Playwright
 * workers the listener may not be attached when the first keypress fires.
 * This helper retries the keypress up to 3 times with a small delay.
 */
async function openMemoryPanel(page: Page): Promise<void> {
  const panel = page.getByTestId("memory-panel");
  for (let attempt = 0; attempt < 3; attempt++) {
    await page.keyboard.press("Control+Shift+M");
    try {
      await expect(panel).toBeVisible({ timeout: 2000 });
      return; // success
    } catch {
      // Retry — listener may not have been registered yet
    }
  }
  // Final attempt with full timeout
  await page.keyboard.press("Control+Shift+M");
  await expect(panel).toBeVisible({ timeout: 5000 });
}

test.describe("Cross-layer: Memory Context Panel", () => {
  test("XF2-2: memory panel is hidden by default", async ({ page }) => {
    await page.goto("/chat");

    // Chat layout should render
    const chatLayout = page.getByTestId("chat-layout");
    await expect(chatLayout).toBeVisible({ timeout: 5000 });

    // Memory panel defaults to closed (isOpen=false returns null)
    const memoryPanel = page.getByTestId("memory-panel");
    await expect(memoryPanel).toBeHidden();
  });

  test("XF2-2: memory panel opens with keyboard shortcut", async ({
    page,
  }) => {
    await page.goto("/chat");

    await expect(page.getByTestId("chat-layout")).toBeVisible({
      timeout: 5000,
    });

    // Memory panel starts hidden
    const memoryPanel = page.getByTestId("memory-panel");
    await expect(memoryPanel).toBeHidden();

    // Toggle open with Ctrl+Shift+M (retry-safe)
    await openMemoryPanel(page);

    // Close button should be present
    const closeBtn = page.getByTestId("close-memory-panel");
    await expect(closeBtn).toBeVisible();
  });

  test("XF2-2: memory panel supports open and close cycle", async ({
    page,
  }) => {
    await page.goto("/chat");

    await expect(page.getByTestId("chat-layout")).toBeVisible({
      timeout: 5000,
    });

    const memoryPanel = page.getByTestId("memory-panel");

    // Open
    await openMemoryPanel(page);

    // Close via close button
    await page.getByTestId("close-memory-panel").click();
    await expect(memoryPanel).toBeHidden();

    // Reopen via keyboard (listener already attached, should work first try)
    await page.keyboard.press("Control+Shift+M");
    await expect(memoryPanel).toBeVisible({ timeout: 5000 });
  });
});
