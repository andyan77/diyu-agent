"use client";

/**
 * Chat page: dual-pane layout with conversation history + chat area.
 *
 * Task card: FW2-1
 * Composes: Layout (FW2-1), History (FW2-3), StreamMessage (FW2-2),
 *           MessageActions (FW2-5), MemoryPanel (FW2-4), FileUpload (FW2-6)
 */

import { useCallback, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ChatLayout } from "@/components/chat/Layout";
import { FileUpload } from "@/components/chat/FileUpload";
import { History, type ConversationItem } from "@/components/chat/History";
import { MemoryPanel, type MemoryItem } from "@/components/chat/MemoryPanel";
import { MessageActions } from "@/components/chat/MessageActions";
import { StreamMessage, type ChatMessage } from "@/components/chat/StreamMessage";

export default function ChatPage() {
  const router = useRouter();
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [activeConv, setActiveConv] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
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

  const handleSend = useCallback(async () => {
    if (!input.trim() || !activeConv || sending) return;

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: input.trim(),
      timestamp: new Date().toISOString(),
    };

    const messageText = input.trim();
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setSending(true);

    // Streaming placeholder while waiting for backend
    const placeholderId = crypto.randomUUID();
    setMessages((prev) => [
      ...prev,
      {
        id: placeholderId,
        role: "assistant",
        content: "",
        isStreaming: true,
        timestamp: new Date().toISOString(),
      },
    ]);

    try {
      const token = sessionStorage.getItem("token");
      if (!token) {
        router.push("/login");
        return;
      }

      const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
      const res = await fetch(
        `${apiBase}/api/v1/conversations/${activeConv}/messages`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ message: messageText }),
        },
      );

      if (res.status === 401) {
        sessionStorage.removeItem("token");
        router.push("/login");
        return;
      }

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.message ?? `Request failed (${res.status})`);
      }

      const data: {
        assistant_response: string;
        tokens_used: { input: number; output: number };
        model_id: string;
      } = await res.json();

      setMessages((prev) =>
        prev.map((m) =>
          m.id === placeholderId
            ? {
                ...m,
                content: data.assistant_response,
                isStreaming: false,
                tokensUsed: data.tokens_used,
                modelId: data.model_id,
              }
            : m,
        ),
      );
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : "Something went wrong";
      setMessages((prev) =>
        prev.map((m) =>
          m.id === placeholderId
            ? { ...m, content: `Error: ${errMsg}`, isStreaming: false }
            : m,
        ),
      );
    } finally {
      setSending(false);
    }
  }, [input, activeConv, sending, router]);

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
                disabled={!activeConv || !input.trim() || sending}
                aria-label="Send message"
                style={{
                  padding: "8px 16px",
                  background: "#3b82f6",
                  color: "white",
                  border: "none",
                  borderRadius: 8,
                  cursor: activeConv && input.trim() && !sending ? "pointer" : "not-allowed",
                  opacity: activeConv && input.trim() && !sending ? 1 : 0.5,
                }}
              >
                {sending ? "Sending..." : "Send"}
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
