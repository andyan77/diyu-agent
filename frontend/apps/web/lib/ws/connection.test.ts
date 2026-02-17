/**
 * Unit tests for WebSocket connection manager (FW2-7).
 *
 * Acceptance: pnpm test --filter web -- --grep ws
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { WSConnection, type WSMessage } from "./connection";

// Minimal WebSocket mock
class MockWebSocket {
  static instances: MockWebSocket[] = [];
  url: string;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  sent: string[] = [];
  closed = false;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  send(data: string) {
    this.sent.push(data);
  }

  close() {
    this.closed = true;
    this.onclose?.();
  }

  // Test helpers
  simulateOpen() {
    this.onopen?.();
  }

  simulateMessage(data: WSMessage) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }

  simulateClose() {
    this.onclose?.();
  }
}

describe("WSConnection", () => {
  beforeEach(() => {
    MockWebSocket.instances = [];
    vi.stubGlobal("WebSocket", MockWebSocket);
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("connects with token in URL", () => {
    const onMessage = vi.fn();
    const conn = new WSConnection({
      url: "ws://localhost/ws",
      token: "test-token",
      onMessage,
    });

    conn.connect();
    expect(MockWebSocket.instances).toHaveLength(1);
    expect(MockWebSocket.instances[0].url).toBe(
      "ws://localhost/ws?token=test-token",
    );
    conn.disconnect();
  });

  it("reports state changes", () => {
    const states: string[] = [];
    const conn = new WSConnection({
      url: "ws://localhost/ws",
      token: "t",
      onMessage: vi.fn(),
      onStateChange: (s) => states.push(s),
    });

    conn.connect();
    expect(states).toContain("connecting");

    MockWebSocket.instances[0].simulateOpen();
    expect(states).toContain("open");
    expect(conn.currentState).toBe("open");

    conn.disconnect();
    expect(states).toContain("closed");
  });

  it("dispatches received messages", () => {
    const onMessage = vi.fn();
    const conn = new WSConnection({
      url: "ws://localhost/ws",
      token: "t",
      onMessage,
    });

    conn.connect();
    MockWebSocket.instances[0].simulateOpen();
    MockWebSocket.instances[0].simulateMessage({
      type: "message",
      content: "hello",
    });

    expect(onMessage).toHaveBeenCalledWith({
      type: "message",
      content: "hello",
    });
    conn.disconnect();
  });

  it("sends messages when open", () => {
    const conn = new WSConnection({
      url: "ws://localhost/ws",
      token: "t",
      onMessage: vi.fn(),
    });

    conn.connect();
    MockWebSocket.instances[0].simulateOpen();
    conn.send({ type: "message", content: "hi" });

    expect(MockWebSocket.instances[0].sent).toHaveLength(1);
    expect(JSON.parse(MockWebSocket.instances[0].sent[0])).toEqual({
      type: "message",
      content: "hi",
    });
    conn.disconnect();
  });

  it("queues messages when not open and flushes on reconnect", () => {
    const conn = new WSConnection({
      url: "ws://localhost/ws",
      token: "t",
      onMessage: vi.fn(),
    });

    // Send before connect -> queued
    conn.send({ type: "message", content: "queued" });

    conn.connect();
    MockWebSocket.instances[0].simulateOpen();

    // Should have flushed
    expect(MockWebSocket.instances[0].sent).toHaveLength(1);
    conn.disconnect();
  });

  it("schedules reconnect on close", () => {
    const conn = new WSConnection({
      url: "ws://localhost/ws",
      token: "t",
      onMessage: vi.fn(),
      reconnectIntervalMs: 1000,
      maxReconnectAttempts: 3,
    });

    conn.connect();
    MockWebSocket.instances[0].simulateClose();

    // After delay, should create new WebSocket
    vi.advanceTimersByTime(1000);
    expect(MockWebSocket.instances).toHaveLength(2);

    conn.disconnect();
  });

  it("stops reconnecting after max attempts", () => {
    const conn = new WSConnection({
      url: "ws://localhost/ws",
      token: "t",
      onMessage: vi.fn(),
      reconnectIntervalMs: 100,
      maxReconnectAttempts: 2,
    });

    conn.connect();

    // First close -> reconnect attempt 1
    MockWebSocket.instances[0].simulateClose();
    vi.advanceTimersByTime(100);
    expect(MockWebSocket.instances).toHaveLength(2);

    // Second close -> reconnect attempt 2
    MockWebSocket.instances[1].simulateClose();
    vi.advanceTimersByTime(200);
    expect(MockWebSocket.instances).toHaveLength(3);

    // Third close -> no more reconnects
    MockWebSocket.instances[2].simulateClose();
    vi.advanceTimersByTime(10000);
    expect(MockWebSocket.instances).toHaveLength(3);

    conn.disconnect();
  });

  it("disconnect stops reconnection", () => {
    const conn = new WSConnection({
      url: "ws://localhost/ws",
      token: "t",
      onMessage: vi.fn(),
      reconnectIntervalMs: 100,
    });

    conn.connect();
    conn.disconnect();

    vi.advanceTimersByTime(10000);
    // Only 1 WebSocket created (no reconnect after disconnect)
    expect(MockWebSocket.instances).toHaveLength(1);
  });
});
