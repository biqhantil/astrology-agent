/* ── Chat Panel deep module: list + bubbles + presets + input wiring (R3) ── */

import { useCallback, useEffect, useRef, useState, type FC } from 'react';
import ReactMarkdown from 'react-markdown';
import Avatar from '../Shared/Avatar';
import ChatInput from './ChatInput';
import PresetPromptChips from './PresetPromptChips';
import type { Message } from '../../types/conversation';
import { useI18n } from '../../i18n/I18nContext';

export interface ChatPanelProps {
  messages?: Message[];
  isStreaming?: boolean;
  onSend?: (text: string) => void;
  isConnected?: boolean;
}

// ── Message bubble ──────────────────────────────────────────────

const MessageBubble: FC<{
  message: Message;
  isStreaming?: boolean;
  isLast?: boolean;
}> = ({ message, isStreaming = false, isLast = false }) => {
  const { t } = useI18n();
  const isUser = message.role === 'user';
  const isTool = message.role === 'tool';

  if (isTool) {
    return (
      <div className="flex gap-2 px-4 py-1.5">
        <div className="flex-1 max-w-full">
          <div className="card p-2 bg-surface-light/50 border-gray-700/30">
            <div className="flex items-center gap-1.5 text-xs text-gray-400">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
              </svg>
              <span className="font-medium">{message.tool_name ?? t('common.toolCall')}</span>
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
      <Avatar role={message.role} size={28} />
      <div
        className={`max-w-[85%] rounded-2xl px-3.5 py-2 ${
          isUser
            ? 'bg-accent-dark/30 border border-accent-dark/20 text-gray-100 rounded-tr-md'
            : 'bg-surface-light border border-gray-800 text-gray-200 rounded-tl-md'
        }`}
      >
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

        {isStreaming && isLast && (
          <span className="inline-block w-2 h-4 bg-accent/70 rounded-sm animate-pulse ml-0.5" />
        )}

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

// ── Message list ────────────────────────────────────────────────

const MessageList: FC<{
  messages: Message[];
  isStreaming?: boolean;
  emptyPlaceholder: string;
}> = ({
  messages,
  isStreaming = false,
  emptyPlaceholder,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, messages.length, isStreaming]);

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
    <div className="flex-1 overflow-y-auto py-3 space-y-1 scroll-smooth">
      {messages.map((msg, idx) => (
        <div key={msg.id ?? `msg-${idx}`}>
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

// ── Panel ───────────────────────────────────────────────────────

export const ChatPanel: FC<ChatPanelProps> = ({
  messages: externalMessages,
  isStreaming = false,
  onSend: externalOnSend,
  isConnected = false,
}) => {
  const { t } = useI18n();
  const [internalMessages, setInternalMessages] = useState<Message[]>([]);
  const messages = externalMessages ?? internalMessages;

  const handleSend = useCallback(
    (text: string) => {
      if (externalOnSend) {
        externalOnSend(text);
        return;
      }

      const userMsg: Message = {
        id: Date.now(),
        conversation_id: '',
        role: 'user',
        content: text,
        created_at: new Date().toISOString(),
      };
      const assistantMsg: Message = {
        id: Date.now() + 1,
        conversation_id: '',
        role: 'assistant',
        content: t('chat.standaloneReply', { text }),
        created_at: new Date().toISOString(),
      };
      setInternalMessages((prev) => [...prev, userMsg, assistantMsg]);
    },
    [externalOnSend, t],
  );

  const handlePreset = useCallback(
    (prompt: string) => {
      handleSend(prompt);
    },
    [handleSend],
  );

  const showThinking =
    isStreaming &&
    messages.length > 0 &&
    messages[messages.length - 1].role === 'user';

  return (
    <div className="flex flex-col h-full">
      <PresetPromptChips onSelect={handlePreset} disabled={isStreaming} />

      {showThinking && (
        <div className="flex items-center gap-2 px-4 py-2 animate-fade-in">
          <div className="flex gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-accent/50 animate-bounce" style={{ animationDelay: '0s' }} />
            <span className="w-1.5 h-1.5 rounded-full bg-accent/50 animate-bounce" style={{ animationDelay: '0.15s' }} />
            <span className="w-1.5 h-1.5 rounded-full bg-accent/50 animate-bounce" style={{ animationDelay: '0.3s' }} />
          </div>
          <span className="text-[11px] text-zinc-500 tracking-wide">{t('chat.consulting')}</span>
        </div>
      )}

      <MessageList
        messages={messages}
        isStreaming={isStreaming}
        emptyPlaceholder={t('chat.empty')}
      />

      <ChatInput
        onSend={handleSend}
        disabled={isStreaming}
        isConnecting={!isConnected}
        placeholder={t('chat.placeholder')}
      />
    </div>
  );
};

export default ChatPanel;
