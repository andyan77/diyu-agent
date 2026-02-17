"use client";

/**
 * Organization management page: CRUD orgs, view members, view usage.
 *
 * Task card: FA2-2
 */

import { useCallback, useState } from "react";

interface Organization {
  id: string;
  name: string;
  memberCount: number;
  tokenUsage: number;
  createdAt: string;
}

const MOCK_ORGS: Organization[] = [
  {
    id: "org-1",
    name: "Acme Corp",
    memberCount: 12,
    tokenUsage: 150000,
    createdAt: "2026-01-15T00:00:00Z",
  },
  {
    id: "org-2",
    name: "Globex Inc",
    memberCount: 5,
    tokenUsage: 42000,
    createdAt: "2026-02-01T00:00:00Z",
  },
];

export default function OrganizationsPage() {
  const [orgs, setOrgs] = useState<Organization[]>(MOCK_ORGS);
  const [showForm, setShowForm] = useState(false);
  const [formName, setFormName] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);

  const handleCreate = useCallback(() => {
    if (!formName.trim()) return;
    const newOrg: Organization = {
      id: `org-${crypto.randomUUID().slice(0, 8)}`,
      name: formName.trim(),
      memberCount: 0,
      tokenUsage: 0,
      createdAt: new Date().toISOString(),
    };
    setOrgs((prev) => [...prev, newOrg]);
    setFormName("");
    setShowForm(false);
  }, [formName]);

  const handleUpdate = useCallback(
    (id: string) => {
      if (!formName.trim()) return;
      setOrgs((prev) =>
        prev.map((o) => (o.id === id ? { ...o, name: formName.trim() } : o)),
      );
      setFormName("");
      setEditingId(null);
    },
    [formName],
  );

  const handleDelete = useCallback((id: string) => {
    setOrgs((prev) => prev.filter((o) => o.id !== id));
  }, []);

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
        <h1 style={{ fontSize: 20, fontWeight: 600 }}>Organizations</h1>
        <button
          data-testid="create-org"
          onClick={() => {
            setShowForm(true);
            setEditingId(null);
            setFormName("");
          }}
          style={{
            padding: "8px 16px",
            background: "#3b82f6",
            color: "white",
            border: "none",
            borderRadius: 4,
            cursor: "pointer",
          }}
        >
          New Organization
        </button>
      </div>

      {(showForm || editingId) && (
        <div
          data-testid="org-form"
          style={{
            padding: 16,
            border: "1px solid #e5e7eb",
            borderRadius: 8,
            marginBottom: 16,
          }}
        >
          <input
            data-testid="org-name-input"
            type="text"
            placeholder="Organization name"
            value={formName}
            onChange={(e) => setFormName(e.target.value)}
            aria-label="Organization name"
            style={{
              padding: "8px 12px",
              border: "1px solid #d1d5db",
              borderRadius: 4,
              marginRight: 8,
            }}
          />
          <button
            data-testid="save-org"
            onClick={() =>
              editingId ? handleUpdate(editingId) : handleCreate()
            }
            style={{
              padding: "8px 16px",
              background: "#22c55e",
              color: "white",
              border: "none",
              borderRadius: 4,
              cursor: "pointer",
            }}
          >
            {editingId ? "Update" : "Create"}
          </button>
          <button
            data-testid="cancel-org"
            onClick={() => {
              setShowForm(false);
              setEditingId(null);
            }}
            style={{
              padding: "8px 16px",
              background: "none",
              border: "1px solid #d1d5db",
              borderRadius: 4,
              cursor: "pointer",
              marginLeft: 8,
            }}
          >
            Cancel
          </button>
        </div>
      )}

      <div data-testid="org-list">
        {orgs.map((org) => (
          <div
            key={org.id}
            data-testid={`org-${org.id}`}
            style={{
              padding: 16,
              border: "1px solid #e5e7eb",
              borderRadius: 8,
              marginBottom: 8,
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div>
              <div style={{ fontWeight: 600 }}>{org.name}</div>
              <div style={{ fontSize: 12, color: "#6b7280", marginTop: 4 }}>
                {org.memberCount} members | {org.tokenUsage.toLocaleString()}{" "}
                tokens used
              </div>
            </div>
            <div style={{ display: "flex", gap: 8 }}>
              <button
                data-testid={`edit-org-${org.id}`}
                onClick={() => {
                  setEditingId(org.id);
                  setFormName(org.name);
                  setShowForm(false);
                }}
                style={{
                  padding: "4px 10px",
                  border: "1px solid #d1d5db",
                  borderRadius: 4,
                  cursor: "pointer",
                  fontSize: 12,
                }}
              >
                Edit
              </button>
              <button
                data-testid={`delete-org-${org.id}`}
                onClick={() => handleDelete(org.id)}
                style={{
                  padding: "4px 10px",
                  border: "1px solid #fca5a5",
                  borderRadius: 4,
                  cursor: "pointer",
                  fontSize: 12,
                  color: "#ef4444",
                }}
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
