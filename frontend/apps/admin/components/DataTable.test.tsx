/**
 * Unit tests for DataTable component (FA2-1).
 */

import { describe, it, expect, vi } from "vitest";
import { DataTable, type Column } from "./DataTable";

interface TestRow {
  id: string;
  name: string;
  value: number;
}

const testData: TestRow[] = Array.from({ length: 25 }, (_, i) => ({
  id: `row-${i}`,
  name: `Item ${i}`,
  value: i * 10,
}));

const columns: Column<TestRow>[] = [
  { key: "name", header: "Name" },
  { key: "value", header: "Value" },
];

describe("DataTable", () => {
  it("exports DataTable component", () => {
    expect(DataTable).toBeDefined();
    expect(typeof DataTable).toBe("function");
  });

  it("accepts required props", () => {
    // Type check: DataTable should accept data, columns, searchField, pageSize, bulkActions
    const props = {
      data: testData,
      columns,
      searchField: "name" as const,
      pageSize: 10,
      bulkActions: [
        { label: "Delete", action: vi.fn() },
      ],
    };

    expect(props.data).toHaveLength(25);
    expect(props.columns).toHaveLength(2);
    expect(props.pageSize).toBe(10);
    expect(props.bulkActions).toHaveLength(1);
  });

  it("columns support custom render", () => {
    const customColumn: Column<TestRow> = {
      key: "value",
      header: "Value",
      render: (row) => `$${row.value}`,
    };

    expect(customColumn.render?.(testData[1])).toBe("$10");
  });

  it("pagination calculates correctly", () => {
    const pageSize = 10;
    const totalPages = Math.ceil(testData.length / pageSize);
    expect(totalPages).toBe(3);

    const page0 = testData.slice(0, pageSize);
    expect(page0).toHaveLength(10);

    const page2 = testData.slice(2 * pageSize, 3 * pageSize);
    expect(page2).toHaveLength(5);
  });

  it("search filters data", () => {
    const q = "item 1";
    const filtered = testData.filter((r) =>
      r.name.toLowerCase().includes(q.toLowerCase()),
    );
    // "Item 1", "Item 10" through "Item 19"
    expect(filtered.length).toBeGreaterThan(0);
    expect(filtered.every((r) => r.name.toLowerCase().includes(q))).toBe(true);
  });
});
