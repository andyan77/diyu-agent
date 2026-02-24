"use client";

/**
 * Memory privacy management page.
 *
 * Task card: FW4-5 (part), MC4-1 (delete pipeline)
 * XNode: XF4-3 (view memory -> delete -> confirm deletion)
 */

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

interface MemoryItem {
  id: string;
  content: string;
  memory_type: string;
  created_at: string;
  importance: number;
}

export default function MemoryPage() {
  const router = useRouter();
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const apiBase =
    process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8001";

  const getToken = useCallback((): string | null => {
    return sessionStorage.getItem("token");
  }, []);

  const fetchMemories = useCallback(async () => {
    const token = getToken();
    if (!token) {
      router.push("/login");
      return;
    }

    try {
      setLoading(true);
      const res = await fetch(`${apiBase}/api/v1/memory/items`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.status === 401) {
        sessionStorage.removeItem("token");
        router.push("/login");
        return;
      }

      if (!res.ok) {
        throw new Error(`Failed to fetch memories (${res.status})`);
      }

      const data: { items: MemoryItem[] } = await res.json();
      setMemories(data.items);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load memories");
    } finally {
      setLoading(false);
    }
  }, [apiBase, getToken, router]);

  useEffect(() => {
    fetchMemories();
  }, [fetchMemories]);

  const handleDelete = useCallback(
    async (memoryId: string) => {
      const token = getToken();
      if (!token) return;

      try {
        setDeleting(memoryId);
        const res = await fetch(`${apiBase}/api/v1/memory/items/${memoryId}`, {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        });

        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.message ?? `Delete failed (${res.status})`);
        }

        // Remove from local state
        setMemories((prev) => prev.filter((m) => m.id !== memoryId));
        setConfirmDelete(null);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Delete failed");
      } finally {
        setDeleting(null);
      }
    },
    [apiBase, getToken],
  );

  return (
    <main style={{ maxWidth: 700, margin: "40px auto", padding: "0 16px" }}>
      <h1 data-testid="memory-title" style={{ fontSize: 24, marginBottom: 8 }}>
        AI Memory
      </h1>
      <p style={{ color: "#6b7280", marginBottom: 24 }}>
        View and manage what the AI remembers about you. You can delete any memory at any time.
      </p>

      {loading && <p data-testid="loading">Loading memories...</p>}

      {error && (
        <div
          data-testid="error-message"
          role="alert"
          style={{
            background: "#fef2f2",
            border: "1px solid #fecaca",
            padding: 12,
            borderRadius: 8,
            marginBottom: 16,
            color: "#dc2626",
          }}
        >
          {error}
        </div>
      )}

      {!loading && memories.length === 0 && (
        <div
          data-testid="empty-state"
          style={{ textAlign: "center", color: "#9ca3af", marginTop: 80 }}
        >
          No memories stored yet.
        </div>
      )}

      <div data-testid="memory-list">
        {memories.map((memory) => (
          <div
            key={memory.id}
            data-testid={`memory-item-${memory.id}`}
            style={{
              border: "1px solid #e5e7eb",
              borderRadius: 8,
              padding: 16,
              marginBottom: 12,
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div style={{ flex: 1 }}>
                <div
                  data-testid="memory-content"
                  style={{ marginBottom: 8, lineHeight: 1.5 }}
                >
                  {memory.content}
                </div>
                <div style={{ fontSize: 12, color: "#9ca3af", display: "flex", gap: 16 }}>
                  <span data-testid="memory-type">{memory.memory_type}</span>
                  <span>{new Date(memory.created_at).toLocaleDateString()}</span>
                </div>
              </div>
              <div>
                {confirmDelete === memory.id ? (
                  <div style={{ display: "flex", gap: 8 }}>
                    <button
                      data-testid="confirm-delete-button"
                      onClick={() => handleDelete(memory.id)}
                      disabled={deleting === memory.id}
                      style={{
                        padding: "4px 12px",
                        background: "#dc2626",
                        color: "white",
                        border: "none",
                        borderRadius: 6,
                        fontSize: 12,
                        cursor: deleting === memory.id ? "not-allowed" : "pointer",
                      }}
                    >
                      {deleting === memory.id ? "Deleting..." : "Confirm"}
                    </button>
                    <button
                      data-testid="cancel-delete-button"
                      onClick={() => setConfirmDelete(null)}
                      style={{
                        padding: "4px 12px",
                        background: "#f3f4f6",
                        border: "1px solid #d1d5db",
                        borderRadius: 6,
                        fontSize: 12,
                        cursor: "pointer",
                      }}
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button
                    data-testid="delete-button"
                    onClick={() => setConfirmDelete(memory.id)}
                    aria-label={`Delete memory: ${memory.content.slice(0, 30)}`}
                    style={{
                      padding: "4px 12px",
                      background: "transparent",
                      border: "1px solid #fecaca",
                      borderRadius: 6,
                      color: "#dc2626",
                      fontSize: 12,
                      cursor: "pointer",
                    }}
                  >
                    Delete
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </main>
  );
}
