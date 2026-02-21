/**
 * E2E test authentication helper.
 *
 * Logs in via the real backend API and injects the JWT into
 * sessionStorage so the chat page can authenticate requests.
 *
 * NO MOCKS — uses the actual /api/v1/auth/login endpoint.
 */

import type { Page } from "@playwright/test";

const API_BASE = `http://localhost:${process.env.E2E_API_PORT ?? "8001"}`;

const DEV_EMAIL = process.env.E2E_EMAIL ?? "dev@diyu.ai";
const DEV_PASSWORD = process.env.E2E_PASSWORD ?? "devpass123";

/**
 * Login via backend API and inject token into sessionStorage.
 *
 * Must be called after page.goto() to a page on the same origin,
 * because sessionStorage is origin-scoped.
 */
export async function loginAndSetToken(
  page: Page,
  opts?: { email?: string; password?: string },
): Promise<string> {
  const email = opts?.email ?? DEV_EMAIL;
  const password = opts?.password ?? DEV_PASSWORD;

  const response = await page.request.post(`${API_BASE}/api/v1/auth/login`, {
    data: { email, password },
  });

  if (!response.ok()) {
    const body = await response.text();
    throw new Error(
      `Login failed (${response.status()}): ${body}. ` +
        `Ensure backend is running on port ${process.env.E2E_API_PORT ?? "8001"} ` +
        `and dev user is seeded.`,
    );
  }

  const { token } = (await response.json()) as { token: string };

  // Inject token into sessionStorage (must be on same origin)
  await page.evaluate((t: string) => {
    sessionStorage.setItem("token", t);
  }, token);

  return token;
}
