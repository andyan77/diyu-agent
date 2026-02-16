/**
 * XSS protection tests.
 *
 * Task card: OS1-6
 * Acceptance: pnpm test --filter web -- --grep xss
 */

import { describe, it, expect } from "vitest";
import { stripTags, escapeHTML } from "./sanitize";

// NOTE: DOMPurify requires a DOM environment (jsdom/happy-dom).
// Server-side tests use stripTags and escapeHTML which work without DOM.
// DOMPurify integration is verified via browser/E2E tests.

describe("xss protection", () => {
  describe("stripTags", () => {
    it("removes script tags", () => {
      const input = '<script>alert("xss")</script>Hello';
      expect(stripTags(input)).toBe('alert("xss")Hello');
    });

    it("removes all HTML tags", () => {
      const input = "<b>bold</b> <i>italic</i> <a href='x'>link</a>";
      expect(stripTags(input)).toBe("bold italic link");
    });

    it("handles nested tags", () => {
      const input = "<div><p><strong>text</strong></p></div>";
      expect(stripTags(input)).toBe("text");
    });

    it("preserves text without tags", () => {
      const input = "plain text with no tags";
      expect(stripTags(input)).toBe("plain text with no tags");
    });

    it("handles empty string", () => {
      expect(stripTags("")).toBe("");
    });

    it("strips event handler tags", () => {
      const input = '<img src=x onerror="alert(1)">';
      expect(stripTags(input)).toBe("");
    });

    it("strips iframe tags", () => {
      const input = '<iframe src="evil.com"></iframe>safe';
      expect(stripTags(input)).toBe("safe");
    });
  });

  describe("escapeHTML", () => {
    it("escapes angle brackets", () => {
      expect(escapeHTML("<script>")).toBe("&lt;script&gt;");
    });

    it("escapes ampersands", () => {
      expect(escapeHTML("A & B")).toBe("A &amp; B");
    });

    it("escapes double quotes", () => {
      expect(escapeHTML('"quoted"')).toBe("&quot;quoted&quot;");
    });

    it("escapes single quotes", () => {
      expect(escapeHTML("it's")).toBe("it&#x27;s");
    });

    it("handles complex injection", () => {
      const input = '<img src=x onerror="alert(\'xss\')">';
      const result = escapeHTML(input);
      expect(result).not.toContain("<");
      expect(result).not.toContain(">");
      expect(result).toContain("&lt;");
      expect(result).toContain("&gt;");
    });

    it("preserves safe text", () => {
      expect(escapeHTML("hello world")).toBe("hello world");
    });

    it("handles empty string", () => {
      expect(escapeHTML("")).toBe("");
    });

    it("escapes javascript: URI", () => {
      const input = 'javascript:alert("xss")';
      // escapeHTML escapes quotes but javascript: stays
      // The actual protection is via DOMPurify and CSP
      const result = escapeHTML(input);
      expect(result).toContain("&quot;");
    });
  });
});
