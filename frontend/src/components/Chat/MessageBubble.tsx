/* ── Single chat message bubble ──────────────────────── */

import { type FC } from 'react';
import ReactMarkdown from 'react-markdown';
import Avatar from '../Shared/Avatar';
import type { Message } from '../../types/conversation';

interface MessageBubbleProps {
  message: Message;
  /** If true, show a streaming indicator (pulsing cursor) */
  isStreaming?: boolean;
  /** If true, this is the most recent assistant message */
  isLast?: boolean;
}

/**
 * Renders a single chat message bubble with avatar, markdown content,
 * and streaming indicator for in-progress assistant responses.
 */
const MessageBubble: FC<MessageBubbleProps> = ({
  message,
  isStreaming = false,
  isLast = false,
}) => {
  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';
  const isTool = message.role === 'tool';

  // Tool messages are collapsed by default (shown as cards)
  if (isTool) {
    return (
      <div className="flex gap-2 px-4 py-1.5">
        <div className="flex-1 max-w-full">
          <div className="card p-2 bg-surface-light/50 border-gray-700/30">
            <div className="flex items-center gap-1.5 text-xs text-gray-400">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
              </svg>
              <span className="font-medium">{message.tool_name ?? 'Tool call'}</span>
            </div>
            {message.content && (
              <p className="text-xs text-gray-500 mt-1 truncate">{message.content}</p>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex gap-2 px-4 py-1.5 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <Avatar role={message.role} size={28} />

      {/* Content bubble */}
      <div
        className={`max-w-[85%] rounded-2xl px-3.5 py-2 ${
          isUser
            ? 'bg-accent-dark/30 border border-accent-dark/20 text-gray-100 rounded-tr-md'
            : 'bg-surface-light border border-gray-800 text-gray-200 rounded-tl-md'
        }`}
      >
        {/* Markdown rendered content */}
        <div className="prose prose-invert prose-sm max-w-none">
          <ReactMarkdown
            components={{
              p: ({ children }) => <p className="mb-1 last:mb-0 leading-relaxed">{children}</p>,
              ul: ({ children }) => <ul className="list-disc pl-4 my-1 space-y-0.5">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal pl-4 my-1 space-y-0.5">{children}</ol>,
              li: ({ children }) => <li className="text-gray-200">{children}</li>,
              strong: ({ children }) => <strong className="font-semibold text-gray-100">{children}</strong>,
              em: ({ children }) => <em className="italic text-gray-300">{children}</em>,
              code: ({ children }) => (
                <code className="px-1 py-0.5 rounded bg-gray-800 text-accent-light text-xs">
                  {children}
                </code>
              ),
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>

        {/* Streaming cursor for in-progress assistant messages */}
        {isStreaming && isLast && (
          <span className="inline-block w-2 h-4 bg-accent/70 rounded-sm animate-pulse ml-0.5" />
        )}

        {/* Timestamp for non-streaming messages */}
        {!isStreaming && message.created_at && (
          <div className="flex justify-end mt-1">
            <span className="text-[10px] text-gray-600">
              {new Date(message.created_at).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageBubble;
