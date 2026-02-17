"use client";

/**
 * Memory context panel: view and manage AI memory items.
 *
 * Task card: FW2-4
 * - Toggle with Cmd+Shift+M
 * - View memory items associated with current conversation
 * - Delete individual memory entries
 */

import { useCallback, useEffect, useState } from "react";

export interface MemoryItem {
  id: string;
  content: string;
  confidence: number;
  createdAt: string;
  source: string;
}

interface MemoryPanelProps {
  items: MemoryItem[];
  isOpen: boolean;
  onToggle: () => void;
  onDelete: (id: string) => void;
}

export function MemoryPanel({
  items,
  isOpen,
  onToggle,
  onDelete,
}: MemoryPanelProps) {
  const [filter, setFilter] = useState("");

  // Keyboard shortcut: Cmd+Shift+M
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === "M") {
        e.preventDefault();
        onToggle();
      }
    },
    [onToggle],
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  const filtered = filter.trim()
    ? items.filter((item) =>
        item.content.toLowerCase().includes(filter.toLowerCase()),
      )
    : items;

  if (!isOpen) return null;

  return (
    <div
      data-testid="memory-panel"
      role="complementary"
      aria-label="Memory context"
      style={{
        width: 320,
        borderLeft: "1px solid #e5e7eb",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          padding: "12px",
          borderBottom: "1px solid #e5e7eb",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600 }}>
          Memory ({items.length})
        </h3>
        <button
          data-testid="close-memory-panel"
          onClick={onToggle}
          aria-label="Close memory panel"
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            fontSize: 16,
          }}
        >
          x
        </button>
      </div>

      <div style={{ padding: "8px 12px" }}>
        <input
          data-testid="memory-filter"
          type="text"
          placeholder="Filter memories..."
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          aria-label="Filter memories"
          style={{
            width: "100%",
            padding: "6px 8px",
            border: "1px solid #d1d5db",
            borderRadius: 4,
            boxSizing: "border-box",
          }}
        />
      </div>

      <ul
        data-testid="memory-list"
        style={{
          flex: 1,
          overflow: "auto",
          listStyle: "none",
          margin: 0,
          padding: 0,
        }}
      >
        {filtered.map((item) => (
          <li
            key={item.id}
            data-testid={`memory-${item.id}`}
            style={{
              padding: "10px 12px",
              borderBottom: "1px solid #f3f4f6",
            }}
          >
            <div style={{ fontSize: 13 }}>{item.content}</div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginTop: 4,
              }}
            >
              <span style={{ fontSize: 11, color: "#6b7280" }}>
                confidence: {(item.confidence * 100).toFixed(0)}%
              </span>
              <button
                data-testid={`delete-memory-${item.id}`}
                onClick={() => onDelete(item.id)}
                aria-label={`Delete memory: ${item.content.slice(0, 30)}`}
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  fontSize: 11,
                  color: "#ef4444",
                }}
              >
                delete
              </button>
            </div>
          </li>
        ))}
        {filtered.length === 0 && (
          <li
            data-testid="memory-empty"
            style={{ padding: "20px 12px", textAlign: "center", color: "#9ca3af" }}
          >
            No memories found
          </li>
        )}
      </ul>
    </div>
  );
}
