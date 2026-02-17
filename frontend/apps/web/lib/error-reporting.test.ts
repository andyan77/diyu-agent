/**
 * Tests for error reporting service.
 *
 * Task card: OS2-5
 * Verifies: error reports are built correctly, sensitive data redacted.
 *
 * Uses dependency injection (captured console.error) instead of vi.spyOn.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { reportError } from "./error-reporting";

describe("reportError", () => {
  const captured: unknown[][] = [];
  let originalConsoleError: typeof console.error;
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    captured.length = 0;
    originalConsoleError = console.error;
    originalFetch = globalThis.fetch;

    // Replace console.error with a capturing function (no vi.spyOn)
    console.error = (...args: unknown[]) => {
      captured.push(args);
    };

    // Stub fetch globally
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true }));
  });

  afterEach(() => {
    console.error = originalConsoleError;
    globalThis.fetch = originalFetch;
    vi.unstubAllGlobals();
  });

  it("calls console.error in non-production", () => {
    const error = new Error("test error");
    reportError(error, { source: "test" });
    expect(captured.length).toBeGreaterThan(0);
    expect(captured[0][0]).toBe("[ErrorReporting]");
    const report = captured[0][1] as Record<string, unknown>;
    expect(report).toMatchObject({
      message: "test error",
      context: expect.objectContaining({ source: "test" }),
    });
  });

  it("includes timestamp in report", () => {
    reportError(new Error("x"));
    const report = captured[0]?.[1] as Record<string, unknown>;
    expect(report).toHaveProperty("timestamp");
    expect(typeof report.timestamp).toBe("string");
  });

  it("redacts sensitive context keys", () => {
    reportError(new Error("x"), {
      token: "secret-token",
      password: "secret-pass",
      source: "test",
    });
    const report = captured[0]?.[1] as Record<string, unknown>;
    const ctx = report.context as Record<string, unknown>;
    expect(ctx.token).toBe("[REDACTED]");
    expect(ctx.password).toBe("[REDACTED]");
    expect(ctx.source).toBe("test");
  });

  it("sends to endpoint when NEXT_PUBLIC_ERROR_REPORTING_URL is set", () => {
    const originalEnv = process.env.NEXT_PUBLIC_ERROR_REPORTING_URL;
    process.env.NEXT_PUBLIC_ERROR_REPORTING_URL =
      "https://errors.example.com/report";

    reportError(new Error("send me"));

    expect(globalThis.fetch).toHaveBeenCalledWith(
      "https://errors.example.com/report",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
      }),
    );

    process.env.NEXT_PUBLIC_ERROR_REPORTING_URL = originalEnv;
  });
});
