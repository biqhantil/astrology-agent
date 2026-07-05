/* ── Scrollable message list ─────────────────────────── */

import { useEffect, useRef, type FC } from 'react';
import MessageBubble from './MessageBubble';
import type { Message } from '../../types/conversation';

interface MessageListProps {
  messages: Message[];
  /** If true, show a streaming indicator on the last assistant message */
  isStreaming?: boolean;
  /** Placeholder text when there are no messages */
  emptyPlaceholder?: string;
  /** Called when a message is clicked (e.g., for inline chart tool card) */
  onMessageClick?: (message: Message) => void;
}

/**
 * Renders a scrollable list of chat messages, auto-scrolling to the bottom
 * when new messages arrive.
 *
 * Handles:
 * - User/assistant/tool messages
 * - Streaming indicator on latest assistant message
 * - Auto-scroll on new content
 */
const MessageList: FC<MessageListProps> = ({
  messages,
  isStreaming = false,
  emptyPlaceholder = 'Start a conversation by typing a message or choosing a preset.',
  onMessageClick,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change or streaming updates
  useEffect(() => {
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, messages.length, isStreaming]);

  // Empty state
  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="text-center max-w-sm">
          <div className="text-3xl mb-3 opacity-20">♆</div>
          <p className="text-gray-500 text-sm">{emptyPlaceholder}</p>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="flex-1 overflow-y-auto py-3 space-y-1 scroll-smooth"
    >
      {messages.map((msg, idx) => (
        <div
          key={msg.id ?? `msg-${idx}`}
          onClick={() => onMessageClick?.(msg)}
          className={msg.role === 'tool' ? 'cursor-pointer' : ''}
        >
          <MessageBubble
            message={msg}
            isStreaming={
              isStreaming &&
              idx === messages.length - 1 &&
              msg.role === 'assistant'
            }
            isLast={idx === messages.length - 1}
          />
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
};

export default MessageList;
