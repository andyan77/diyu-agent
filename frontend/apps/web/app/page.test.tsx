import { describe, it, expect } from "vitest";
import Home from "./page";

describe("web Home page", () => {
  it("exports a default function component", () => {
    expect(typeof Home).toBe("function");
  });

  it("has the expected function name", () => {
    expect(Home.name).toBe("Home");
  });
});
