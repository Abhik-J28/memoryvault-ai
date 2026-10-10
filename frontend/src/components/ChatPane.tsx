/**
 * MemoryVault AI — Chat Pane Component
 * ======================================
 * Phase 5
 *
 * Left side of the split-pane layout (55%).
 * Renders a scrollable chat thread with bot/user message bubbles,
 * quick-reply chips, a typing indicator, and a text input bar.
 */

'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { Brain, Send, RotateCcw } from 'lucide-react';
import QuickChips from './QuickChips';
import type { ChatResponse, RouteStep, LayoutData, PredictionData } from '@/lib/api';
import { sendChatMessage } from '@/lib/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Message {
  id: string;
  role: 'bot' | 'user';
  text: string;
  quickReplies?: string[];
}

interface ChatPaneProps {
  sessionId: string;
  username?: string | null;
  onRouteData: (route: RouteStep[], layout: LayoutData, prediction: PredictionData, customUserRooms?: string[]) => void;
  onResetSearch?: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ChatPane({ sessionId, username, onRouteData, onResetSearch }: ChatPaneProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [dialogueState, setDialogueState] = useState('GREETING');
  const [context, setContext] = useState<Record<string, unknown>>({});
  const [chipDisabled, setChipDisabled] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const hasInitiated = useRef(false);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: 'smooth',
    });
  }, [messages, isTyping]);

  // Initiate conversation on mount
  useEffect(() => {
    if (hasInitiated.current) return;
    hasInitiated.current = true;
    handleSend('', true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSend = useCallback(
    async (text: string, isInit = false) => {
      if (!isInit && !text.trim()) return;

      // Disable previous quick replies
      setChipDisabled(true);

      // Add user message (skip for initial greeting)
      if (!isInit && text.trim()) {
        const userMsg: Message = {
          id: `user-${Date.now()}`,
          role: 'user',
          text: text.trim(),
        };
        setMessages((prev) => [...prev, userMsg]);
      }

      setInput('');
      setIsTyping(true);

      try {
        const response: ChatResponse = await sendChatMessage(
          sessionId,
          isInit ? '' : text.trim(),
          dialogueState,
          context,
          username,
        );

        setDialogueState(response.state);
        setContext(response.context);

        const botMsg: Message = {
          id: `bot-${Date.now()}`,
          role: 'bot',
          text: response.bot_message,
          quickReplies: response.quick_replies,
        };

        setMessages((prev) => [...prev, botMsg]);
        setChipDisabled(false);

        // If route data is available, send to parent
        if (response.route_data && response.layout && response.prediction) {
          onRouteData(response.route_data, response.layout, response.prediction, response.custom_user_rooms);
        }
      } catch {
        const errorMsg: Message = {
          id: `bot-err-${Date.now()}`,
          role: 'bot',
          text: '⚠️ Something went wrong connecting to the backend. Please make sure the server is running on port 8000.',
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setIsTyping(false);
        inputRef.current?.focus();
      }
    },
    [sessionId, username, dialogueState, context, onRouteData],
  );

  const handleChipSelect = (chip: string) => {
    if (chipDisabled) return;
    handleSend(chip);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend(input);
    }
  };

  // ── Render ─────────────────────────────────────────────────────────

  return (
    <div className="chat-pane">
      {/* Header */}
      <div className="chat-header justify-between">
        <div className="flex items-center gap-2">
          <Brain size={18} color="#0284c7" />
          <span>Conversational Triage</span>
        </div>
        {onResetSearch && (
          <button
            type="button"
            className="search-another-header-btn"
            onClick={onResetSearch}
            title="Start a fresh search for another lost item"
          >
            <RotateCcw size={13} />
            <span>Search Another</span>
          </button>
        )}
      </div>

      {/* Messages scroll area */}
      <div ref={scrollRef} className="chat-messages">
        {messages.map((msg) => (
          <div key={msg.id} className={`chat-bubble-row ${msg.role}`}>
            <div className={`chat-bubble ${msg.role}`}>
              {/* Render markdown-like bold */}
              <p
                dangerouslySetInnerHTML={{
                  __html: msg.text
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\n/g, '<br />'),
                }}
              />
            </div>
            {/* Quick replies below bot bubble */}
            {msg.role === 'bot' && msg.quickReplies && msg.quickReplies.length > 0 && (
              <QuickChips
                chips={msg.quickReplies}
                onSelect={handleChipSelect}
                disabled={chipDisabled && msg.id !== messages[messages.length - 1]?.id}
              />
            )}
          </div>
        ))}

        {/* Typing indicator */}
        {isTyping && (
          <div className="chat-bubble-row bot">
            <div className="chat-bubble bot typing-indicator">
              <span className="dot" />
              <span className="dot" />
              <span className="dot" />
            </div>
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className="chat-input-bar">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message…"
          className="chat-input"
          disabled={isTyping}
        />
        <button
          type="button"
          onClick={() => handleSend(input)}
          disabled={isTyping || !input.trim()}
          className="chat-send-btn"
          aria-label="Send message"
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  );
}
