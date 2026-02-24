import { test, expect } from "@playwright/test";
import { loginAndSetToken } from "../../helpers/auth";

/**
 * Cross-layer FE E2E: System monitoring dashboard (XF4-2).
 *
 * Phase 4 hard gate: p4-monitoring-dashboard
 * XNode: XF4-2 (system monitoring dashboard)
 *
 * Covers:
 *   XF4-2: Monitoring page renders with title
 *   XF4-2: Overview cards display health, uptime, latency, error rate
 *   XF4-2: Services table renders with status badges
 *   XF4-2: Auto-refresh toggle works
 *   XF4-2: Request metrics section displays
 */

const ADMIN_BASE = process.env.ADMIN_BASE_URL ?? "http://localhost:3001";

const MOCK_STATUS = {
  healthy: true,
  uptime_seconds: 86400,
  version: "0.1.0",
  services: {
    database: { status: "healthy", latency_ms: 3 },
    redis: { status: "healthy", latency_ms: 1 },
    neo4j: { status: "degraded", latency_ms: 45 },
    qdrant: { status: "healthy", latency_ms: 8 },
    celery: { status: "healthy", latency_ms: 2 },
  },
  metrics: {
    active_requests: 12,
    total_requests: 54321,
    error_rate: 0.02,
    p95_latency_ms: 125,
    memory_mb: 512,
  },
};

test.describe("Cross-layer: System Monitoring Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    // Mock admin status API to return rich monitoring data
    await page.route("**/api/v1/admin/status", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(MOCK_STATUS),
      }),
    );

    // Navigate to admin login page first (no auth redirect), set tokens, then go to monitoring
    await page.goto(`${ADMIN_BASE}/login`);
    const token = await loginAndSetToken(page);
    // Also set admin_token since monitoring page uses admin_token key
    await page.evaluate((t: string) => {
      sessionStorage.setItem("admin_token", t);
    }, token);
    await page.goto(`${ADMIN_BASE}/monitoring`);
  });

  test("XF4-2: monitoring page renders with title", async ({ page }) => {
    const title = page.getByTestId("monitoring-title");
    await expect(title).toBeVisible({ timeout: 5000 });
    await expect(title).toHaveText("System Monitoring");
  });

  test("XF4-2: auto-refresh toggle is present and checked", async ({
    page,
  }) => {
    const toggle = page.getByTestId("auto-refresh-toggle");
    await expect(toggle).toBeVisible({ timeout: 5000 });
    await expect(toggle).toBeChecked();
  });

  test("XF4-2: auto-refresh can be toggled off", async ({ page }) => {
    const toggle = page.getByTestId("auto-refresh-toggle");
    await expect(toggle).toBeVisible({ timeout: 5000 });

    // Uncheck
    await toggle.uncheck();
    await expect(toggle).not.toBeChecked();

    // Re-check
    await toggle.check();
    await expect(toggle).toBeChecked();
  });

  test("XF4-2: overview cards render with metrics", async ({ page }) => {
    // Wait for loading to finish
    const loading = page.getByTestId("loading");
    if (await loading.isVisible()) {
      await expect(loading).toBeHidden({ timeout: 10000 });
    }

    const cards = page.getByTestId("overview-cards");
    await expect(cards).toBeVisible({ timeout: 10000 });

    // Individual metric cards
    await expect(page.getByTestId("overall-health")).toBeVisible();
    await expect(page.getByTestId("uptime")).toBeVisible();
    await expect(page.getByTestId("p95-latency")).toBeVisible();
    await expect(page.getByTestId("error-rate")).toBeVisible();
  });

  test("XF4-2: services table renders with rows", async ({ page }) => {
    const loading = page.getByTestId("loading");
    if (await loading.isVisible()) {
      await expect(loading).toBeHidden({ timeout: 10000 });
    }

    const table = page.getByTestId("services-table");
    await expect(table).toBeVisible({ timeout: 10000 });

    // Should have header + at least 1 service row
    const rows = table.locator("tbody tr");
    await expect(rows).not.toHaveCount(0);
  });

  test("XF4-2: request metrics section renders", async ({ page }) => {
    const loading = page.getByTestId("loading");
    if (await loading.isVisible()) {
      await expect(loading).toBeHidden({ timeout: 10000 });
    }

    await expect(page.getByTestId("active-requests")).toBeVisible({
      timeout: 10000,
    });
    await expect(page.getByTestId("total-requests")).toBeVisible();
    await expect(page.getByTestId("memory-usage")).toBeVisible();
    await expect(page.getByTestId("version")).toBeVisible();
  });

  test("XF4-2: error state renders on API failure", async ({ page }) => {
    // Remove mock and set invalid token to trigger auth error
    await page.unroute("**/api/v1/admin/status");
    await page.evaluate(() => {
      sessionStorage.setItem("admin_token", "invalid-token");
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
