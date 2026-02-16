/**
 * XSS sanitization utilities.
 *
 * Task card: OS1-6
 * - DOMPurify-based HTML sanitization
 * - Script tag injection -> stripped
 * - Event handler injection -> stripped
 * - Safe subset of HTML allowed (bold, italic, links, etc.)
 *
 * Dependencies: DOMPurify
 */

import DOMPurify from "dompurify";

/**
 * Sanitize HTML string, removing dangerous elements and attributes.
 *
 * Strips:
 * - <script> tags and their content
 * - Event handler attributes (onclick, onerror, etc.)
 * - javascript: URIs
 * - data: URIs (except images)
 * - <iframe>, <object>, <embed>, <form> tags
 *
 * Allows:
 * - Text formatting (b, i, em, strong, u, s, br, p, span)
 * - Lists (ul, ol, li)
 * - Links (a with href, target, rel)
 * - Images (img with src, alt, width, height)
 * - Headings (h1-h6)
 * - Code blocks (code, pre)
 */
export function sanitizeHTML(dirty: string): string {
  if (typeof window === "undefined") {
    // Server-side: strip all HTML tags as DOMPurify needs a DOM
    return stripTags(dirty);
  }

  return DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS: [
      "b",
      "i",
      "em",
      "strong",
      "u",
      "s",
      "br",
      "p",
      "span",
      "ul",
      "ol",
      "li",
      "a",
      "img",
      "h1",
      "h2",
      "h3",
      "h4",
      "h5",
      "h6",
      "code",
      "pre",
      "blockquote",
      "div",
    ],
    ALLOWED_ATTR: [
      "href",
      "target",
      "rel",
      "src",
      "alt",
      "width",
      "height",
      "class",
      "id",
    ],
    ALLOW_DATA_ATTR: false,
    ADD_ATTR: ["target"],
    FORBID_TAGS: ["script", "iframe", "object", "embed", "form", "style"],
    FORBID_ATTR: [
      "onerror",
      "onclick",
      "onload",
      "onmouseover",
      "onfocus",
      "onblur",
    ],
  });
}

/**
 * Strip ALL HTML tags from a string.
 * Used as server-side fallback where DOMPurify is unavailable.
 */
export function stripTags(input: string): string {
  return input.replace(/<[^>]*>/g, "");
}

/**
 * Escape HTML entities to prevent injection in non-HTML contexts.
 * Use this for user-generated content rendered as text, not HTML.
 */
export function escapeHTML(input: string): string {
  return input
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#x27;");
}
