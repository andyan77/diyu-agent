"use client";

/**
 * Skill structured rendering -- right-side Artifact panel.
 *
 * Task card: FW3-2
 * Renders structured Skill outputs (tables, JSON, charts placeholder)
 * as an expandable side panel in the chat view.
 */

import { useState } from "react";

export interface ArtifactData {
  id: string;
  skillName: string;
  type: "table" | "json" | "text" | "chart";
  title: string;
  content: unknown;
  createdAt: string;
}

interface ArtifactPanelProps {
  artifact: ArtifactData | null;
  isOpen: boolean;
  onClose: () => void;
}

function renderContent(artifact: ArtifactData): React.ReactNode {
  switch (artifact.type) {
    case "table": {
      const rows = artifact.content as Record<string, unknown>[];
      if (!rows || rows.length === 0) {
        return <div style={{ color: "#9ca3af" }}>No data</div>;
      }
      const headers = Object.keys(rows[0] ?? {});
      return (
        <table
          data-testid="artifact-table"
          style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}
        >
          <thead>
            <tr>
              {headers.map((h) => (
                <th
                  key={h}
                  style={{
                    padding: "6px 8px",
                    textAlign: "left",
                    borderBottom: "2px solid #e5e7eb",
                    fontSize: 11,
                    fontWeight: 600,
                    color: "#6b7280",
                    textTransform: "uppercase",
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} style={{ borderBottom: "1px solid #f3f4f6" }}>
                {headers.map((h) => (
                  <td key={h} style={{ padding: "6px 8px" }}>
                    {String(row[h] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      );
    }
    case "json":
      return (
        <pre
          data-testid="artifact-json"
          style={{
            background: "#f9fafb",
            padding: 12,
            borderRadius: 6,
            fontSize: 12,
            overflow: "auto",
            maxHeight: 400,
          }}
        >
          {JSON.stringify(artifact.content, null, 2)}
        </pre>
      );
    case "text":
      return (
        <div data-testid="artifact-text" style={{ whiteSpace: "pre-wrap", fontSize: 13 }}>
          {String(artifact.content)}
        </div>
      );
    case "chart":
      return (
        <div
          data-testid="artifact-chart-placeholder"
          style={{
            padding: 40,
            textAlign: "center",
            color: "#9ca3af",
            border: "1px dashed #d1d5db",
            borderRadius: 8,
          }}
        >
          Chart visualization (placeholder)
        </div>
      );
    default:
      return null;
  }
}

export function ArtifactPanel({ artifact, isOpen, onClose }: ArtifactPanelProps) {
  const [collapsed, setCollapsed] = useState(false);

  if (!isOpen || !artifact) return null;

  return (
    <div
      data-testid="artifact-panel"
      style={{
        width: collapsed ? 48 : 400,
        borderLeft: "1px solid #e5e7eb",
        background: "white",
        display: "flex",
        flexDirection: "column",
        transition: "width 0.2s",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "12px 16px",
          borderBottom: "1px solid #e5e7eb",
        }}
      >
        {!collapsed && (
          <div>
            <div style={{ fontSize: 14, fontWeight: 600 }}>{artifact.title}</div>
            <div style={{ fontSize: 11, color: "#9ca3af" }}>
              {artifact.skillName} &middot; {artifact.type}
            </div>
          </div>
        )}
        <div style={{ display: "flex", gap: 4 }}>
          <button
            data-testid="artifact-collapse"
            onClick={() => setCollapsed((prev) => !prev)}
            aria-label={collapsed ? "Expand panel" : "Collapse panel"}
            style={{
              padding: "4px 8px",
              border: "none",
              background: "none",
              cursor: "pointer",
              fontSize: 16,
            }}
          >
            {collapsed ? "\u25C0" : "\u25B6"}
          </button>
          <button
            data-testid="artifact-close"
            onClick={onClose}
            aria-label="Close artifact panel"
            style={{
              padding: "4px 8px",
              border: "none",
              background: "none",
              cursor: "pointer",
              fontSize: 16,
            }}
          >
            &times;
          </button>
        </div>
      </div>

      {/* Content */}
      {!collapsed && (
        <div style={{ flex: 1, overflow: "auto", padding: 16 }}>
          {renderContent(artifact)}
        </div>
      )}
    </div>
  );
}
