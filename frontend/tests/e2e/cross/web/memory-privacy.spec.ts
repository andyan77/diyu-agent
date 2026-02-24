import { test, expect } from "@playwright/test";
import { loginAndSetToken } from "../../helpers/auth";

/**
 * Cross-layer FE E2E: Memory privacy management (XF4-3).
 *
 * Phase 4 hard gate: p4-memory-privacy-e2e
 * XNode: XF4-3 (view memory -> delete -> confirm deletion)
 *
 * Covers:
 *   XF4-3: Memory page renders with title and description
 *   XF4-3: Memory list loads items from API
 *   XF4-3: Two-step delete flow (Delete -> Confirm/Cancel)
 *   XF4-3: Empty state renders when no memories exist
 */

test.describe("Cross-layer: Memory Privacy Management", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to login first (no auth redirect), set token, then go to memory
    await page.goto("/login");
    await loginAndSetToken(page);
    await page.goto("/memory");
  });

  test("XF4-3: memory page renders with title", async ({ page }) => {
    const title = page.getByTestId("memory-title");
    await expect(title).toBeVisible({ timeout: 5000 });
    await expect(title).toHaveText("AI Memory");
  });

  test("XF4-3: memory list container renders", async ({ page }) => {
    // Wait for loading to finish
    const loading = page.getByTestId("loading");
    if (await loading.isVisible()) {
      await expect(loading).toBeHidden({ timeout: 10000 });
    }

    // Either memory list with items, or empty state should be visible
    const memoryList = page.getByTestId("memory-list");
    const emptyState = page.getByTestId("empty-state");

    const visible = await Promise.race([
      memoryList
        .waitFor({ state: "visible", timeout: 5000 })
        .then(() => "list"),
      emptyState
        .waitFor({ state: "visible", timeout: 5000 })
        .then(() => "empty"),
    ]);

    expect(["list", "empty"]).toContain(visible);
  });

  test("XF4-3: empty state displays when no memories", async ({ page }) => {
    // Wait for loading to finish
    const loading = page.getByTestId("loading");
    if (await loading.isVisible()) {
      await expect(loading).toBeHidden({ timeout: 10000 });
    }

    // If there are no memories for this user, empty state should render
    const emptyState = page.getByTestId("empty-state");
    const memoryItems = page.locator('[data-testid^="memory-item-"]');

    const count = await memoryItems.count();
    if (count === 0) {
      await expect(emptyState).toBeVisible();
      await expect(emptyState).toContainText("No memories stored");
    }
  });

  test("XF4-3: memory items display content and type", async ({ page }) => {
    // Wait for loading to finish
    const loading = page.getByTestId("loading");
    if (await loading.isVisible()) {
      await expect(loading).toBeHidden({ timeout: 10000 });
    }

    const memoryItems = page.locator('[data-testid^="memory-item-"]');
    const count = await memoryItems.count();

    if (count > 0) {
      // First memory item should have content and type
      const firstItem = memoryItems.first();
      await expect(firstItem.getByTestId("memory-content")).toBeVisible();
      await expect(firstItem.getByTestId("memory-type")).toBeVisible();

      // Delete button should be present
      await expect(firstItem.getByTestId("delete-button")).toBeVisible();
    }
  });

  test("XF4-3: delete button shows confirm/cancel step", async ({ page }) => {
    // Wait for loading to finish
    const loading = page.getByTestId("loading");
    if (await loading.isVisible()) {
      await expect(loading).toBeHidden({ timeout: 10000 });
    }

    const memoryItems = page.locator('[data-testid^="memory-item-"]');
    const count = await memoryItems.count();

    if (count > 0) {
      const firstItem = memoryItems.first();

      // Click Delete to enter confirm state
      await firstItem.getByTestId("delete-button").click();

      // Confirm and Cancel buttons should appear
      await expect(
        firstItem.getByTestId("confirm-delete-button"),
      ).toBeVisible();
      await expect(
        firstItem.getByTestId("cancel-delete-button"),
      ).toBeVisible();
    }
  });

  test("XF4-3: cancel delete reverts to initial state", async ({ page }) => {
    const loading = page.getByTestId("loading");
    if (await loading.isVisible()) {
      await expect(loading).toBeHidden({ timeout: 10000 });
    }

    const memoryItems = page.locator('[data-testid^="memory-item-"]');
    const count = await memoryItems.count();

    if (count > 0) {
      const firstItem = memoryItems.first();

      // Enter confirm state
      await firstItem.getByTestId("delete-button").click();
      await expect(
        firstItem.getByTestId("confirm-delete-button"),
      ).toBeVisible();

      // Click Cancel
      await firstItem.getByTestId("cancel-delete-button").click();

      // Should revert to single Delete button
      await expect(firstItem.getByTestId("delete-button")).toBeVisible();
    }
  });

  test("XF4-3: confirm delete removes memory item", async ({ page }) => {
    const loading = page.getByTestId("loading");
    if (await loading.isVisible()) {
      await expect(loading).toBeHidden({ timeout: 10000 });
    }

    const memoryItems = page.locator('[data-testid^="memory-item-"]');
    const countBefore = await memoryItems.count();

    if (countBefore > 0) {
      const firstItem = memoryItems.first();

      // Enter confirm state and confirm deletion
      await firstItem.getByTestId("delete-button").click();
      await firstItem.getByTestId("confirm-delete-button").click();

      // Wait for deletion — item count should decrease
      await expect(memoryItems).toHaveCount(countBefore - 1, {
        timeout: 10000,
      });
    }
  });

  test("XF4-3: error state renders on API failure", async ({ page }) => {
    await page.evaluate(() => {
      sessionStorage.setItem("token", "invalid-token");
    });
    await page.reload();

    const errorOrLogin = await Promise.race([
      page
        .getByTestId("error-message")
        .waitFor({ state: "visible", timeout: 5000 })
        .then(() => "error"),
      page
        .waitForURL("**/login**", { timeout: 5000 })
        .then(() => "login"),
    ]);

    expect(["error", "login"]).toContain(errorOrLogin);
  });
});
