import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright configuration for DIYU Agent frontend e2e tests.
 *
 * Phase 2 soft gate: p2-streaming, p2-xf2-1-login-to-streaming
 *
 * Starts two servers:
 *   1. Next.js frontend on port 3000
 *   2. FastAPI backend on port 8001 (avoids conflict with other local services)
 *
 * Prerequisites (handled by scripts/e2e_setup.sh):
 *   - PostgreSQL + Redis running
 *   - Alembic migrations applied
 *   - Dev user seeded (dev@diyu.ai / devpass123)
 */

const apiPort = process.env.E2E_API_PORT ?? "8001";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "list",
  use: {
    baseURL: process.env.BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: [
    {
      command: `uv run uvicorn src.main:app --host 0.0.0.0 --port ${apiPort}`,
      url: `http://localhost:${apiPort}/healthz`,
      cwd: "..",
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
      env: {
        DATABASE_URL:
          process.env.DATABASE_URL ??
          "postgresql+asyncpg://diyu:diyu_dev@localhost:25432/diyu",
        REDIS_URL: process.env.REDIS_URL ?? "redis://localhost:6380/0",
        JWT_SECRET_KEY: process.env.JWT_SECRET_KEY ?? "CHANGE_ME_IN_PRODUCTION",
        JWT_SECRET: process.env.JWT_SECRET ?? "CHANGE_ME_IN_PRODUCTION",
        LLM_API_KEY: process.env.LLM_API_KEY ?? "",
        LLM_MODEL: process.env.LLM_MODEL ?? "qwen-plus",
        LLM_BASE_URL:
          process.env.LLM_BASE_URL ??
          "https://dashscope.aliyuncs.com/compatible-mode/v1",
        CORS_ORIGINS: "http://localhost:3000",
      },
    },
    {
      command: "pnpm --filter web dev",
      url: "http://localhost:3000",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      env: {
        NEXT_PUBLIC_API_BASE_URL: `http://localhost:${apiPort}`,
      },
    },
  ],
});
