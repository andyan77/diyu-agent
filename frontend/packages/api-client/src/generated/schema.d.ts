/**
 * Auto-generated OpenAPI types.
 *
 * Task card: FW2-8
 * Generated from: openapi/openapi.yaml
 * Regenerate: pnpm openapi:generate
 *
 * NOTE: This file is a placeholder skeleton. In production,
 * openapi-typescript generates from the actual OpenAPI spec.
 */

export interface paths {
  "/api/v1/conversations/": {
    get: {
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["ConversationList"];
          };
        };
      };
    };
    post: {
      responses: {
        201: {
          content: {
            "application/json": components["schemas"]["ConversationCreated"];
          };
        };
      };
    };
  };
  "/api/v1/conversations/{session_id}/messages": {
    get: {
      parameters: {
        path: { session_id: string };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["MessageList"];
          };
        };
      };
    };
    post: {
      parameters: {
        path: { session_id: string };
      };
      requestBody: {
        content: {
          "application/json": components["schemas"]["SendMessageRequest"];
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["SendMessageResponse"];
          };
        };
      };
    };
  };
  "/api/v1/llm/models": {
    get: {
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["ModelList"];
          };
        };
      };
    };
  };
  "/api/v1/llm/call": {
    post: {
      requestBody: {
        content: {
          "application/json": components["schemas"]["LLMCallRequest"];
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["LLMCallResponse"];
          };
        };
      };
    };
  };
  "/api/v1/upload/request": {
    post: {
      requestBody: {
        content: {
          "application/json": components["schemas"]["UploadRequest"];
        };
      };
      responses: {
        200: {
          content: {
            "application/json": components["schemas"]["UploadSlot"];
          };
        };
      };
    };
  };
}

export interface components {
  schemas: {
    ConversationList: {
      session_id: string;
      created_at: string;
    }[];
    ConversationCreated: {
      session_id: string;
      created_at: string;
    };
    MessageList: {
      role: "user" | "assistant";
      content: string;
      timestamp?: string;
    }[];
    SendMessageRequest: {
      message: string;
      model_id?: string;
    };
    SendMessageResponse: {
      turn_id: string;
      session_id: string;
      assistant_response: string;
      tokens_used: { input: number; output: number };
      model_id: string;
      intent_type: string;
    };
    ModelList: {
      models: {
        id: string;
        name: string;
        provider: string;
      }[];
    };
    LLMCallRequest: {
      prompt: string;
      model_id?: string;
      parameters?: Record<string, unknown>;
    };
    LLMCallResponse: {
      text: string;
      tokens_used: { input: number; output: number };
      model_id: string;
      finish_reason?: string;
    };
    UploadRequest: {
      filename: string;
      content_type: string;
      size_bytes: number;
    };
    UploadSlot: {
      upload_id: string;
      upload_url: string;
      expires_at: string;
    };
  };
}
