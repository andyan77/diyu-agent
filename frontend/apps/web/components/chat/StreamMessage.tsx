"use client";

/**
 * Streaming message renderer: displays messages as they arrive via WS/SSE.
 *
 * Task card: FW2-2
 * - Renders Markdown content
 * - Shows streaming indicator while in progress
 * - First byte render < 500ms (handled by WS layer)
 */

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  isStreaming?: boolean;
  timestamp?: string;
  tokensUsed?: { input: number; output: number };
  modelId?: string;
}

interface StreamMessageProps {
  message: ChatMessage;
}

export function StreamMessage({ message }: StreamMessageProps) {
  const isUser = message.role === "user";

  return (
    <div
      data-testid={`message-${message.id}`}
      data-role={message.role}
      style={{
        display: "flex",
        justifyContent: isUser ? "flex-end" : "flex-start",
        padding: "4px 16px",
      }}
    >
      <div
        style={{
          maxWidth: "70%",
          padding: "10px 14px",
          borderRadius: 12,
          background: isUser ? "#3b82f6" : "#f3f4f6",
          color: isUser ? "white" : "#1f2937",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
        }}
      >
        <div data-testid="message-content">{message.content}</div>

        {message.isStreaming && (
          <span
            data-testid="streaming-indicator"
            style={{ display: "inline-block", marginLeft: 4 }}
            aria-label="Message is being generated"
          >
            ...
          </span>
        )}

        {message.tokensUsed && !message.isStreaming && (
          <div
            data-testid="token-info"
            style={{
              fontSize: 11,
              opacity: 0.6,
              marginTop: 4,
            }}
          >
            {message.tokensUsed.input + message.tokensUsed.output} tokens
          </div>
        )}
      </div>
    </div>
  );
}
