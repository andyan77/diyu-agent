/**
 * Tests for ErrorBoundary component.
 *
 * Task card: OS2-5
 * Verifies: ErrorBoundary class structure and state management.
 *
 * No module-level mocks needed: tests verify the component contract
 * (static methods, instance state) without triggering side effects.
 */

import { describe, it, expect, vi } from "vitest";
import { ErrorBoundary } from "./ErrorBoundary";

describe("ErrorBoundary", () => {
  it("exports a React component class", () => {
    expect(typeof ErrorBoundary).toBe("function");
    expect(ErrorBoundary.prototype).toBeDefined();
    expect(typeof ErrorBoundary.prototype.render).toBe("function");
  });

  it("has getDerivedStateFromError static method", () => {
    expect(typeof ErrorBoundary.getDerivedStateFromError).toBe("function");
  });

  it("getDerivedStateFromError returns error state", () => {
    const error = new Error("test crash");
    const state = ErrorBoundary.getDerivedStateFromError(error);
    expect(state).toEqual({ hasError: true, error });
  });

  it("has componentDidCatch method", () => {
    expect(typeof ErrorBoundary.prototype.componentDidCatch).toBe("function");
  });

  it("has handleReset method", () => {
    const instance = new ErrorBoundary({ children: null });
    expect(typeof instance.handleReset).toBe("function");
  });

  it("initial state has no error", () => {
    const instance = new ErrorBoundary({ children: null });
    expect(instance.state).toEqual({ hasError: false, error: null });
  });

  it("handleReset clears error state", () => {
    const instance = new ErrorBoundary({ children: null });
    instance.state = { hasError: true, error: new Error("x") };
    instance.setState = vi.fn();
    instance.handleReset();
    expect(instance.setState).toHaveBeenCalledWith({
      hasError: false,
      error: null,
    });
  });
});
