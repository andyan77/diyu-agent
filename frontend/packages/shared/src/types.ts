import type { MessageType } from "./constants";

export interface Message {
  id: string;
  conversationId: string;
  type: MessageType;
  content: string;
  createdAt: string;
  metadata?: Record<string, unknown>;
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messageCount: number;
}

export interface UserProfile {
  id: string;
  orgId: string;
  name: string;
  role: string;
  permissions: string[];
}
