"use client";

/**
 * Chat history sidebar: list, create, rename, delete, search conversations.
 *
 * Task card: FW2-3
 * Dependencies: FW2-1
 */

import { useMemo, useState } from "react";

export interface ConversationItem {
  id: string;
  title: string;
  updatedAt: string;
}

interface HistoryProps {
  conversations: ConversationItem[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onRename: (id: string, newTitle: string) => void;
  onDelete: (id: string) => void;
}

export function History({
  conversations,
  activeId,
  onSelect,
  onCreate,
  onRename,
  onDelete,
}: HistoryProps) {
  const [search, setSearch] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");

  const filtered = useMemo(() => {
    if (!search.trim()) return conversations;
    const q = search.toLowerCase();
    return conversations.filter((c) => c.title.toLowerCase().includes(q));
  }, [conversations, search]);

  const handleRenameSubmit = (id: string) => {
    if (editTitle.trim()) {
      onRename(id, editTitle.trim());
    }
    setEditingId(null);
  };

  return (
    <div
      data-testid="chat-history"
      style={{ display: "flex", flexDirection: "column", height: "100%" }}
    >
      <div style={{ padding: "12px", borderBottom: "1px solid #e5e7eb" }}>
        <button
          data-testid="new-conversation"
          onClick={onCreate}
          style={{
            width: "100%",
            padding: "8px 12px",
            background: "#3b82f6",
            color: "white",
            border: "none",
            borderRadius: 4,
            cursor: "pointer",
            marginBottom: 8,
          }}
        >
          New Conversation
        </button>
        <input
          data-testid="search-conversations"
          type="text"
          placeholder="Search..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search conversations"
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
        role="listbox"
        aria-label="Conversations"
        style={{ flex: 1, overflow: "auto", listStyle: "none", margin: 0, padding: 0 }}
      >
        {filtered.map((conv) => (
          <li
            key={conv.id}
            role="option"
            aria-selected={conv.id === activeId}
            data-testid={`conversation-${conv.id}`}
            style={{
              padding: "8px 12px",
              cursor: "pointer",
              background: conv.id === activeId ? "#eff6ff" : "transparent",
              borderBottom: "1px solid #f3f4f6",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            {editingId === conv.id ? (
              <input
                data-testid="rename-input"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                onBlur={() => handleRenameSubmit(conv.id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleRenameSubmit(conv.id);
                  if (e.key === "Escape") setEditingId(null);
                }}
                ref={(el) => el?.focus()}
                style={{ flex: 1, padding: "2px 4px", border: "1px solid #93c5fd" }}
              />
            ) : (
              <>
                <button
                  type="button"
                  onClick={() => onSelect(conv.id)}
                  style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", background: "none", border: "none", cursor: "pointer", textAlign: "left", padding: 0 }}
                >
                  {conv.title}
                </button>
                <span style={{ display: "flex", gap: 4 }}>
                  <button
                    data-testid={`rename-${conv.id}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      setEditingId(conv.id);
                      setEditTitle(conv.title);
                    }}
                    aria-label={`Rename ${conv.title}`}
                    style={{ background: "none", border: "none", cursor: "pointer", fontSize: 12 }}
                  >
                    edit
                  </button>
                  <button
                    data-testid={`delete-${conv.id}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(conv.id);
                    }}
                    aria-label={`Delete ${conv.title}`}
                    style={{ background: "none", border: "none", cursor: "pointer", fontSize: 12, color: "#ef4444" }}
                  >
                    del
                  </button>
                </span>
              </>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
