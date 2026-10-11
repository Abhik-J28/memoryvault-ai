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
  onRouteData: (
    route: RouteStep[],
    layout: LayoutData,
    prediction: PredictionData,
    customUserRooms?: string[],
    repeatedFindingRooms?: string[],
    findingCounts?: Record<string, number>,
    context?: Record<string, unknown>,
  ) => void;
  onEarlyFindings?: (
    layout: LayoutData | null,
    repeatedFindingRooms: string[],
    findingCounts: Record<string, number>,
    customUserRooms?: string[],
    itemType?: string,
  ) => void;
  onResetSearch?: () => void;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ChatPane({ sessionId, username, onRouteData, onEarlyFindings, onResetSearch }: ChatPaneProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [chipDisabled, setChipDisabled] = useState(false);

  // Use refs for dialogue state & context to break the re-render dependency cycle
  // that was causing "Maximum update depth exceeded" errors
  const dialogueStateRef = useRef('GREETING');
  const contextRef = useRef<Record<string, unknown>>({});

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
          dialogueStateRef.current,
          contextRef.current,
          username,
        );

        // Update refs (no re-render, no dependency loop)
        dialogueStateRef.current = response.state;
        contextRef.current = response.context;

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
          onRouteData(
            response.route_data,
            response.layout,
            response.prediction,
            response.custom_user_rooms,
            response.repeated_finding_rooms,
            response.finding_counts,
            response.context,
          );
        } else if (
          onEarlyFindings &&
          (response.repeated_finding_rooms || response.custom_user_rooms || response.layout)
        ) {
          // Proactive habit reminder: bubble up layout, previous findings & habit pins as soon as item is identified
          onEarlyFindings(
            response.layout || null,
            response.repeated_finding_rooms || [],
            response.finding_counts || {},
            response.custom_user_rooms || [],
            (response.context?.item_type as string) || undefined,
          );
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
    [sessionId, username, onRouteData, onEarlyFindings],
  );

  // Initiate conversation on mount
  useEffect(() => {
    if (hasInitiated.current) return;
    hasInitiated.current = true;
    handleSend('', true);
  }, [handleSend]);

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
      <div className="chat-header justify-between bg-slate-900 border-b border-slate-800 px-4 py-2.5 text-slate-100 font-bold text-xs tracking-wider uppercase flex items-center">
        <div className="flex items-center gap-2">
          <Brain size={16} className="text-sky-400" />
          <span>Conversational Triage</span>
        </div>
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
