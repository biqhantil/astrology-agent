/* ── Chat Panel: message list + input + presets ──────── */

import { useCallback, useState, type FC } from 'react';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import PresetPromptChips from './PresetPromptChips';
import type { Message } from '../../types/conversation';

interface ChatPanelProps {
  /** External messages array (for SSE-driven state) */
  messages?: Message[];
  /** True while an LLM response is streaming in */
  isStreaming?: boolean;
  /** Custom send handler */
  onSend?: (text: string) => void;
  /** Connection status for the input indicator */
  isConnected?: boolean;
}

/**
 * Main ChatPanel component connecting the message list, input,
 * and preset chips into a unified chat interface.
 *
 * The panel auto-sizes within its flex container (parent must have height).
 */
const ChatPanel: FC<ChatPanelProps> = ({
  messages: externalMessages,
  isStreaming = false,
  onSend: externalOnSend,
  isConnected = false,
}) => {
  // Internal message state when no external messages are provided
  const [internalMessages, setInternalMessages] = useState<Message[]>([]);

  const messages = externalMessages ?? internalMessages;

  const handleSend = useCallback(
    (text: string) => {
      if (externalOnSend) {
        externalOnSend(text);
        return;
      }

      // Internal message management (standalone mode)
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
        content: `You said: "${text}"\n\nI'm your astrology agent, ready to interpret your chart once the backend is connected via SSE.`,
        created_at: new Date().toISOString(),
      };

      setInternalMessages((prev) => [...prev, userMsg, assistantMsg]);
    },
    [externalOnSend],
  );

  const handlePreset = useCallback(
    (prompt: string) => {
      handleSend(prompt);
    },
    [handleSend],
  );

  return (
    <div className="flex flex-col h-full">
      {/* Preset chips (above messages) */}
      <PresetPromptChips onSelect={handlePreset} disabled={isStreaming} />

      {/* Message list (takes remaining space) */}
      <MessageList messages={messages} isStreaming={isStreaming} />

      {/* Chat input */}
      <ChatInput
        onSend={handleSend}
        disabled={isStreaming}
        isConnecting={!isConnected}
      />
    </div>
  );
};

export default ChatPanel;
