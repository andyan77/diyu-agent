"use client";

/**
 * Knowledge browse page: search, filter, and view knowledge entries.
 *
 * Task card: FW3-1
 * API: GET /api/v1/admin/knowledge (G3-1)
 */

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

interface KnowledgeEntry {
  entry_id: string;
  entity_type: string;
  properties: Record<string, unknown>;
  org_id: string;
}

type EntityFilter = "all" | "product" | "brand" | "category" | "style";

const ENTITY_FILTERS: { label: string; value: EntityFilter }[] = [
  { label: "All", value: "all" },
  { label: "Product", value: "product" },
  { label: "Brand", value: "brand" },
  { label: "Category", value: "category" },
  { label: "Style", value: "style" },
];

export default function KnowledgeBrowsePage() {
  const router = useRouter();
  const [entries, setEntries] = useState<KnowledgeEntry[]>([]);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<EntityFilter>("all");
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const pageSize = 20;

  const fetchEntries = useCallback(async () => {
    setLoading(true);
    try {
      const token = sessionStorage.getItem("token");
      if (!token) {
        router.push("/login");
        return;
      }

      const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
      const params = new URLSearchParams({
        limit: String(pageSize),
        offset: String(page * pageSize),
      });
      if (filter !== "all") {
        params.set("entity_type", filter);
      }

      const res = await fetch(`${apiBase}/api/v1/admin/knowledge?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.status === 401) {
        sessionStorage.removeItem("token");
        router.push("/login");
        return;
      }

      if (res.ok) {
        const data: { entries: KnowledgeEntry[]; total: number } = await res.json();
        setEntries(data.entries);
        setTotal(data.total);
      }
    } catch {
      // API not available yet - show empty state
    } finally {
      setLoading(false);
    }
  }, [router, filter, page]);

  useEffect(() => {
    fetchEntries();
  }, [fetchEntries]);

  const filtered = search.trim()
    ? entries.filter(
        (e) =>
          e.entity_type.toLowerCase().includes(search.toLowerCase()) ||
          JSON.stringify(e.properties).toLowerCase().includes(search.toLowerCase()),
      )
    : entries;

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: "0 auto" }}>
      <h1
        data-testid="knowledge-title"
        style={{ fontSize: 24, fontWeight: 600, marginBottom: 16 }}
      >
        Knowledge Base
      </h1>

      {/* Search + Filter bar */}
      <div
        style={{
          display: "flex",
          gap: 12,
          marginBottom: 16,
          alignItems: "center",
        }}
      >
        <input
          data-testid="knowledge-search"
          type="text"
          placeholder="Search knowledge entries..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          aria-label="Search knowledge"
          style={{
            flex: 1,
            padding: "8px 12px",
            border: "1px solid #d1d5db",
            borderRadius: 8,
          }}
        />
        <div style={{ display: "flex", gap: 4 }}>
          {ENTITY_FILTERS.map((f) => (
            <button
              key={f.value}
              data-testid={`filter-${f.value}`}
              onClick={() => {
                setFilter(f.value);
                setPage(0);
              }}
              style={{
                padding: "6px 12px",
                border: "1px solid #d1d5db",
                borderRadius: 6,
                background: filter === f.value ? "#3b82f6" : "white",
                color: filter === f.value ? "white" : "#374151",
                cursor: "pointer",
                fontSize: 13,
              }}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Loading state */}
      {loading && (
        <div data-testid="loading" style={{ textAlign: "center", padding: 40, color: "#9ca3af" }}>
          Loading...
        </div>
      )}

      {/* Empty state */}
      {!loading && filtered.length === 0 && (
        <div
          data-testid="empty-state"
          style={{ textAlign: "center", padding: 60, color: "#9ca3af" }}
        >
          No knowledge entries found.
        </div>
      )}

      {/* Entry grid */}
      {!loading && filtered.length > 0 && (
        <div
          data-testid="knowledge-grid"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
            gap: 16,
          }}
        >
          {filtered.map((entry) => (
            <div
              key={entry.entry_id}
              data-testid={`entry-${entry.entry_id}`}
              style={{
                border: "1px solid #e5e7eb",
                borderRadius: 8,
                padding: 16,
                background: "white",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  marginBottom: 8,
                }}
              >
                <span
                  style={{
                    fontSize: 11,
                    fontWeight: 600,
                    textTransform: "uppercase",
                    color: "#6b7280",
                    background: "#f3f4f6",
                    padding: "2px 8px",
                    borderRadius: 4,
                  }}
                >
                  {entry.entity_type}
                </span>
              </div>
              <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 4 }}>
                {String(
                  entry.properties.name ??
                    entry.properties.title ??
                    entry.entry_id,
                )}
              </div>
              <div style={{ fontSize: 12, color: "#6b7280", lineHeight: 1.4 }}>
                {String(
                  entry.properties.description ??
                    entry.properties.summary ??
                    "",
                ).slice(0, 120)}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      <div
        data-testid="pagination"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginTop: 16,
          fontSize: 12,
          color: "#6b7280",
        }}
      >
        <span>
          {total} entries, page {page + 1} of {totalPages}
        </span>
        <div style={{ display: "flex", gap: 4 }}>
          <button
            data-testid="prev-page"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            style={{
              padding: "4px 8px",
              border: "1px solid #d1d5db",
              borderRadius: 4,
              cursor: page === 0 ? "not-allowed" : "pointer",
              opacity: page === 0 ? 0.5 : 1,
            }}
          >
            Prev
          </button>
          <button
            data-testid="next-page"
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
            style={{
              padding: "4px 8px",
              border: "1px solid #d1d5db",
              borderRadius: 4,
              cursor: page >= totalPages - 1 ? "not-allowed" : "pointer",
              opacity: page >= totalPages - 1 ? 0.5 : 1,
            }}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
