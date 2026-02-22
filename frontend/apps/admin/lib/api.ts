/**
 * Shared API client instance for admin app.
 *
 * Wraps @diyu/api-client with session-token auth.
 * All pages should import `getAdminClient()` instead of raw fetch.
 */

import { createApiClient, type ApiClient } from "@diyu/api-client";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/api";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return sessionStorage.getItem("diyu_admin_token");
}

/**
 * Returns a configured ApiClient bound to the current admin session token.
 *
 * Call this inside component callbacks / effects (not at module top-level)
 * so the token is read fresh each time.
 */
export function getAdminClient(): ApiClient {
  const token = getToken();
  return createApiClient(API_BASE, token ?? undefined);
}
