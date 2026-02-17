"use client";

/**
 * Chat page: dual-pane layout with conversation history + chat area.
 *
 * Task card: FW2-1
 * Composes: Layout (FW2-1), History (FW2-3), StreamMessage (FW2-2),
 *           MessageActions (FW2-5), MemoryPanel (FW2-4), FileUpload (FW2-6)
 */

import { useCallback, useRef, useState } from "react";
import { ChatLayout } from "@/components/chat/Layout";
import { FileUpload } from "@/components/chat/FileUpload";
import { History, type ConversationItem } from "@/components/chat/History";
import { MemoryPanel, type MemoryItem } from "@/components/chat/MemoryPanel";
import { MessageActions } from "@/components/chat/MessageActions";
import { StreamMessage, type ChatMessage } from "@/components/chat/StreamMessage";

export default function ChatPage() {
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [activeConv, setActiveConv] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [memoryOpen, setMemoryOpen] = useState(false);
  const [memoryItems] = useState<MemoryItem[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const handleNewConversation = useCallback(() => {
    const id = crypto.randomUUID();
    const newConv: ConversationItem = {
      id,
      title: `New Chat ${conversations.length + 1}`,
      updatedAt: new Date().toISOString(),
    };
    setConversations((prev) => [newConv, ...prev]);
    setActiveConv(id);
    setMessages([]);
  }, [conversations.length]);

  const handleSend = useCallback(() => {
    if (!input.trim() || !activeConv) return;

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: input.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput("");

    // Simulate assistant response (replaced by WS in production)
    const assistantMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "assistant",
      content: "",
      isStreaming: true,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, assistantMsg]);

    setTimeout(() => {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMsg.id
            ? { ...m, content: "This is a placeholder response.", isStreaming: false }
            : m,
        ),
      );
    }, 300);
  }, [input, activeConv]);

  const handleUpload = useCallback(async (_file: File): Promise<string> => {
    // Placeholder: would call G2-6 3-step upload
    return crypto.randomUUID();
  }, []);

  return (
    <ChatLayout
      sidebar={
        <History
          conversations={conversations}
          activeId={activeConv}
          onSelect={setActiveConv}
          onCreate={handleNewConversation}
          onRename={(id, title) =>
            setConversations((prev) =>
              prev.map((c) => (c.id === id ? { ...c, title } : c)),
            )
          }
          onDelete={(id) => {
            setConversations((prev) => prev.filter((c) => c.id !== id));
            if (activeConv === id) {
              setActiveConv(null);
              setMessages([]);
            }
          }}
        />
      }
    >
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          {/* Messages area */}
          <div
            data-testid="messages-area"
            style={{ flex: 1, overflow: "auto", padding: "16px 0" }}
          >
            {messages.length === 0 && (
              <div
                data-testid="empty-state"
                style={{ textAlign: "center", color: "#9ca3af", marginTop: 80 }}
              >
                Start a new conversation
              </div>
            )}
            {messages.map((msg) => (
              <div key={msg.id}>
                <StreamMessage message={msg} />
                {!msg.isStreaming && msg.role !== "system" && (
                  <MessageActions
                    messageId={msg.id}
                    content={msg.content}
                    role={msg.role}
                  />
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Input area */}
          <div
            data-testid="input-area"
            style={{
              borderTop: "1px solid #e5e7eb",
              padding: "12px 16px",
            }}
          >
            <FileUpload onUpload={handleUpload} maxSizeMB={10} />
            <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
              <input
                data-testid="message-input"
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                placeholder={activeConv ? "Type a message..." : "Create a conversation first"}
                disabled={!activeConv}
                aria-label="Message input"
                style={{
                  flex: 1,
                  padding: "8px 12px",
                  border: "1px solid #d1d5db",
                  borderRadius: 8,
                }}
              />
              <button
                data-testid="send-button"
                onClick={handleSend}
                disabled={!activeConv || !input.trim()}
                aria-label="Send message"
                style={{
                  padding: "8px 16px",
                  background: "#3b82f6",
                  color: "white",
                  border: "none",
                  borderRadius: 8,
                  cursor: activeConv && input.trim() ? "pointer" : "not-allowed",
                  opacity: activeConv && input.trim() ? 1 : 0.5,
                }}
              >
                Send
              </button>
            </div>
          </div>
        </div>

        {/* Memory panel */}
        <MemoryPanel
          items={memoryItems}
          isOpen={memoryOpen}
          onToggle={() => setMemoryOpen((prev) => !prev)}
          onDelete={() => {
            /* placeholder */
          }}
        />
      </div>
    </ChatLayout>
  );
}
