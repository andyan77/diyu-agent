/**
 * Unit tests for audit log filtering logic (FA2-3).
 */

import { describe, it, expect } from "vitest";

interface AuditEntry {
  id: string;
  userId: string;
  userName: string;
  action: string;
  resource: string;
  timestamp: string;
}

const entries: AuditEntry[] = [
  {
    id: "1",
    userId: "u1",
    userName: "Alice",
    action: "create",
    resource: "conversation",
    timestamp: "2026-02-17T10:00:00Z",
  },
  {
    id: "2",
    userId: "u2",
    userName: "Bob",
    action: "delete",
    resource: "user",
    timestamp: "2026-02-17T11:00:00Z",
  },
  {
    id: "3",
    userId: "u1",
    userName: "Alice",
    action: "update",
    resource: "organization",
    timestamp: "2026-02-17T12:00:00Z",
  },
  {
    id: "4",
    userId: "u3",
    userName: "Charlie",
    action: "login",
    resource: "session",
    timestamp: "2026-02-16T09:00:00Z",
  },
];

function filterEntries(
  data: AuditEntry[],
  opts: { action?: string; user?: string; dateFrom?: string; dateTo?: string },
): AuditEntry[] {
  let result = data;

  if (opts.action && opts.action !== "all") {
    result = result.filter((e) => e.action === opts.action);
  }

  if (opts.user) {
    const q = opts.user.toLowerCase();
    result = result.filter((e) => e.userName.toLowerCase().includes(q));
  }

  if (opts.dateFrom) {
    const from = new Date(opts.dateFrom).getTime();
    result = result.filter((e) => new Date(e.timestamp).getTime() >= from);
  }

  if (opts.dateTo) {
    const to = new Date(opts.dateTo).getTime() + 86400000;
    result = result.filter((e) => new Date(e.timestamp).getTime() <= to);
  }

  return result;
}

describe("Audit log filtering", () => {
  it("filters by action type", () => {
    const result = filterEntries(entries, { action: "create" });
    expect(result).toHaveLength(1);
    expect(result[0].action).toBe("create");
  });

  it("filters by user name", () => {
    const result = filterEntries(entries, { user: "alice" });
    expect(result).toHaveLength(2);
    expect(result.every((e) => e.userName === "Alice")).toBe(true);
  });

  it("filters by date range", () => {
    const result = filterEntries(entries, {
      dateFrom: "2026-02-17",
      dateTo: "2026-02-17",
    });
    expect(result).toHaveLength(3);
    expect(result.every((e) => e.timestamp.startsWith("2026-02-17"))).toBe(
      true,
    );
  });

  it("combines multiple filters", () => {
    const result = filterEntries(entries, {
      action: "create",
      user: "alice",
    });
    expect(result).toHaveLength(1);
  });

  it("action=all returns everything", () => {
    const result = filterEntries(entries, { action: "all" });
    expect(result).toHaveLength(4);
  });

  it("empty filters return all entries", () => {
    const result = filterEntries(entries, {});
    expect(result).toHaveLength(4);
  });
});
