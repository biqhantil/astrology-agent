/* ── React hook for SSE streaming connection ─────────── */

import { useRef, useState, useCallback, useEffect } from 'react';
import { connectSSE, type SSECallback } from '../api/sse';
import type { SSEEventPayload } from '../types/events';

export interface UseSSEOptions {
  /** Conversation ID to subscribe to */
  conversationId: string | null;
  /** Called for every incoming SSE event */
  onEvent?: (event: SSEEventPayload) => void;
  /** Enable auto-reconnect on connection loss (default: true) */
  autoReconnect?: boolean;
  /** Reconnect delay in ms (default: 3000) */
  reconnectDelay?: number;
}

export interface UseSSEReturn {
  /** Whether the SSE connection is currently established */
  isConnected: boolean;
  /** The most recent SSE event received */
  lastEvent: SSEEventPayload | null;
  /** Manually reconnect */
  reconnect: () => void;
  /** Disconnect from SSE */
  disconnect: () => void;
}

/**
 * React hook that manages an SSE connection to the backend.
 *
 * Automatically connects when ``conversationId`` is set and disconnects
 * on unmount or when ``conversationId`` changes.
 *
 * Events are dispatched to the ``onEvent`` callback AND accumulated
 * in ``lastEvent`` for reactive UI updates.
 */
export function useSSE(options: UseSSEOptions): UseSSEReturn {
  const {
    conversationId,
    onEvent: externalOnEvent,
    autoReconnect = true,
    reconnectDelay = 3000,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<SSEEventPayload | null>(null);

  const disconnectRef = useRef<(() => void) | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const conversationIdRef = useRef<string | null>(null);

  const handleEvent: SSECallback = useCallback(
    (event) => {
      setLastEvent(event);
      externalOnEvent?.(event);
    },
    [externalOnEvent],
  );

  const handleStatus = useCallback(
    (connected: boolean) => {
      setIsConnected(connected);
      // Auto-reconnect logic
      if (!connected && autoReconnect && conversationIdRef.current) {
        reconnectTimerRef.current = setTimeout(() => {
          if (conversationIdRef.current) {
            doConnect(conversationIdRef.current, handleEvent, handleStatus, disconnectRef);
          }
        }, reconnectDelay);
      }
    },
    [autoReconnect, reconnectDelay, handleEvent],
  );

  const disconnect = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    disconnectRef.current?.();
    disconnectRef.current = null;
    setIsConnected(false);
  }, []);

  const reconnect = useCallback(() => {
    disconnect();
    if (conversationIdRef.current) {
      doConnect(conversationIdRef.current, handleEvent, handleStatus, disconnectRef);
    }
  }, [disconnect, handleEvent, handleStatus]);

  // Connect when conversationId changes
  useEffect(() => {
    conversationIdRef.current = conversationId;

    if (conversationId) {
      doConnect(conversationId, handleEvent, handleStatus, disconnectRef);
    }

    return () => {
      disconnect();
    };
  }, [conversationId, handleEvent, handleStatus, disconnect]);

  return { isConnected, lastEvent, reconnect, disconnect };
}

/**
 * Internal helper to open an SSE connection and store the close function.
 */
function doConnect(
  conversationId: string,
  onEvent: SSECallback,
  onStatus: (connected: boolean) => void,
  disconnectRef: React.MutableRefObject<(() => void) | null>,
): void {
  // Close existing connection first
  disconnectRef.current?.();

  const close = connectSSE(conversationId, onEvent, onStatus);
  disconnectRef.current = close;
}
