import { describe, it, expect } from "vitest";
import { Button } from "./button";

describe("Button", () => {
  it("is a function component", () => {
    expect(typeof Button).toBe("function");
  });

  it("has correct display name or function name", () => {
    expect(Button.name).toBe("Button");
  });
});
