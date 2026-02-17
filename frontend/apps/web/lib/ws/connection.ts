/**
 * WebSocket connection manager with auto-reconnect.
 *
 * Task card: FW2-7
 * - Disconnect -> auto-reconnect with exponential backoff
 * - Reconnect P95 < 5s
 * - Message queue during disconnect (no message loss)
 */

// From @diyu/shared constants
const WS_RECONNECT_INTERVAL_MS = 3000;
const WS_MAX_RECONNECT_ATTEMPTS = 10;

export type WSState = "connecting" | "open" | "closing" | "closed";

export interface WSMessage {
  type: string;
  [key: string]: unknown;
}

export interface WSConnectionOptions {
  url: string;
  token: string;
  onMessage: (data: WSMessage) => void;
  onStateChange?: (state: WSState) => void;
  maxReconnectAttempts?: number;
  reconnectIntervalMs?: number;
}

export class WSConnection {
  private ws: WebSocket | null = null;
  private state: WSState = "closed";
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private pendingMessages: WSMessage[] = [];
  private disposed = false;

  private readonly url: string;
  private readonly token: string;
  private readonly onMessage: (data: WSMessage) => void;
  private readonly onStateChange?: (state: WSState) => void;
  private readonly maxReconnectAttempts: number;
  private readonly reconnectIntervalMs: number;

  constructor(options: WSConnectionOptions) {
    this.url = options.url;
    this.token = options.token;
    this.onMessage = options.onMessage;
    this.onStateChange = options.onStateChange;
    this.maxReconnectAttempts =
      options.maxReconnectAttempts ?? WS_MAX_RECONNECT_ATTEMPTS;
    this.reconnectIntervalMs =
      options.reconnectIntervalMs ?? WS_RECONNECT_INTERVAL_MS;
  }

  get currentState(): WSState {
    return this.state;
  }

  connect(): void {
    if (this.disposed) return;
    this.setState("connecting");

    const separator = this.url.includes("?") ? "&" : "?";
    const wsUrl = `${this.url}${separator}token=${this.token}`;

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.setState("open");
      this.reconnectAttempts = 0;
      this.flushPending();
    };

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data as string) as WSMessage;
        this.onMessage(data);
      } catch {
        // Ignore malformed messages
      }
    };

    this.ws.onclose = () => {
      this.setState("closed");
      if (!this.disposed) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = () => {
      // onclose will fire after onerror
    };
  }

  send(message: WSMessage): void {
    if (this.state === "open" && this.ws) {
      this.ws.send(JSON.stringify(message));
    } else {
      this.pendingMessages.push(message);
    }
  }

  disconnect(): void {
    this.disposed = true;
    this.clearReconnectTimer();
    if (this.ws) {
      this.setState("closing");
      this.ws.close();
      this.ws = null;
    }
    this.setState("closed");
  }

  private setState(newState: WSState): void {
    if (this.state !== newState) {
      this.state = newState;
      this.onStateChange?.(newState);
    }
  }

  private flushPending(): void {
    while (this.pendingMessages.length > 0 && this.state === "open") {
      const msg = this.pendingMessages.shift()!;
      this.send(msg);
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) return;

    const delay = Math.min(
      this.reconnectIntervalMs * Math.pow(2, this.reconnectAttempts),
      30_000,
    );
    this.reconnectAttempts++;

    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
}
