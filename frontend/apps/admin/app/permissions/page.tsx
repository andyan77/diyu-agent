"use client";

/**
 * Permission matrix management page.
 *
 * Task card: FA1-2
 * - View role-permission matrix
 * - Edit role permissions (admin only)
 * - Visual grid of roles x permissions
 *
 * Dependencies: RBAC (I1-4)
 */

import { useCallback, useState } from "react";

// --- Types ---

interface PermissionEntry {
  permission: string;
  label: string;
}

interface RolePermissions {
  role: string;
  label: string;
  permissions: Set<string>;
}

// --- Default matrix matching I1-4 RBAC skeleton ---

const PERMISSIONS: PermissionEntry[] = [
  { permission: "read", label: "Read" },
  { permission: "write", label: "Write" },
  { permission: "admin:access", label: "Admin Access" },
  { permission: "manage:members", label: "Manage Members" },
  { permission: "manage:settings", label: "Manage Settings" },
  { permission: "manage:roles", label: "Manage Roles" },
  { permission: "admin:billing", label: "Admin Billing" },
  { permission: "admin:system", label: "Admin System" },
];

const DEFAULT_ROLES: RolePermissions[] = [
  {
    role: "super_admin",
    label: "Super Admin",
    permissions: new Set(PERMISSIONS.map((p) => p.permission)),
  },
  {
    role: "org_admin",
    label: "Org Admin",
    permissions: new Set([
      "read",
      "write",
      "admin:access",
      "manage:members",
      "manage:settings",
      "manage:roles",
      "admin:billing",
    ]),
  },
  {
    role: "manager",
    label: "Manager",
    permissions: new Set(["read", "write", "manage:members"]),
  },
  {
    role: "member",
    label: "Member",
    permissions: new Set(["read", "write"]),
  },
  {
    role: "viewer",
    label: "Viewer",
    permissions: new Set(["read"]),
  },
];

export default function PermissionsPage() {
  const [roles, setRoles] = useState<RolePermissions[]>(DEFAULT_ROLES);
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  const togglePermission = useCallback(
    (roleIndex: number, permission: string) => {
      setRoles((prev) => {
        const updated = [...prev];
        const role = { ...updated[roleIndex] };
        const perms = new Set(role.permissions);
        if (perms.has(permission)) {
          perms.delete(permission);
        } else {
          perms.add(permission);
        }
        role.permissions = perms;
        updated[roleIndex] = role;
        return updated;
      });
      setSaveMessage(null);
    },
    [],
  );

  const handleSave = useCallback(async () => {
    setIsSaving(true);
    setSaveMessage(null);
    try {
      const payload = roles.map((r) => ({
        role: r.role,
        permissions: Array.from(r.permissions),
      }));

      const token =
        typeof window !== "undefined"
          ? sessionStorage.getItem("token")
          : null;

      const response = await fetch("/api/v1/admin/permissions", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ roles: payload }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.message || `Save failed: ${response.status}`);
      }

      setSaveMessage("Permissions saved successfully.");
    } catch (err) {
      setSaveMessage(
        err instanceof Error ? err.message : "Failed to save permissions.",
      );
    } finally {
      setIsSaving(false);
    }
  }, [roles]);

  return (
    <div style={{ padding: "2rem" }}>
      <h1>Permission Matrix</h1>
      <p>Manage role-based permissions for your organization.</p>

      <table
        data-testid="permission-matrix"
        style={{
          borderCollapse: "collapse",
          width: "100%",
          marginTop: "1rem",
        }}
      >
        <thead>
          <tr>
            <th style={{ textAlign: "left", padding: "0.5rem" }}>
              Permission
            </th>
            {roles.map((r) => (
              <th key={r.role} style={{ padding: "0.5rem", textAlign: "center" }}>
                {r.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {PERMISSIONS.map((p) => (
            <tr key={p.permission}>
              <td style={{ padding: "0.5rem" }}>{p.label}</td>
              {roles.map((r, ri) => (
                <td
                  key={r.role}
                  style={{ padding: "0.5rem", textAlign: "center" }}
                >
                  <input
                    type="checkbox"
                    checked={r.permissions.has(p.permission)}
                    onChange={() => togglePermission(ri, p.permission)}
                    aria-label={`${r.label} - ${p.label}`}
                    data-testid={`perm-${r.role}-${p.permission}`}
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>

      <div style={{ marginTop: "1rem" }}>
        <button
          type="button"
          onClick={handleSave}
          disabled={isSaving}
          data-testid="save-permissions"
        >
          {isSaving ? "Saving..." : "Save Changes"}
        </button>
      </div>

      {saveMessage && (
        <p data-testid="save-message" style={{ marginTop: "0.5rem" }}>
          {saveMessage}
        </p>
      )}
    </div>
  );
}
