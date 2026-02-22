"use client";

/**
 * Reusable DataTable component with search, filter, pagination, bulk actions.
 *
 * Task card: FA2-1
 */

import { useMemo, useState } from "react";

export interface Column<T> {
  key: string;
  header: string;
  render?: (row: T) => React.ReactNode;
}

interface DataTableProps<T extends { id: string }> {
  data: T[];
  columns: Column<T>[];
  searchField?: keyof T;
  pageSize?: number;
  bulkActions?: { label: string; action: (ids: string[]) => void | Promise<void> }[];
}

export function DataTable<T extends { id: string }>({
  data,
  columns,
  searchField,
  pageSize = 10,
  bulkActions,
}: DataTableProps<T>) {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const filtered = useMemo(() => {
    if (!search.trim() || !searchField) return data;
    const q = search.toLowerCase();
    return data.filter((row) => {
      const val = row[searchField];
      return typeof val === "string" && val.toLowerCase().includes(q);
    });
  }, [data, search, searchField]);

  const totalPages = Math.ceil(filtered.length / pageSize);
  const pageData = filtered.slice(page * pageSize, (page + 1) * pageSize);

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selected.size === pageData.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(pageData.map((r) => r.id)));
    }
  };

  return (
    <div data-testid="data-table">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 12,
        }}
      >
        {searchField && (
          <input
            data-testid="table-search"
            type="text"
            placeholder="Search..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(0);
            }}
            aria-label="Search table"
            style={{
              padding: "6px 10px",
              border: "1px solid #d1d5db",
              borderRadius: 4,
            }}
          />
        )}
        {bulkActions && selected.size > 0 && (
          <div style={{ display: "flex", gap: 8 }}>
            {bulkActions.map((action) => (
              <button
                key={action.label}
                data-testid={`bulk-${action.label.toLowerCase().replace(/\s+/g, "-")}`}
                onClick={() => action.action(Array.from(selected))}
                style={{
                  padding: "4px 10px",
                  border: "1px solid #d1d5db",
                  borderRadius: 4,
                  cursor: "pointer",
                  fontSize: 12,
                }}
              >
                {action.label} ({selected.size})
              </button>
            ))}
          </div>
        )}
      </div>

      <table
        style={{ width: "100%", borderCollapse: "collapse" }}
        data-testid="table-body"
      >
        <thead>
          <tr style={{ borderBottom: "2px solid #e5e7eb" }}>
            {bulkActions && (
              <th style={{ width: 40, padding: "8px 4px" }}>
                <input
                  type="checkbox"
                  data-testid="select-all"
                  checked={selected.size === pageData.length && pageData.length > 0}
                  onChange={toggleSelectAll}
                  aria-label="Select all"
                />
              </th>
            )}
            {columns.map((col) => (
              <th
                key={col.key}
                style={{
                  padding: "8px 12px",
                  textAlign: "left",
                  fontSize: 12,
                  fontWeight: 600,
                  color: "#6b7280",
                  textTransform: "uppercase",
                }}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {pageData.map((row) => (
            <tr
              key={row.id}
              data-testid={`row-${row.id}`}
              style={{ borderBottom: "1px solid #f3f4f6" }}
            >
              {bulkActions && (
                <td style={{ padding: "8px 4px" }}>
                  <input
                    type="checkbox"
                    checked={selected.has(row.id)}
                    onChange={() => toggleSelect(row.id)}
                    aria-label={`Select ${row.id}`}
                  />
                </td>
              )}
              {columns.map((col) => (
                <td key={col.key} style={{ padding: "8px 12px", fontSize: 13 }}>
                  {col.render
                    ? col.render(row)
                    : String((row as Record<string, unknown>)[col.key] ?? "")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>

      {/* Pagination */}
      <div
        data-testid="pagination"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginTop: 12,
          fontSize: 12,
          color: "#6b7280",
        }}
      >
        <span>
          {filtered.length} total, page {page + 1} of {Math.max(totalPages, 1)}
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
