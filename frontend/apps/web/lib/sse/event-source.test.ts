/**
 * Unit tests for SSE EventSource client (FW2-9).
 *
 * Acceptance: pnpm test --filter web -- --grep sse
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { SSEClient, type SSEEventType } from "./event-source";

// Mock EventSource
class MockEventSource {
  static instance: MockEventSource | null = null;
  static OPEN = 1;
  url: string;
  readyState = 0;
  onopen: (() => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  private listeners = new Map<string, ((event: Event) => void)[]>();
  closed = false;

  constructor(url: string) {
    this.url = url;
    MockEventSource.instance = this;
  }

  addEventListener(type: string, handler: (event: Event) => void) {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, []);
    }
    this.listeners.get(type)!.push(handler);
  }

  close() {
    this.closed = true;
    this.readyState = 2;
  }

  // Test helpers
  simulateOpen() {
    this.readyState = 1;
    this.onopen?.();
  }

  simulateEvent(type: SSEEventType, data: Record<string, unknown>) {
    const handlers = this.listeners.get(type) ?? [];
    const event = { data: JSON.stringify(data) } as unknown as Event;
    for (const handler of handlers) {
      handler(event);
    }
  }

  simulateMessage(data: Record<string, unknown>) {
    this.onmessage?.({
      data: JSON.stringify(data),
    } as MessageEvent);
  }
}

describe("SSEClient", () => {
  beforeEach(() => {
    MockEventSource.instance = null;
    vi.stubGlobal("EventSource", MockEventSource);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("connects with token in URL", () => {
    const client = new SSEClient({
      url: "http://localhost/sse",
      token: "test-token",
    });

    client.connect();
    expect(MockEventSource.instance).not.toBeNull();
    expect(MockEventSource.instance!.url).toBe(
      "http://localhost/sse?token=test-token",
    );
    client.disconnect();
  });

  it("reports connected state", () => {
    const client = new SSEClient({
      url: "http://localhost/sse",
      token: "t",
    });

    expect(client.connected).toBe(false);
    client.connect();
    MockEventSource.instance!.simulateOpen();
    expect(client.connected).toBe(true);
    client.disconnect();
    expect(client.connected).toBe(false);
  });

  it("fires onOpen callback", () => {
    const onOpen = vi.fn();
    const client = new SSEClient({
      url: "http://localhost/sse",
      token: "t",
      onOpen,
    });

    client.connect();
    MockEventSource.instance!.simulateOpen();
    expect(onOpen).toHaveBeenCalledOnce();
    client.disconnect();
  });

  it("dispatches typed events", () => {
    const onEvent = vi.fn();
    const client = new SSEClient({
      url: "http://localhost/sse",
      token: "t",
      onEvent,
    });

    client.connect();
    MockEventSource.instance!.simulateEvent("budget_warning", {
      remaining: 100,
    });

    expect(onEvent).toHaveBeenCalledOnce();
    const call = onEvent.mock.calls[0][0];
    expect(call.type).toBe("budget_warning");
    expect(call.data).toEqual({ remaining: 100 });
    expect(call.timestamp).toBeDefined();
    client.disconnect();
  });

  it("dispatches generic messages with type field", () => {
    const onEvent = vi.fn();
    const client = new SSEClient({
      url: "http://localhost/sse",
      token: "t",
      onEvent,
    });

    client.connect();
    MockEventSource.instance!.simulateMessage({
      type: "system_notification",
      message: "hello",
    });

    expect(onEvent).toHaveBeenCalledOnce();
    const call = onEvent.mock.calls[0][0];
    expect(call.type).toBe("system_notification");
    expect(call.data).toEqual({ message: "hello" });
    client.disconnect();
  });

  it("handles all 6 event types", () => {
    const onEvent = vi.fn();
    const client = new SSEClient({
      url: "http://localhost/sse",
      token: "t",
      onEvent,
    });

    client.connect();

    const types: SSEEventType[] = [
      "task_status_update",
      "system_notification",
      "budget_warning",
      "knowledge_update",
      "media_event",
      "experiment_update",
    ];

    for (const type of types) {
      MockEventSource.instance!.simulateEvent(type, { test: true });
    }

    expect(onEvent).toHaveBeenCalledTimes(6);
    client.disconnect();
  });

  it("disconnect closes EventSource", () => {
    const client = new SSEClient({
      url: "http://localhost/sse",
      token: "t",
    });

    client.connect();
    client.disconnect();
    expect(MockEventSource.instance!.closed).toBe(true);
  });
});
