"use client";

/**
 * User management page: search, filter, paginate, bulk operations.
 *
 * Task card: FA2-1
 */

import { useState } from "react";
import { DataTable, type Column } from "@/components/DataTable";

interface User {
  id: string;
  name: string;
  email: string;
  role: string;
  status: "active" | "disabled";
  createdAt: string;
}

const MOCK_USERS: User[] = Array.from({ length: 25 }, (_, i) => ({
  id: `user-${i + 1}`,
  name: `User ${i + 1}`,
  email: `user${i + 1}@example.com`,
  role: i === 0 ? "admin" : "member",
  status: i % 5 === 0 ? "disabled" : "active",
  createdAt: new Date(Date.now() - i * 86400000).toISOString(),
}));

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
  const [users] = useState<User[]>(MOCK_USERS);

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
