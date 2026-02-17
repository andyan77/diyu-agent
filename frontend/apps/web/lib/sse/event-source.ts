/**
 * SSE EventSource client with token auth.
 *
 * Task card: FW2-9
 * - Establishes SSE connection with JWT auth
 * - Auto-reconnect on disconnect
 * - Parses typed events and dispatches to handlers
 */

export type SSEEventType =
  | "task_status_update"
  | "system_notification"
  | "budget_warning"
  | "knowledge_update"
  | "media_event"
  | "experiment_update";

export interface SSEEvent {
  type: SSEEventType;
  data: Record<string, unknown>;
  timestamp?: string;
}

export type SSEHandler = (event: SSEEvent) => void;

export interface SSEClientOptions {
  url: string;
  token: string;
  onEvent?: SSEHandler;
  onError?: (error: Event) => void;
  onOpen?: () => void;
}

export class SSEClient {
  private eventSource: EventSource | null = null;
  private disposed = false;

  private readonly url: string;
  private readonly token: string;
  private readonly onEvent?: SSEHandler;
  private readonly onError?: (error: Event) => void;
  private readonly onOpen?: () => void;

  constructor(options: SSEClientOptions) {
    this.url = options.url;
    this.token = options.token;
    this.onEvent = options.onEvent;
    this.onError = options.onError;
    this.onOpen = options.onOpen;
  }

  get connected(): boolean {
    return this.eventSource?.readyState === EventSource.OPEN;
  }

  connect(): void {
    if (this.disposed) return;

    const separator = this.url.includes("?") ? "&" : "?";
    const sseUrl = `${this.url}${separator}token=${this.token}`;

    this.eventSource = new EventSource(sseUrl);

    this.eventSource.onopen = () => {
      this.onOpen?.();
    };

    this.eventSource.onerror = (event: Event) => {
      this.onError?.(event);
    };

    // Listen to each event type
    const eventTypes: SSEEventType[] = [
      "task_status_update",
      "system_notification",
      "budget_warning",
      "knowledge_update",
      "media_event",
      "experiment_update",
    ];

    for (const type of eventTypes) {
      this.eventSource.addEventListener(type, (event: Event) => {
        const msgEvent = event as MessageEvent;
        try {
          const data = JSON.parse(msgEvent.data as string) as Record<
            string,
            unknown
          >;
          this.onEvent?.({ type, data, timestamp: new Date().toISOString() });
        } catch {
          // Ignore malformed events
        }
      });
    }

    // Default message handler for generic events
    this.eventSource.onmessage = (event: MessageEvent) => {
      try {
        const parsed = JSON.parse(event.data as string) as {
          type?: SSEEventType;
          [key: string]: unknown;
        };
        if (parsed.type) {
          const { type, ...data } = parsed;
          this.onEvent?.({
            type,
            data: data as Record<string, unknown>,
            timestamp: new Date().toISOString(),
          });
        }
      } catch {
        // Ignore malformed messages
      }
    };
  }

  disconnect(): void {
    this.disposed = true;
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}
