/* ── Chat session transport (SSE) — deep module for stream protocol (R3) ── */

import { createParser } from 'eventsource-parser';
import { getAuthHeaders } from '../api/client';
import type { SSEEventPayload } from '../types/events';

export type SSECallback = (event: SSEEventPayload) => void;
export type SSEStatusCallback = (connected: boolean) => void;

/**
 * Opens an SSE connection to `/v1/stream` with JWT headers.
 * Uses fetch + eventsource-parser (native EventSource cannot set Authorization).
 *
 * @returns close function
 */
export function connectSSE(
  conversationId: string,
  onEvent: SSECallback,
  onStatus?: SSEStatusCallback,
): () => void {
  const abortController = new AbortController();

  const startConnection = async () => {
    const baseUrl = import.meta.env.VITE_API_BASE_URL ?? '';
    const url = `${baseUrl}/v1/stream?conversation_id=${encodeURIComponent(conversationId)}`;
    const headers: Record<string, string> = {
      ...getAuthHeaders(),
      Accept: 'text/event-stream',
      'Cache-Control': 'no-cache',
    };

    try {
      const response = await fetch(url, {
        headers,
        signal: abortController.signal,
      });

      if (!response.ok) {
        onStatus?.(false);
        console.error(`SSE connection failed: ${response.status} ${response.statusText}`);
        return;
      }

      onStatus?.(true);

      const parser = createParser({
        onEvent: (parsedEvent) => {
          const { event: eventType, data: rawData } = parsedEvent;
          if (!eventType || rawData == null) return;

          try {
            const parsed = JSON.parse(rawData) as Record<string, unknown>;
            const event = {
              type: eventType as SSEEventPayload['type'],
              data: parsed,
            } as unknown as SSEEventPayload;
            onEvent(event);
          } catch (err) {
            console.warn(`SSE: Failed to parse event data for "${eventType}":`, err);
          }
        },
        onError: (err) => {
          console.warn('SSE parse error:', err);
        },
      });

      const reader = response.body?.getReader();
      if (!reader) {
        console.error('SSE: No response body reader available');
        return;
      }

      const decoder = new TextDecoder();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        parser.feed(decoder.decode(value, { stream: true }));
      }
    } catch (err) {
      if ((err as Error).name === 'AbortError') return;
      console.error('SSE connection error:', err);
      onStatus?.(false);
    }
  };

  startConnection();

  return () => {
    abortController.abort();
    onStatus?.(false);
  };
}
