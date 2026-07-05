/* ── SSE client with header support via fetch + eventsource-parser ── */

import { createParser } from 'eventsource-parser';
import { getAuthHeaders } from './client';
import type { SSEEventPayload } from '../types/events';

export type SSECallback = (event: SSEEventPayload) => void;
export type SSEStatusCallback = (connected: boolean) => void;

/**
 * Opens an SSE connection to the backend /v1/stream endpoint.
 *
 * Uses `fetch` with custom headers (JWT) and the `eventsource-parser`
 * library to parse the SSE stream, since the native `EventSource` API
 * does not support custom request headers.
 *
 * @param conversationId - Active conversation UUID
 * @param onEvent - Callback for each parsed SSE event
 * @param onStatus - Optional callback for connection status changes
 * @returns A function to close the connection
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

          const data = rawData;

          try {
            const parsed = JSON.parse(data) as Record<string, unknown>;

            const event = {
              type: eventType as SSEEventPayload['type'],
              data: parsed,
            } as SSEEventPayload;

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

        const chunk = decoder.decode(value, { stream: true });
        parser.feed(chunk);
      }
    } catch (err) {
      if ((err as Error).name === 'AbortError') {
        // Intentional close
        return;
      }
      console.error('SSE connection error:', err);
      onStatus?.(false);
    }
  };

  startConnection();

  // Return close function
  return () => {
    abortController.abort();
    onStatus?.(false);
  };
}

export default connectSSE;
