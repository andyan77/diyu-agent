/**
 * Unit tests for SSE event dispatcher (FW2-9).
 */

import { describe, it, expect, vi } from "vitest";
import { SSEDispatcher } from "./dispatcher";
import type { SSEEvent } from "./event-source";

describe("SSEDispatcher", () => {
  const makeEvent = (type: SSEEvent["type"]): SSEEvent => ({
    type,
    data: { test: true },
    timestamp: new Date().toISOString(),
  });

  it("dispatches to registered handlers", () => {
    const dispatcher = new SSEDispatcher();
    const handler = vi.fn();

    dispatcher.on("budget_warning", handler);
    dispatcher.dispatch(makeEvent("budget_warning"));

    expect(handler).toHaveBeenCalledOnce();
  });

  it("does not dispatch to wrong type", () => {
    const dispatcher = new SSEDispatcher();
    const handler = vi.fn();

    dispatcher.on("budget_warning", handler);
    dispatcher.dispatch(makeEvent("system_notification"));

    expect(handler).not.toHaveBeenCalled();
  });

  it("supports multiple handlers per type", () => {
    const dispatcher = new SSEDispatcher();
    const h1 = vi.fn();
    const h2 = vi.fn();

    dispatcher.on("media_event", h1);
    dispatcher.on("media_event", h2);
    dispatcher.dispatch(makeEvent("media_event"));

    expect(h1).toHaveBeenCalledOnce();
    expect(h2).toHaveBeenCalledOnce();
  });

  it("unsubscribe removes handler", () => {
    const dispatcher = new SSEDispatcher();
    const handler = vi.fn();

    const unsub = dispatcher.on("task_status_update", handler);
    unsub();
    dispatcher.dispatch(makeEvent("task_status_update"));

    expect(handler).not.toHaveBeenCalled();
  });

  it("removeAll clears all handlers", () => {
    const dispatcher = new SSEDispatcher();
    const h1 = vi.fn();
    const h2 = vi.fn();

    dispatcher.on("budget_warning", h1);
    dispatcher.on("media_event", h2);
    dispatcher.removeAll();

    dispatcher.dispatch(makeEvent("budget_warning"));
    dispatcher.dispatch(makeEvent("media_event"));

    expect(h1).not.toHaveBeenCalled();
    expect(h2).not.toHaveBeenCalled();
  });

  it("removeAll with type only clears that type", () => {
    const dispatcher = new SSEDispatcher();
    const h1 = vi.fn();
    const h2 = vi.fn();

    dispatcher.on("budget_warning", h1);
    dispatcher.on("media_event", h2);
    dispatcher.removeAll("budget_warning");

    dispatcher.dispatch(makeEvent("budget_warning"));
    dispatcher.dispatch(makeEvent("media_event"));

    expect(h1).not.toHaveBeenCalled();
    expect(h2).toHaveBeenCalledOnce();
  });
});
