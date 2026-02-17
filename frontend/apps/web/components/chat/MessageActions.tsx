"use client";

/**
 * Message actions: copy, retry, feedback (thumbs up/down).
 *
 * Task card: FW2-5
 * - Copy: copies message content to clipboard
 * - Retry: regenerates assistant response
 * - Feedback: records positive/negative signal
 */

import { useCallback, useState } from "react";

interface MessageActionsProps {
  messageId: string;
  content: string;
  role: "user" | "assistant";
  onRetry?: (messageId: string) => void;
  onFeedback?: (messageId: string, type: "positive" | "negative") => void;
}

export function MessageActions({
  messageId,
  content,
  role,
  onRetry,
  onFeedback,
}: MessageActionsProps) {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<"positive" | "negative" | null>(
    null,
  );

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API not available
    }
  }, [content]);

  const handleFeedback = useCallback(
    (type: "positive" | "negative") => {
      setFeedback(type);
      onFeedback?.(messageId, type);
    },
    [messageId, onFeedback],
  );

  return (
    <div
      data-testid={`message-actions-${messageId}`}
      style={{
        display: "flex",
        gap: 4,
        padding: "2px 16px",
        justifyContent: role === "user" ? "flex-end" : "flex-start",
      }}
    >
      <button
        data-testid={`copy-${messageId}`}
        onClick={handleCopy}
        aria-label="Copy message"
        style={{
          background: "none",
          border: "none",
          cursor: "pointer",
          fontSize: 12,
          color: "#6b7280",
        }}
      >
        {copied ? "copied" : "copy"}
      </button>

      {role === "assistant" && (
        <>
          <button
            data-testid={`retry-${messageId}`}
            onClick={() => onRetry?.(messageId)}
            aria-label="Retry message"
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              fontSize: 12,
              color: "#6b7280",
            }}
          >
            retry
          </button>
          <button
            data-testid={`feedback-positive-${messageId}`}
            onClick={() => handleFeedback("positive")}
            aria-label="Good response"
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              fontSize: 12,
              color: feedback === "positive" ? "#22c55e" : "#6b7280",
            }}
          >
            +
          </button>
          <button
            data-testid={`feedback-negative-${messageId}`}
            onClick={() => handleFeedback("negative")}
            aria-label="Bad response"
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              fontSize: 12,
              color: feedback === "negative" ? "#ef4444" : "#6b7280",
            }}
          >
            -
          </button>
        </>
      )}
    </div>
  );
}
