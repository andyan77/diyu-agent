import { describe, it, expect } from "vitest";
import AdminHome from "./page";

describe("admin AdminHome page", () => {
  it("exports a default function component", () => {
    expect(typeof AdminHome).toBe("function");
  });

  it("has the expected function name", () => {
    expect(AdminHome.name).toBe("AdminHome");
  });
});
