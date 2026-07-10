/* ── Conversation & Message types ────────────────────── */

export type MessageRole = 'system' | 'user' | 'assistant' | 'tool';
export type ConversationStatus = 'active' | 'archived';

export interface Message {
  id: number;
  conversation_id: string;
  role: MessageRole;
  content: string;
  tool_call_id?: string;
  tool_name?: string;
  payload?: Record<string, unknown>;
  created_at: string;
}

export interface Conversation {
  id: string;
  user_id: string;
  chart_context_id?: string;
  synastry_context_id?: string;
  title?: string;
  status: ConversationStatus;
  model_version?: string;
  created_at: string;
  updated_at: string;
}

export interface SendMessageResponse {
  user_message: Message;
  assistant_message: Message;
}
