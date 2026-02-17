/**
 * Contract tests for OpenAPI generated types (FW2-8).
 *
 * Verifies that the generated schema types match expected API contracts.
 */

import { describe, it, expect } from "vitest";
import type { components, paths } from "./schema";

describe("OpenAPI schema contract", () => {
  it("ConversationCreated has required fields", () => {
    const conv: components["schemas"]["ConversationCreated"] = {
      session_id: "abc-123",
      created_at: "2026-02-17T00:00:00Z",
    };
    expect(conv.session_id).toBeDefined();
    expect(conv.created_at).toBeDefined();
  });

  it("SendMessageRequest has message field", () => {
    const req: components["schemas"]["SendMessageRequest"] = {
      message: "Hello",
    };
    expect(req.message).toBe("Hello");
    expect(req.model_id).toBeUndefined();
  });

  it("SendMessageResponse has all required fields", () => {
    const res: components["schemas"]["SendMessageResponse"] = {
      turn_id: "t-1",
      session_id: "s-1",
      assistant_response: "Hi there",
      tokens_used: { input: 10, output: 5 },
      model_id: "gpt-4o",
      intent_type: "chat",
    };
    expect(res.turn_id).toBeDefined();
    expect(res.tokens_used.input).toBe(10);
  });

  it("LLMCallResponse has text and tokens", () => {
    const res: components["schemas"]["LLMCallResponse"] = {
      text: "Answer",
      tokens_used: { input: 5, output: 3 },
      model_id: "gpt-4o",
    };
    expect(res.text).toBe("Answer");
    expect(res.finish_reason).toBeUndefined();
  });

  it("UploadSlot has upload_id and upload_url", () => {
    const slot: components["schemas"]["UploadSlot"] = {
      upload_id: "u-1",
      upload_url: "https://storage.example.com/upload",
      expires_at: "2026-02-17T01:00:00Z",
    };
    expect(slot.upload_id).toBeDefined();
    expect(slot.upload_url).toContain("https://");
  });

  it("paths type is well-formed", () => {
    // Type-level test: paths interface should exist and be indexable
    type ConvPath = paths["/api/v1/conversations/"];
    type LLMPath = paths["/api/v1/llm/call"];
    type UploadPath = paths["/api/v1/upload/request"];

    // These just verify the types compile
    const _c: ConvPath | null = null;
    const _l: LLMPath | null = null;
    const _u: UploadPath | null = null;
    expect(_c).toBeNull();
    expect(_l).toBeNull();
    expect(_u).toBeNull();
  });

  it("ModelList contains models array", () => {
    const list: components["schemas"]["ModelList"] = {
      models: [
        { id: "gpt-4o", name: "GPT-4o", provider: "openai" },
        { id: "claude-3", name: "Claude 3", provider: "anthropic" },
      ],
    };
    expect(list.models).toHaveLength(2);
    expect(list.models[0].id).toBe("gpt-4o");
  });

  it("MessageList items have role and content", () => {
    const msgs: components["schemas"]["MessageList"] = [
      { role: "user", content: "Hi" },
      { role: "assistant", content: "Hello" },
    ];
    expect(msgs).toHaveLength(2);
    expect(msgs[0].role).toBe("user");
  });
});
