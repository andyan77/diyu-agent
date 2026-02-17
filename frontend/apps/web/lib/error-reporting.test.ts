/**
 * Tests for error reporting service.
 *
 * Task card: OS2-5
 * Verifies: error reports are built correctly, sensitive data redacted.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { reportError } from "./error-reporting";

describe("reportError", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    // Mock fetch globally
    global.fetch = vi.fn().mockResolvedValue({ ok: true });
  });

  it("calls console.error in non-production", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    const error = new Error("test error");
    reportError(error, { source: "test" });
    expect(spy).toHaveBeenCalledWith(
      "[ErrorReporting]",
      expect.objectContaining({
        message: "test error",
        context: expect.objectContaining({ source: "test" }),
      }),
    );
  });

  it("includes timestamp in report", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    reportError(new Error("x"));
    const report = spy.mock.calls[0]?.[1];
    expect(report).toHaveProperty("timestamp");
    expect(typeof report.timestamp).toBe("string");
  });

  it("redacts sensitive context keys", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    reportError(new Error("x"), {
      token: "secret-token",
      password: "secret-pass",
      source: "test",
    });
    const report = spy.mock.calls[0]?.[1];
    expect(report.context.token).toBe("[REDACTED]");
    expect(report.context.password).toBe("[REDACTED]");
    expect(report.context.source).toBe("test");
  });

  it("sends to endpoint when NEXT_PUBLIC_ERROR_REPORTING_URL is set", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    const originalEnv = process.env.NEXT_PUBLIC_ERROR_REPORTING_URL;
    process.env.NEXT_PUBLIC_ERROR_REPORTING_URL = "https://errors.example.com/report";

    reportError(new Error("send me"));

    expect(global.fetch).toHaveBeenCalledWith(
      "https://errors.example.com/report",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
      }),
    );

    process.env.NEXT_PUBLIC_ERROR_REPORTING_URL = originalEnv;
  });
});
