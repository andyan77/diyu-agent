"use client";

/**
 * Content review queue: moderate knowledge entries pending approval.
 *
 * Task card: FA3-2
 * Shows items flagged by content security pipeline (OS3-1)
 * for human review with approve/reject/escalate actions.
 */

import { useCallback, useEffect, useState } from "react";
import { getAdminClient } from "@/lib/api";

interface ReviewItem {
  id: string;
  entity_type: string;
  name: string;
  content_preview: string;
  security_status: "flagged" | "suspicious" | "under_review";
  flagged_reason: string;
  submitted_by: string;
  submitted_at: string;
}

interface KnowledgeListResponse {
  entries: {
    entry_id: string;
    entity_type: string;
    properties: Record<string, unknown>;
    org_id: string;
    status: string;
  }[];
  total: number;
}

const STATUS_COLORS: Record<string, string> = {
  flagged: "#ef4444",
  suspicious: "#f59e0b",
  under_review: "#3b82f6",
};

export default function ContentReviewPage() {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    async function loadReviewItems() {
      try {
        const api = getAdminClient();
        const data = await api.get<KnowledgeListResponse>(
          "/v1/admin/knowledge?limit=50",
        );
        setItems(
          data.entries
            .filter((e) => e.properties.security_status)
            .map((e) => ({
              id: e.entry_id,
              entity_type: e.entity_type,
              name: (e.properties.name as string) ?? e.entry_id,
              content_preview:
                (e.properties.content_preview as string) ??
                "No preview available.",
              security_status: ((e.properties.security_status as string) ??
                "flagged") as ReviewItem["security_status"],
              flagged_reason:
                (e.properties.flagged_reason as string) ?? "Pending review",
              submitted_by:
                (e.properties.submitted_by as string) ?? "unknown",
              submitted_at:
                (e.properties.submitted_at as string) ??
                new Date().toISOString(),
            })),
        );
      } catch {
        // API unreachable -- leave empty list
      }
    }
    void loadReviewItems();
  }, []);

  const handleAction = useCallback(
    async (itemId: string, action: "approve" | "reject" | "escalate") => {
      try {
        const api = getAdminClient();
        await api.post(`/v1/admin/knowledge/${itemId}/review`, { action });
      } catch {
        // API unreachable -- still update UI optimistically
      }

      if (action === "approve" || action === "reject") {
        setItems((prev) => prev.filter((item) => item.id !== itemId));
        if (selectedId === itemId) setSelectedId(null);
      } else {
        setItems((prev) =>
          prev.map((item) =>
            item.id === itemId ? { ...item, security_status: "under_review" as const } : item,
          ),
        );
      }
    },
    [selectedId],
  );

  const selected = items.find((i) => i.id === selectedId);

  return (
    <div style={{ padding: 24, maxWidth: 1400 }}>
      <h1
        data-testid="review-title"
        style={{ fontSize: 20, fontWeight: 600, marginBottom: 16 }}
      >
        Content Review Queue
      </h1>

      <div style={{ display: "flex", gap: 16 }}>
        {/* Queue list */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 8 }}>
            {items.length} items pending review
          </div>

          {items.length === 0 && (
            <div
              data-testid="review-empty"
              style={{ padding: 40, textAlign: "center", color: "#9ca3af" }}
            >
              All items reviewed. Queue is empty.
            </div>
          )}

          {items.map((item) => (
            <div
              key={item.id}
              data-testid={`review-item-${item.id}`}
              onClick={() => setSelectedId(item.id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter") setSelectedId(item.id);
              }}
              style={{
                border: selectedId === item.id ? "2px solid #3b82f6" : "1px solid #e5e7eb",
                borderRadius: 8,
                padding: 12,
                marginBottom: 8,
                cursor: "pointer",
                background: selectedId === item.id ? "#eff6ff" : "white",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  marginBottom: 4,
                }}
              >
                <span style={{ fontSize: 14, fontWeight: 500 }}>{item.name}</span>
                <span
                  style={{
                    fontSize: 11,
                    fontWeight: 600,
                    color: STATUS_COLORS[item.security_status] ?? "#374151",
                  }}
                >
                  {item.security_status}
                </span>
              </div>
              <div style={{ fontSize: 12, color: "#6b7280" }}>
                {item.entity_type} &middot; {item.flagged_reason}
              </div>
            </div>
          ))}
        </div>

        {/* Detail panel */}
        {selected && (
          <div
            data-testid="review-detail"
            style={{
              width: 440,
              border: "1px solid #e5e7eb",
              borderRadius: 8,
              padding: 20,
              background: "white",
            }}
          >
            <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>
              {selected.name}
            </h2>

            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 2 }}>
                Type: {selected.entity_type}
              </div>
              <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 2 }}>
                Submitted by: {selected.submitted_by}
              </div>
              <div style={{ fontSize: 12, color: "#6b7280", marginBottom: 2 }}>
                Time: {new Date(selected.submitted_at).toLocaleString()}
              </div>
              <div style={{ fontSize: 12, marginBottom: 2 }}>
                <span style={{ color: "#6b7280" }}>Reason: </span>
                <span
                  style={{
                    color: STATUS_COLORS[selected.security_status] ?? "#374151",
                    fontWeight: 500,
                  }}
                >
                  {selected.flagged_reason}
                </span>
              </div>
            </div>

            <div
              style={{
                background: "#f9fafb",
                border: "1px solid #e5e7eb",
                borderRadius: 6,
                padding: 12,
                fontSize: 13,
                lineHeight: 1.5,
                marginBottom: 16,
              }}
            >
              {selected.content_preview}
            </div>

            <div style={{ display: "flex", gap: 8 }}>
              <button
                data-testid="review-approve"
                onClick={() => handleAction(selected.id, "approve")}
                style={{
                  flex: 1,
                  padding: "8px 0",
                  background: "#22c55e",
                  color: "white",
                  border: "none",
                  borderRadius: 6,
                  cursor: "pointer",
                  fontWeight: 500,
                }}
              >
                Approve
              </button>
              <button
                data-testid="review-reject"
                onClick={() => handleAction(selected.id, "reject")}
                style={{
                  flex: 1,
                  padding: "8px 0",
                  background: "#ef4444",
                  color: "white",
                  border: "none",
                  borderRadius: 6,
                  cursor: "pointer",
                  fontWeight: 500,
                }}
              >
                Reject
              </button>
              <button
                data-testid="review-escalate"
                onClick={() => handleAction(selected.id, "escalate")}
                style={{
                  flex: 1,
                  padding: "8px 0",
                  background: "#f59e0b",
                  color: "white",
                  border: "none",
                  borderRadius: 6,
                  cursor: "pointer",
                  fontWeight: 500,
                }}
              >
                Escalate
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
