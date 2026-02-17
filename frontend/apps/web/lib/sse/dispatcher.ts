/**
 * SSE event dispatcher - routes events to registered handlers.
 *
 * Task card: FW2-9
 * - Maps SSE event types to UI handler callbacks
 * - Supports multiple handlers per event type
 */

import type { SSEEvent, SSEEventType, SSEHandler } from "./event-source";

export class SSEDispatcher {
  private handlers = new Map<SSEEventType, Set<SSEHandler>>();

  on(type: SSEEventType, handler: SSEHandler): () => void {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, new Set());
    }
    this.handlers.get(type)!.add(handler);

    // Return unsubscribe function
    return () => {
      this.handlers.get(type)?.delete(handler);
    };
  }

  dispatch(event: SSEEvent): void {
    const handlers = this.handlers.get(event.type);
    if (handlers) {
      for (const handler of handlers) {
        handler(event);
      }
    }
  }

  removeAll(type?: SSEEventType): void {
    if (type) {
      this.handlers.delete(type);
    } else {
      this.handlers.clear();
    }
  }
}
