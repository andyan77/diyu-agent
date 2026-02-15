import { describe, it, expect } from "vitest";
import { createApiClient } from "./client";

describe("createApiClient", () => {
  it("returns an object with required methods", () => {
    const client = createApiClient("https://api.example.com");
    expect(client).toHaveProperty("get");
    expect(client).toHaveProperty("post");
    expect(client).toHaveProperty("put");
    expect(client).toHaveProperty("delete");
    expect(client).toHaveProperty("instance");
  });

  it("configures base URL on the axios instance", () => {
    const client = createApiClient("https://api.test.com");
    expect(client.instance.defaults.baseURL).toBe("https://api.test.com");
  });

  it("sets Authorization header when token is provided", () => {
    const client = createApiClient("https://api.test.com", "test-token");
    expect(client.instance.defaults.headers["Authorization"]).toBe(
      "Bearer test-token",
    );
  });

  it("does not set Authorization header when token is omitted", () => {
    const client = createApiClient("https://api.test.com");
    expect(
      client.instance.defaults.headers["Authorization"],
    ).toBeUndefined();
  });

  it("sets 30-second timeout", () => {
    const client = createApiClient("https://api.test.com");
    expect(client.instance.defaults.timeout).toBe(30_000);
  });
});
