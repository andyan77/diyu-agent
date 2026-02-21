import { test, expect } from "@playwright/test";

/**
 * Cross-layer FE E2E: Knowledge editing workflow (XF3-2).
 *
 * Phase 3 hard gate (TASK-INT-P3-FE).
 * Tests the admin app's knowledge management page structure
 * and review workflow UI.
 *
 * Covers:
 *   XF3-2: Knowledge editing workflow renders correctly in admin
 *
 * Architecture: Admin app provides /knowledge and /knowledge/review
 * pages for managing the Knowledge layer. This test verifies the
 * admin UI structure exists and is navigable.
 */

test.describe("Cross-layer: Knowledge Editing Workflow", () => {
  test("XF3-2: admin knowledge page renders", async ({ page }) => {
    await page.goto("/knowledge");

    // Knowledge page should render (admin app)
    const heading = page.locator("h1, h2, [data-testid='knowledge-heading']");
    await expect(heading.first()).toBeVisible({ timeout: 5000 });
  });

  test("XF3-2: admin knowledge review page renders", async ({ page }) => {
    await page.goto("/knowledge/review");

    // Review page should render
    const content = page.locator(
      "main, [data-testid='knowledge-review'], [role='main']"
    );
    await expect(content.first()).toBeVisible({ timeout: 5000 });
  });

  test("XF3-2: admin knowledge page has navigation", async ({ page }) => {
    await page.goto("/knowledge");

    // Navigation structure should exist
    const nav = page.locator("nav, [data-testid='sidebar'], [role='navigation']");
    await expect(nav.first()).toBeVisible({ timeout: 5000 });
  });
});
