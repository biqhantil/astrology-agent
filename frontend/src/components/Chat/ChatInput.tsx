/* ── Chat text input with send button ────────────────── */

import { useState, useRef, useCallback, type FC, type KeyboardEvent } from 'react';
import { useI18n } from '../../i18n/I18nContext';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  isConnecting?: boolean;
}

const ChatInput: FC<ChatInputProps> = ({
  onSend,
  disabled = false,
  placeholder,
  isConnecting = false,
}) => {
  const { t } = useI18n();
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const ph = placeholder ?? t('chat.placeholder');

  const handleSend = useCallback(() => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText('');
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

  const handleChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 5 * 24)}px`;
  }, []);

  return (
    <div className="border-t border-gray-800 p-3 bg-gray-950/80 backdrop-blur-sm">
      {isConnecting && (
        <div className="flex items-center gap-1.5 mb-2 text-xs text-gray-500">
          <span className="w-1.5 h-1.5 rounded-full bg-yellow-500 animate-pulse" />
          {t('chat.connecting')}
        </div>
      )}

      <div className="flex items-end gap-2">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={ph}
          disabled={disabled}
          rows={1}
          className="input-field resize-none overflow-hidden min-h-[40px] max-h-[120px] py-2.5"
          aria-label={ph}
        />

        <button
          onClick={handleSend}
          disabled={disabled || !text.trim()}
          className="btn-primary h-10 w-10 p-0 flex-shrink-0 rounded-full"
          aria-label={t('chat.send')}
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
