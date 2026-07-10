/* ── Conversation lifecycle hook ─────────────────────── */

import { useState, useCallback, useEffect } from 'react';
import { get, post, patch, setToken, getToken } from '../api/client';
import { useAuthContext } from '../context/AuthContext';
import { useSSEContext } from '../context/SSEContext';
import type {
  Conversation,
  Message,
  SendMessageResponse,
} from '../types';

interface UseConversationReturn {
  conversation: Conversation | null;
  messages: Message[];
  sendMessage: (text: string) => Promise<void>;
  updateConversation: (updates: { chart_context_id?: string; title?: string }) => Promise<void>;
  sending: boolean;
  loading: boolean;
  error: string | null;
}

/**
 * Manages conversation lifecycle — auto-creates on mount,
 * loads message history, sends messages via the API.
 */
export function useConversation(): UseConversationReturn {
  const { token } = useAuthContext();
  const { connect, disconnect, isConnected } = useSSEContext();

  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create or find an active conversation on mount
  useEffect(() => {
    if (!token) return;

    const init = async () => {
      setLoading(true);
      setError(null);
      try {
        const list = await get<Conversation[]>('/v1/conversations?status=active');
        let conv = list.length > 0 ? list[0] : null;

        if (!conv) {
          conv = await post<Conversation>('/v1/conversations', {});
        }

        setConversation(conv);

        // Load message history
        const msgs = await get<{ items: Message[] }>(`/v1/conversations/${conv.id}/messages?limit=50`);
        setMessages(msgs.items);

        // Connect SSE
        connect(conv.id);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to initialize conversation');
      } finally {
        setLoading(false);
      }
    };

    init();

    return () => {
      disconnect();
    };
  }, [token]);

  const updateConversation = useCallback(async (updates: { chart_context_id?: string; title?: string }) => {
    if (!conversation) return;
    try {
      const updated = await patch<Conversation>(`/v1/conversations/${conversation.id}`, updates);
      setConversation(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update conversation');
    }
  }, [conversation]);

  const sendMessage = useCallback(async (text: string) => {
    if (!conversation || sending) return;

    setSending(true);
    setError(null);

    // Optimistically add user message
    const optimistic: Message = {
      id: Date.now(),
      conversation_id: conversation.id,
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimistic]);

    try {
      const res = await post<SendMessageResponse>(
        `/v1/conversations/${conversation.id}/messages`,
        { content: text },
      );

      // Replace optimistic with real messages
      setMessages((prev) => {
        const withoutOptimistic = prev.filter((m) => m.id !== optimistic.id);
        return [...withoutOptimistic, res.user_message, res.assistant_message];
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message');
      // Remove optimistic message on failure
      setMessages((prev) => prev.filter((m) => m.id !== optimistic.id));
    } finally {
      setSending(false);
    }
  }, [conversation, sending]);

  return {
    conversation,
    messages,
    sendMessage,
    updateConversation,
    sending,
    loading,
    error,
  };
}
