"use client";

/**
 * Knowledge editor workbench: create, edit, delete knowledge entries.
 *
 * Task card: FA3-1
 * API: POST/GET/PUT/DELETE /api/v1/admin/knowledge (G3-1)
 */

import { useCallback, useEffect, useState } from "react";
import { DataTable, type Column } from "@/components/DataTable";

interface KnowledgeEntry {
  id: string;
  entity_type: string;
  name: string;
  status: "published" | "draft" | "archived";
  updatedAt: string;
}

const MOCK_ENTRIES: KnowledgeEntry[] = Array.from({ length: 30 }, (_, i) => ({
  id: `entry-${i + 1}`,
  entity_type: ["product", "brand", "category", "style"][i % 4] ?? "product",
  name: `Knowledge Entry ${i + 1}`,
  status: (["published", "draft", "archived"][i % 3] ?? "published") as KnowledgeEntry["status"],
  updatedAt: new Date(Date.now() - i * 86400000).toISOString().slice(0, 10),
}));

const columns: Column<KnowledgeEntry>[] = [
  { key: "name", header: "Name" },
  { key: "entity_type", header: "Type" },
  {
    key: "status",
    header: "Status",
    render: (row) => {
      const colors: Record<string, string> = {
        published: "#22c55e",
        draft: "#f59e0b",
        archived: "#6b7280",
      };
      return (
        <span style={{ color: colors[row.status] ?? "#374151", fontWeight: 500 }}>
          {row.status}
        </span>
      );
    },
  },
  { key: "updatedAt", header: "Updated" },
];

export default function KnowledgeEditorPage() {
  const [entries, setEntries] = useState<KnowledgeEntry[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newType, setNewType] = useState("product");

  useEffect(() => {
    // Placeholder: would fetch from Knowledge Admin API (G3-1)
    setEntries(MOCK_ENTRIES);
  }, []);

  const handleCreate = useCallback(() => {
    if (!newName.trim()) return;
    const entry: KnowledgeEntry = {
      id: `entry-${Date.now()}`,
      entity_type: newType,
      name: newName.trim(),
      status: "draft",
      updatedAt: new Date().toISOString().slice(0, 10),
    };
    setEntries((prev) => [entry, ...prev]);
    setNewName("");
    setShowCreate(false);
  }, [newName, newType]);

  return (
    <div style={{ padding: 24, maxWidth: 1200 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <h1
          data-testid="knowledge-editor-title"
          style={{ fontSize: 20, fontWeight: 600 }}
        >
          Knowledge Editor
        </h1>
        <button
          data-testid="create-entry-btn"
          onClick={() => setShowCreate((prev) => !prev)}
          style={{
            padding: "8px 16px",
            background: "#3b82f6",
            color: "white",
            border: "none",
            borderRadius: 6,
            cursor: "pointer",
            fontSize: 13,
          }}
        >
          {showCreate ? "Cancel" : "Create Entry"}
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <div
          data-testid="create-form"
          style={{
            border: "1px solid #e5e7eb",
            borderRadius: 8,
            padding: 16,
            marginBottom: 16,
            display: "flex",
            gap: 12,
            alignItems: "end",
          }}
        >
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: 12, color: "#6b7280", display: "block", marginBottom: 4 }}>
              Name
            </label>
            <input
              data-testid="entry-name-input"
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Entry name"
              aria-label="Entry name"
              style={{
                width: "100%",
                padding: "6px 10px",
                border: "1px solid #d1d5db",
                borderRadius: 4,
              }}
            />
          </div>
          <div>
            <label style={{ fontSize: 12, color: "#6b7280", display: "block", marginBottom: 4 }}>
              Type
            </label>
            <select
              data-testid="entry-type-select"
              value={newType}
              onChange={(e) => setNewType(e.target.value)}
              aria-label="Entity type"
              style={{
                padding: "6px 10px",
                border: "1px solid #d1d5db",
                borderRadius: 4,
              }}
            >
              <option value="product">Product</option>
              <option value="brand">Brand</option>
              <option value="category">Category</option>
              <option value="style">Style</option>
            </select>
          </div>
          <button
            data-testid="submit-entry-btn"
            onClick={handleCreate}
            disabled={!newName.trim()}
            style={{
              padding: "6px 16px",
              background: newName.trim() ? "#22c55e" : "#d1d5db",
              color: "white",
              border: "none",
              borderRadius: 4,
              cursor: newName.trim() ? "pointer" : "not-allowed",
            }}
          >
            Save
          </button>
        </div>
      )}

      <DataTable
        data={entries}
        columns={columns}
        searchField="name"
        pageSize={10}
        bulkActions={[
          {
            label: "Publish",
            action: (ids) => {
              setEntries((prev) =>
                prev.map((e) => (ids.includes(e.id) ? { ...e, status: "published" as const } : e)),
              );
            },
          },
          {
            label: "Archive",
            action: (ids) => {
              setEntries((prev) =>
                prev.map((e) => (ids.includes(e.id) ? { ...e, status: "archived" as const } : e)),
              );
            },
          },
          {
            label: "Delete",
            action: (ids) => {
              setEntries((prev) => prev.filter((e) => !ids.includes(e.id)));
            },
          },
        ]}
      />
    </div>
  );
}
