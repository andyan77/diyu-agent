"use client";

/**
 * User management page: search, filter, paginate, bulk operations.
 *
 * Task card: FA2-1
 */

import { useEffect, useState } from "react";
import { DataTable, type Column } from "@/components/DataTable";
import { getAdminClient } from "@/lib/api";

interface User {
  id: string;
  name: string;
  email: string;
  role: string;
  status: "active" | "disabled";
  createdAt: string;
}

const columns: Column<User>[] = [
  { key: "name", header: "Name" },
  { key: "email", header: "Email" },
  { key: "role", header: "Role" },
  {
    key: "status",
    header: "Status",
    render: (row) => (
      <span
        style={{
          color: row.status === "active" ? "#22c55e" : "#ef4444",
          fontWeight: 500,
        }}
      >
        {row.status}
      </span>
    ),
  },
  { key: "createdAt", header: "Created" },
];

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        setLoading(true);
        const client = getAdminClient();
        const data = await client.get<User[]>("/admin/users");
        setUsers(data);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load users");
      } finally {
        setLoading(false);
      }
    };

    void fetchUsers();
  }, []);

  if (loading) {
    return (
      <div style={{ padding: 24, maxWidth: 1200 }}>
        <h1 style={{ fontSize: 20, fontWeight: 600, marginBottom: 16 }}>
          User Management
        </h1>
        <p>Loading users...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 24, maxWidth: 1200 }}>
        <h1 style={{ fontSize: 20, fontWeight: 600, marginBottom: 16 }}>
          User Management
        </h1>
        <p style={{ color: "#ef4444" }}>Error: {error}</p>
      </div>
    );
  }

  return (
    <div style={{ padding: 24, maxWidth: 1200 }}>
      <h1 style={{ fontSize: 20, fontWeight: 600, marginBottom: 16 }}>
        User Management
      </h1>
      <DataTable
        data={users}
        columns={columns}
        searchField="name"
        pageSize={10}
        bulkActions={[
          {
            label: "Disable",
            action: (ids) => {
              // Placeholder: would call admin API
              void ids;
            },
          },
          {
            label: "Enable",
            action: (ids) => {
              void ids;
            },
          },
        ]}
      />
    </div>
  );
}
