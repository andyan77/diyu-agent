/**
 * Token management tests.
 *
 * Task card: FW1-4
 * Acceptance: pnpm test --filter web -- --grep token
 */

import { describe, it, expect, beforeEach } from "vitest";
import {
  createTokenStore,
  getAuthHeader,
  getDeployMode,
  type TokenStore,
} from "./token";

describe("token management", () => {
  describe("getDeployMode", () => {
    it("defaults to private when env not set", () => {
      const original = process.env.NEXT_PUBLIC_DEPLOY_MODE;
      delete process.env.NEXT_PUBLIC_DEPLOY_MODE;
      expect(getDeployMode()).toBe("private");
      if (original) process.env.NEXT_PUBLIC_DEPLOY_MODE = original;
    });

    it("returns saas when env is saas", () => {
      const original = process.env.NEXT_PUBLIC_DEPLOY_MODE;
      process.env.NEXT_PUBLIC_DEPLOY_MODE = "saas";
      expect(getDeployMode()).toBe("saas");
      if (original) {
        process.env.NEXT_PUBLIC_DEPLOY_MODE = original;
      } else {
        delete process.env.NEXT_PUBLIC_DEPLOY_MODE;
      }
    });
  });

  describe("private mode", () => {
    let store: TokenStore;

    beforeEach(() => {
      store = createTokenStore("private");
      store.clearToken();
    });

    it("has mode private", () => {
      expect(store.mode).toBe("private");
    });

    it("starts with null token", () => {
      expect(store.getToken()).toBeNull();
    });

    it("stores and retrieves token", () => {
      store.setToken("test-jwt-123");
      expect(store.getToken()).toBe("test-jwt-123");
    });

    it("clears token", () => {
      store.setToken("test-jwt-123");
      store.clearToken();
      expect(store.getToken()).toBeNull();
    });

    it("getAuthHeader returns Bearer token", () => {
      store.setToken("abc");
      expect(getAuthHeader(store)).toBe("Bearer abc");
    });

    it("getAuthHeader returns undefined when no token", () => {
      expect(getAuthHeader(store)).toBeUndefined();
    });
  });

  describe("saas mode", () => {
    let store: TokenStore;

    beforeEach(() => {
      store = createTokenStore("saas");
    });

    it("has mode saas", () => {
      expect(store.mode).toBe("saas");
    });

    it("getToken returns null (HttpOnly cookie)", () => {
      expect(store.getToken()).toBeNull();
    });

    it("setToken is no-op", () => {
      store.setToken("should-be-ignored");
      expect(store.getToken()).toBeNull();
    });

    it("clearToken is no-op", () => {
      store.clearToken();
      expect(store.getToken()).toBeNull();
    });

    it("getAuthHeader returns undefined (cookies handle auth)", () => {
      expect(getAuthHeader(store)).toBeUndefined();
    });
  });
});
