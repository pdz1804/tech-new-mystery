'use client';

import React, { useState, useCallback, memo } from 'react';
import { Bot, Check, Copy, RotateCcw, User } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ChatMessage as ChatMessageType } from '@/types/chat';
import { ToolIndicator } from './ToolIndicator';
import { MarkdownContent } from '@/components/article/MarkdownContent';

interface ChatMessageProps {
  message: ChatMessageType;
  onRegenerate?: (messageId: string) => void;
  onDelete?: (messageId: string) => void;
  isStreaming?: boolean;
  isMobile?: boolean;
}

/**
 * Main ChatMessage component
 */
export const ChatMessage = memo(function ChatMessage({
  message,
  onRegenerate,
  isStreaming = false,
}: ChatMessageProps) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === 'user';
  const isAssistantStreaming = !isUser && isStreaming;
  const hasToolCalls = Boolean(message.tool_calls?.length);
  const isThinking = !isUser && isStreaming && !message.content.trim() && !hasToolCalls;
  const isUsingTools = !isUser && isStreaming && !message.content.trim() && hasToolCalls;

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }, [message.content]);


  const handleRegenerate = useCallback(() => {
    if (onRegenerate) {
      onRegenerate(message.id);
    }
  }, [message.id, onRegenerate]);

  return (
    <div
      className={cn(
        'group flex w-full gap-3 py-3',
        isUser ? 'justify-end' : 'justify-start'
      )}
    >
      {!isUser && (
        <div className="mt-1 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-2xl border border-black/5 border-t-white/70 bg-white/65 text-slate-700 shadow-[inset_0_1px_0_rgba(255,255,255,0.7),0_8px_18px_rgba(15,23,42,0.06)] backdrop-blur-2xl">
          <Bot className="h-4 w-4" aria-hidden="true" />
        </div>
      )}

      <div
        className={cn(
          'flex min-w-0 max-w-[78%] flex-col gap-2 sm:max-w-[72%]',
          isUser ? 'items-end' : 'items-start'
        )}
      >
        {message.tool_calls && message.tool_calls.length > 0 && (
          <div className={cn('flex flex-col gap-2 w-full', isUser ? 'items-end' : 'items-start')}>
            {message.tool_calls.map((tool) => (
              <ToolIndicator key={tool.tool_id} {...tool} />
            ))}
          </div>
        )}

        <div
          className={cn(
            'min-w-0 break-words text-[15px] leading-7 transition-all',
            isUser
              ? 'rounded-[22px] bg-[#007AFF] px-4 py-2.5 text-white shadow-[0_10px_24px_rgba(0,122,255,0.22)]'
              : 'rounded-[22px] border border-black/5 border-t-white/70 bg-white/64 px-4 py-3 text-slate-950 shadow-[inset_0_1px_0_rgba(255,255,255,0.72),0_12px_28px_rgba(15,23,42,0.07)] backdrop-blur-2xl'
          )}
        >
          {isThinking || isUsingTools ? (
            <div className="flex items-center gap-2 text-slate-500">
              <span className="text-sm font-medium">
                {isUsingTools ? 'Using tools' : 'AI is thinking'}
              </span>
              <span className="flex items-center gap-1" aria-hidden="true">
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-160ms]" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-80ms]" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" />
              </span>
            </div>
          ) : isUser ? (
            <p className="text-white whitespace-pre-wrap">{message.content}</p>
          ) : isAssistantStreaming ? (
            <p className="whitespace-pre-wrap text-slate-950">{message.content}</p>
          ) : (
            <MarkdownContent content={message.content} />
          )}
        </div>

        {!isThinking && (
        <div
          className="flex gap-1 rounded-full border border-black/5 bg-white/70 px-1.5 py-1 opacity-0 shadow-sm backdrop-blur-xl transition-opacity duration-200 group-hover:opacity-100 group-focus-within:opacity-100"
        >
          <button
            type="button"
            onClick={handleCopy}
            className="rounded-full p-1.5 text-slate-500 transition-colors hover:bg-black/5 hover:text-slate-900"
            title="Copy message"
            aria-label="Copy message"
          >
            {copied ? (
              <Check className="h-4 w-4 text-green-600" />
            ) : (
              <Copy className="h-4 w-4 text-slate-500 hover:text-slate-700" />
            )}
          </button>

          {!isUser && onRegenerate && (
            <button
              type="button"
              onClick={handleRegenerate}
              className="rounded-full p-1.5 text-slate-500 transition-colors hover:bg-black/5 hover:text-slate-900"
              title="Regenerate response"
              aria-label="Regenerate response"
            >
              <RotateCcw className="h-4 w-4 text-slate-500 hover:text-slate-700" />
            </button>
          )}
        </div>
        )}
      </div>

      {isUser && (
        <div className="mt-1 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-2xl bg-slate-950 text-white shadow-[0_8px_18px_rgba(15,23,42,0.16)]">
          <User className="h-4 w-4" aria-hidden="true" />
        </div>
      )}
    </div>
  );
});

ChatMessage.displayName = 'ChatMessage';
