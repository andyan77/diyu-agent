"use client";

/**
 * Organization management page: CRUD orgs, view members, view usage.
 *
 * Task card: FA2-2
 */

import { useCallback, useEffect, useState } from "react";
import { getAdminClient } from "@/lib/api";

interface Organization {
  id: string;
  name: string;
  memberCount: number;
  tokenUsage: number;
  createdAt: string;
}

export default function OrganizationsPage() {
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [formName, setFormName] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);

  useEffect(() => {
    const fetchOrgs = async () => {
      try {
        setLoading(true);
        const client = getAdminClient();
        const data = await client.get<Organization[]>("/admin/organizations");
        setOrgs(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load organizations");
      } finally {
        setLoading(false);
      }
    };

    void fetchOrgs();
  }, []);

  const handleCreate = useCallback(async () => {
    if (!formName.trim()) return;
    try {
      const client = getAdminClient();
      const newOrg = await client.post<Organization>("/admin/organizations", {
        name: formName.trim(),
      });
      setOrgs((prev) => [...prev, newOrg]);
      setFormName("");
      setShowForm(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create organization");
    }
  }, [formName]);

  const handleUpdate = useCallback(
    async (id: string) => {
      if (!formName.trim()) return;
      try {
        const client = getAdminClient();
        const updated = await client.put<Organization>(`/admin/organizations/${id}`, {
          name: formName.trim(),
        });
        setOrgs((prev) =>
          prev.map((o) => (o.id === id ? updated : o)),
        );
        setFormName("");
        setEditingId(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to update organization");
      }
    },
    [formName],
  );

  const handleDelete = useCallback(async (id: string) => {
    try {
      const client = getAdminClient();
      await client.delete(`/admin/organizations/${id}`);
      setOrgs((prev) => prev.filter((o) => o.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete organization");
    }
  }, []);

  if (loading) {
    return (
      <div style={{ padding: 24, maxWidth: 1200 }}>
        <h1 style={{ fontSize: 20, fontWeight: 600, marginBottom: 16 }}>
          Organizations
        </h1>
        <p>Loading organizations...</p>
      </div>
    );
  }

  return (
    <div style={{ padding: 24, maxWidth: 1200 }}>
      {error && (
        <div style={{ padding: 12, marginBottom: 16, background: "#fee2e2", color: "#dc2626", borderRadius: 4 }}>
          {error}
        </div>
      )}
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
