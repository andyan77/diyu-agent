"use client";

/**
 * Audit log viewer: filter by time, user, operation type.
 *
 * Task card: FA2-3
 * Dependencies: audit_events (I1-5)
 */

import { useEffect, useMemo, useState } from "react";
import { getAdminClient } from "@/lib/api";

interface AuditEntry {
  id: string;
  userId: string;
  userName: string;
  action: string;
  resource: string;
  timestamp: string;
  details?: string;
}

const ACTION_TYPES = ["all", "create", "update", "delete", "login", "logout"];

export default function AuditPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionFilter, setActionFilter] = useState("all");
  const [userFilter, setUserFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  useEffect(() => {
    const fetchAuditLogs = async () => {
      try {
        setLoading(true);
        const client = getAdminClient();
        const data = await client.get<AuditEntry[]>("/admin/audit-logs");
        setEntries(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load audit logs");
      } finally {
        setLoading(false);
      }
    };

    void fetchAuditLogs();
  }, []);

  const filtered = useMemo(() => {
    let result = entries;

    if (actionFilter !== "all") {
      result = result.filter((e) => e.action === actionFilter);
    }

    if (userFilter.trim()) {
      const q = userFilter.toLowerCase();
      result = result.filter((e) => e.userName.toLowerCase().includes(q));
    }

    if (dateFrom) {
      const from = new Date(dateFrom).getTime();
      result = result.filter((e) => new Date(e.timestamp).getTime() >= from);
    }

    if (dateTo) {
      const to = new Date(dateTo).getTime() + 86400000; // end of day
      result = result.filter((e) => new Date(e.timestamp).getTime() <= to);
    }

    return result;
  }, [entries, actionFilter, userFilter, dateFrom, dateTo]);

  if (loading) {
    return (
      <div style={{ padding: 24, maxWidth: 1200 }}>
        <h1 style={{ fontSize: 20, fontWeight: 600, marginBottom: 16 }}>
          Audit Log
        </h1>
        <p>Loading audit logs...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 24, maxWidth: 1200 }}>
        <h1 style={{ fontSize: 20, fontWeight: 600, marginBottom: 16 }}>
          Audit Log
        </h1>
        <p style={{ color: "#ef4444" }}>Error: {error}</p>
      </div>
    );
  }

  return (
    <div style={{ padding: 24, maxWidth: 1200 }}>
      <h1 style={{ fontSize: 20, fontWeight: 600, marginBottom: 16 }}>
        Audit Log
      </h1>

      {/* Filters */}
      <div
        data-testid="audit-filters"
        style={{
          display: "flex",
          gap: 12,
          marginBottom: 16,
          flexWrap: "wrap",
          alignItems: "center",
        }}
      >
        <div>
          <label
            htmlFor="action-filter"
            style={{ fontSize: 12, color: "#6b7280", display: "block" }}
          >
            Action
          </label>
          <select
            id="action-filter"
            data-testid="action-filter"
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            style={{
              padding: "6px 10px",
              border: "1px solid #d1d5db",
              borderRadius: 4,
            }}
          >
            {ACTION_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label
            htmlFor="user-filter"
            style={{ fontSize: 12, color: "#6b7280", display: "block" }}
          >
            User
          </label>
          <input
            id="user-filter"
            data-testid="user-filter"
            type="text"
            placeholder="Filter by user..."
            value={userFilter}
            onChange={(e) => setUserFilter(e.target.value)}
            style={{
              padding: "6px 10px",
              border: "1px solid #d1d5db",
              borderRadius: 4,
            }}
          />
        </div>

        <div>
          <label
            htmlFor="date-from"
            style={{ fontSize: 12, color: "#6b7280", display: "block" }}
          >
            From
          </label>
          <input
            id="date-from"
            data-testid="date-from"
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            style={{
              padding: "6px 10px",
              border: "1px solid #d1d5db",
              borderRadius: 4,
            }}
          />
        </div>

        <div>
          <label
            htmlFor="date-to"
            style={{ fontSize: 12, color: "#6b7280", display: "block" }}
          >
            To
          </label>
          <input
            id="date-to"
            data-testid="date-to"
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            style={{
              padding: "6px 10px",
              border: "1px solid #d1d5db",
              borderRadius: 4,
            }}
          />
        </div>

        <div style={{ fontSize: 12, color: "#6b7280", alignSelf: "flex-end" }}>
          {filtered.length} results
        </div>
      </div>

      {/* Table */}
      <table
        data-testid="audit-table"
        style={{ width: "100%", borderCollapse: "collapse" }}
      >
        <thead>
          <tr style={{ borderBottom: "2px solid #e5e7eb" }}>
            <th
              style={{
                padding: "8px 12px",
                textAlign: "left",
                fontSize: 12,
                fontWeight: 600,
                color: "#6b7280",
              }}
            >
              Timestamp
            </th>
            <th
              style={{
                padding: "8px 12px",
                textAlign: "left",
                fontSize: 12,
                fontWeight: 600,
                color: "#6b7280",
              }}
            >
              User
            </th>
            <th
              style={{
                padding: "8px 12px",
                textAlign: "left",
                fontSize: 12,
                fontWeight: 600,
                color: "#6b7280",
              }}
            >
              Action
            </th>
            <th
              style={{
                padding: "8px 12px",
                textAlign: "left",
                fontSize: 12,
                fontWeight: 600,
                color: "#6b7280",
              }}
            >
              Resource
            </th>
            <th
              style={{
                padding: "8px 12px",
                textAlign: "left",
                fontSize: 12,
                fontWeight: 600,
                color: "#6b7280",
              }}
            >
              Details
            </th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((entry) => (
            <tr
              key={entry.id}
              data-testid={`audit-${entry.id}`}
              style={{ borderBottom: "1px solid #f3f4f6" }}
            >
              <td style={{ padding: "8px 12px", fontSize: 12 }}>
                {new Date(entry.timestamp).toLocaleString()}
              </td>
              <td style={{ padding: "8px 12px", fontSize: 13 }}>
                {entry.userName}
              </td>
              <td style={{ padding: "8px 12px", fontSize: 13 }}>
                <span
                  style={{
                    padding: "2px 6px",
                    borderRadius: 4,
                    fontSize: 11,
                    background:
                      entry.action === "delete"
                        ? "#fee2e2"
                        : entry.action === "create"
                          ? "#dcfce7"
                          : "#f3f4f6",
                    color:
                      entry.action === "delete"
                        ? "#dc2626"
                        : entry.action === "create"
                          ? "#16a34a"
                          : "#374151",
                  }}
                >
                  {entry.action}
                </span>
              </td>
              <td style={{ padding: "8px 12px", fontSize: 13 }}>
                {entry.resource}
              </td>
              <td style={{ padding: "8px 12px", fontSize: 12, color: "#6b7280" }}>
                {entry.details ?? "-"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
