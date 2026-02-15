import { describe, it, expect } from "vitest";
import {
  DEPLOY_MODES,
  API_VERSION,
  WS_RECONNECT_INTERVAL_MS,
  WS_MAX_RECONNECT_ATTEMPTS,
  MESSAGE_TYPES,
} from "./constants";

describe("shared constants", () => {
  it("DEPLOY_MODES contains saas and private", () => {
    expect(DEPLOY_MODES).toContain("saas");
    expect(DEPLOY_MODES).toContain("private");
    expect(DEPLOY_MODES.length).toBe(2);
  });

  it("API_VERSION is v1", () => {
    expect(API_VERSION).toBe("v1");
  });

  it("WS reconnect defaults are sane", () => {
    expect(WS_RECONNECT_INTERVAL_MS).toBeGreaterThan(0);
    expect(WS_MAX_RECONNECT_ATTEMPTS).toBeGreaterThan(0);
  });

  it("MESSAGE_TYPES includes user and assistant", () => {
    expect(MESSAGE_TYPES).toContain("user");
    expect(MESSAGE_TYPES).toContain("assistant");
    expect(MESSAGE_TYPES).toContain("system");
    expect(MESSAGE_TYPES.length).toBeGreaterThanOrEqual(4);
  });
});
