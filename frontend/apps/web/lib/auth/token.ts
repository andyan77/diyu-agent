/**
 * SaaS / Private dual-mode token management.
 *
 * Task card: FW1-4
 * - SaaS mode: HttpOnly cookie (server-managed, no client access)
 * - Private mode: in-memory token (never persisted to disk)
 *
 * Dependencies: DEPLOY_MODE environment variable
 */

export type DeployMode = "saas" | "private";

/**
 * Resolve current deployment mode from environment.
 * Defaults to "private" if not set.
 */
export function getDeployMode(): DeployMode {
  const mode =
    typeof process !== "undefined"
      ? process.env.NEXT_PUBLIC_DEPLOY_MODE
      : undefined;
  if (mode === "saas") return "saas";
  return "private";
}

// --- Token Store Interface ---

export interface TokenStore {
  getToken(): string | null;
  setToken(token: string): void;
  clearToken(): void;
  readonly mode: DeployMode;
}

// --- In-Memory Store (Private mode) ---

let _inMemoryToken: string | null = null;

const privateStore: TokenStore = {
  mode: "private",
  getToken() {
    return _inMemoryToken;
  },
  setToken(token: string) {
    _inMemoryToken = token;
  },
  clearToken() {
    _inMemoryToken = null;
  },
};

// --- Cookie Store (SaaS mode) ---
// In SaaS mode, tokens are HttpOnly cookies set by the server.
// Client code cannot read/write them directly.
// The store acts as a no-op marker for the auth layer.

const saasStore: TokenStore = {
  mode: "saas",
  getToken() {
    // HttpOnly cookies are sent automatically by the browser.
    // Client JS cannot access them -- return null to signal
    // that auth is cookie-based, not token-based.
    return null;
  },
  setToken(_token: string) {
    // No-op: server sets HttpOnly cookie via Set-Cookie header.
  },
  clearToken() {
    // To logout in SaaS mode, call the /api/v1/auth/logout endpoint
    // which clears the HttpOnly cookie server-side.
  },
};

// --- Factory ---

/**
 * Create token store for the current deployment mode.
 */
export function createTokenStore(mode?: DeployMode): TokenStore {
  const resolved = mode ?? getDeployMode();
  return resolved === "saas" ? saasStore : privateStore;
}

/**
 * Build the Authorization header value for API requests.
 * - Private mode: "Bearer <token>"
 * - SaaS mode: undefined (cookies sent automatically)
 */
export function getAuthHeader(store: TokenStore): string | undefined {
  if (store.mode === "saas") {
    return undefined; // cookies handle auth
  }
  const token = store.getToken();
  return token ? `Bearer ${token}` : undefined;
}
