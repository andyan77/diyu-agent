export const DEPLOY_MODES = ["saas", "private"] as const;
export type DeployMode = (typeof DEPLOY_MODES)[number];

export const API_VERSION = "v1" as const;

export const WS_RECONNECT_INTERVAL_MS = 3000;
export const WS_MAX_RECONNECT_ATTEMPTS = 10;

export const MESSAGE_TYPES = [
  "user",
  "assistant",
  "system",
  "tool_call",
  "tool_result",
] as const;

export type MessageType = (typeof MESSAGE_TYPES)[number];
