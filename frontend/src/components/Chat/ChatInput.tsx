/* ── Chat text input with send button ────────────────── */

import { useState, useRef, useCallback, type FC, type KeyboardEvent } from 'react';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  /** If true, show a "connecting" state */
  isConnecting?: boolean;
}

/**
 * Chat input with auto-growing textarea and send button.
 *
 * - Enter sends the message
 * - Shift+Enter inserts a newline
 * - Auto-grows up to 5 lines
 * - Disabled while connecting or processing
 */
const ChatInput: FC<ChatInputProps> = ({
  onSend,
  disabled = false,
  placeholder = 'Ask about your chart...',
  isConnecting = false,
}) => {
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = useCallback(() => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText('');
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [text, disabled, onSend]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend],
  );

  // Auto-grow textarea
  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setText(e.target.value);
      const el = e.target;
      el.style.height = 'auto';
      el.style.height = `${Math.min(el.scrollHeight, 5 * 24)}px`;
    },
    [],
  );

  return (
    <div className="border-t border-gray-800 p-3 bg-gray-950/80 backdrop-blur-sm">
      {/* Connecting indicator */}
      {isConnecting && (
        <div className="flex items-center gap-1.5 mb-2 text-xs text-gray-500">
          <span className="w-1.5 h-1.5 rounded-full bg-yellow-500 animate-pulse" />
          Connecting to server...
        </div>
      )}

      <div className="flex items-end gap-2">
        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className="input-field resize-none overflow-hidden min-h-[40px] max-h-[120px] py-2.5"
          aria-label="Chat message input"
        />

        {/* Send button */}
        <button
          onClick={handleSend}
          disabled={disabled || !text.trim()}
          className="btn-primary h-10 w-10 p-0 flex-shrink-0 rounded-full"
          aria-label="Send message"
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M22 2L11 13" />
            <path d="M22 2L15 22L11 13L2 9L22 2Z" />
          </svg>
        </button>
      </div>
    </div>
  );
};

export default ChatInput;
