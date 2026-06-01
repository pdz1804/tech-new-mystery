'use client';

import React, { useState, useCallback, memo } from 'react';
import { Bot, Check, Copy, RotateCcw, User } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ChatMessage as ChatMessageType, MessageSegment } from '@/types/chat';
import { ToolIndicator } from './ToolIndicator';
import { MarkdownContent } from '@/components/article/MarkdownContent';

interface ChatMessageProps {
  message: ChatMessageType;
  onRegenerate?: (messageId: string) => void;
  onDelete?: (messageId: string) => void;
  isStreaming?: boolean;
  isMobile?: boolean;
}

/** Render an ordered list of segments (text blocks + tool calls) as they arrived in the stream. */
const SegmentedContent = memo(function SegmentedContent({
  segments,
  isStreaming,
}: {
  segments: MessageSegment[];
  isStreaming: boolean;
}) {
  return (
    <div className="flex flex-col gap-2 w-full">
      {segments.map((seg, i) => {
        if (seg.type === 'tool' && seg.toolCall) {
          return (
            <ToolIndicator key={seg.toolCall.tool_id} {...seg.toolCall} />
          );
        }
        if (seg.type === 'text') {
          const text = seg.content ?? '';
          if (!text) return null;
          return isStreaming ? (
            <p key={i} className="whitespace-pre-wrap text-slate-950 leading-7">
              {text}
            </p>
          ) : (
            <MarkdownContent key={i} content={text} className="chat-markdown" />
          );
        }
        return null;
      })}
    </div>
  );
});

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
  const hasSegments = Boolean(message.segments?.length);
  const hasToolCalls = Boolean(message.tool_calls?.length);

  // Thinking: assistant is streaming but has no content or tools yet
  const isThinking = !isUser && isStreaming && !message.content.trim() && !hasToolCalls && !hasSegments;

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
    onRegenerate?.(message.id);
  }, [message.id, onRegenerate]);

  return (
    <div
      className={cn(
        'group flex w-full gap-3 py-2.5',
        isUser ? 'justify-end' : 'justify-start'
      )}
    >
      {!isUser && (
        <div className="mt-1 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-2xl border border-blue-100 bg-blue-50 text-blue-600 shadow-[0_8px_18px_rgba(37,99,235,0.10)]">
          <Bot className="h-4 w-4" aria-hidden="true" />
        </div>
      )}

      <div
        className={cn(
          'flex min-w-0 flex-col gap-2',
          isUser ? 'max-w-[78%] sm:max-w-[68%]' : 'max-w-[min(100%,860px)] flex-1',
          isUser ? 'items-end' : 'items-start'
        )}
      >
        <div
          className={cn(
            'min-w-0 w-full break-words text-[15px] leading-7 transition-all',
            isUser
              ? 'rounded-[20px] rounded-br-md bg-blue-600 px-4 py-2.5 text-white shadow-[0_10px_24px_rgba(37,99,235,0.24)]'
              : 'rounded-[20px] rounded-tl-md border border-white/60 border-t-white/90 bg-white/66 px-5 py-4 text-slate-950 shadow-[0_16px_36px_rgba(15,23,42,0.08),inset_0_1px_0_rgba(255,255,255,0.88)] backdrop-blur-3xl'
          )}
        >
          {isThinking ? (
            <div className="flex items-center gap-2 text-slate-500">
              <span className="text-sm font-medium">AI is thinking</span>
              <span className="flex items-center gap-1" aria-hidden="true">
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-160ms]" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-80ms]" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" />
              </span>
            </div>
          ) : isUser ? (
            <p className="text-white whitespace-pre-wrap">{message.content}</p>
          ) : hasSegments ? (
            // Streaming or completed message with ordered segments
            <SegmentedContent segments={message.segments!} isStreaming={isAssistantStreaming} />
          ) : (
            // Historical message: text first, then tool calls below (order not known)
            <div className="flex flex-col gap-2">
              {message.content.trim() ? (
                isAssistantStreaming ? (
                  <p className="whitespace-pre-wrap text-slate-950">{message.content}</p>
                ) : (
                  <MarkdownContent content={message.content} className="chat-markdown" />
                )
              ) : null}
              {hasToolCalls && (
                <div className="flex flex-col gap-2 mt-1">
                  {message.tool_calls!.map((tool) => (
                    <ToolIndicator key={tool.tool_id} {...tool} />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {!isThinking && (
          <div className="flex gap-1 rounded-full border border-white/60 bg-white/70 px-1.5 py-1 opacity-0 shadow-sm backdrop-blur-xl transition-opacity duration-200 group-hover:opacity-100 group-focus-within:opacity-100">
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
