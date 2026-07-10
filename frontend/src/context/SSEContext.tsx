/* ── SSE React Context — thin binding over chat/session transport ── */

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useRef,
  type ReactNode,
} from 'react';
import { connectSSE, type SSECallback } from '../chat/session';
import type { SSEEventPayload } from '../types/events';

interface SSEContextValue {
  isConnected: boolean;
  lastEvent: SSEEventPayload | null;
  connect: (conversationId: string) => void;
  disconnect: () => void;
}

const SSEContext = createContext<SSEContextValue | null>(null);

interface SSEProviderProps {
  children: ReactNode;
  onEvent?: (event: SSEEventPayload) => void;
}

export function SSEProvider({ children, onEvent: globalOnEvent }: SSEProviderProps) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<SSEEventPayload | null>(null);
  const disconnectRef = useRef<(() => void) | null>(null);

  const handleEvent: SSECallback = useCallback(
    (event) => {
      setLastEvent(event);
      globalOnEvent?.(event);
    },
    [globalOnEvent],
  );

  const connect = useCallback(
    (conversationId: string) => {
      disconnectRef.current?.();
      const close = connectSSE(conversationId, handleEvent, setIsConnected);
      disconnectRef.current = close;
    },
    [handleEvent],
  );

  const disconnect = useCallback(() => {
    disconnectRef.current?.();
    disconnectRef.current = null;
    setIsConnected(false);
  }, []);

  return (
    <SSEContext.Provider value={{ isConnected, lastEvent, connect, disconnect }}>
      {children}
    </SSEContext.Provider>
  );
}

export function useSSEContext(): SSEContextValue {
  const ctx = useContext(SSEContext);
  if (!ctx) {
    throw new Error('useSSEContext must be used within an SSEProvider');
  }
  return ctx;
}
