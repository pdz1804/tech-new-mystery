'use client';

/**
 * ChatMessage component with rich formatting, markdown support,
 * and code syntax highlighting.
 */

import React, { useState, useCallback, memo } from 'react';
import { Copy, Check, RotateCcw, Trash2 } from 'lucide-react';
import SyntaxHighlighter from 'react-syntax-highlighter';
import { atomOneDark } from 'react-syntax-highlighter/dist/esm/styles/hljs';
import { cn } from '@/lib/utils';
import { ChatMessage as ChatMessageType } from '@/types/chat';
import { ToolIndicator } from './ToolIndicator';

interface ChatMessageProps {
  message: ChatMessageType;
  onRegenerate?: (messageId: string) => void;
  onDelete?: (messageId: string) => void;
  isStreaming?: boolean;
  isMobile?: boolean;
}

/**
 * Markdown renderer for message content
 */
const MarkdownContent = memo(({ content, isStreaming }: { content: string; isStreaming?: boolean }) => {
  // Split content into paragraphs, code blocks, and lists
  const parts = content.split(/(\n```[\s\S]*?```|\n[*-]\s.*?(?=\n|$)|\n\d+\.\s.*?(?=\n|$))/);

  return (
    <div className="space-y-3 text-sm leading-relaxed">
      {parts.map((part, idx) => {
        // Code block
        if (part.startsWith('```')) {
          const lines = part.split('\n');
          const language = lines[0].slice(3).trim() || 'plaintext';
          const code = lines.slice(1, -1).join('\n');

          return (
            <div key={idx} className="rounded-lg overflow-hidden bg-slate-900 my-2">
              <div className="bg-slate-800 px-3 py-2 text-xs font-mono text-slate-300">
                {language}
              </div>
              <SyntaxHighlighter
                language={language}
                style={atomOneDark}
                showLineNumbers
                wrapLines
                customStyle={{
                  margin: 0,
                  padding: '12px',
                  fontSize: '13px',
                  lineHeight: '1.5',
                }}
              >
                {code}
              </SyntaxHighlighter>
            </div>
          );
        }

        // Unordered list
        if (part.match(/^\n[*-]\s/)) {
          const items = part
            .split('\n')
            .filter((line) => line.match(/^[*-]\s/))
            .map((line) => line.replace(/^[*-]\s/, ''));

          return (
            <ul key={idx} className="list-disc list-inside space-y-1 ml-2">
              {items.map((item, i) => (
                <li key={i} className="text-slate-700">
                  {formatInlineContent(item)}
                </li>
              ))}
            </ul>
          );
        }

        // Ordered list
        if (part.match(/^\n\d+\./)) {
          const items = part
            .split('\n')
            .filter((line) => line.match(/^\d+\./))
            .map((line) => line.replace(/^\d+\.\s/, ''));

          return (
            <ol key={idx} className="list-decimal list-inside space-y-1 ml-2">
              {items.map((item, i) => (
                <li key={i} className="text-slate-700">
                  {formatInlineContent(item)}
                </li>
              ))}
            </ol>
          );
        }

        // Regular text paragraph
        if (part.trim()) {
          return (
            <p key={idx} className="text-slate-700 whitespace-pre-wrap">
              {formatInlineContent(part)}
            </p>
          );
        }

        return null;
      })}

      {isStreaming && (
        <span className="inline-block w-2 h-5 bg-blue-400 rounded animate-pulse ml-1" />
      )}
    </div>
  );
});

MarkdownContent.displayName = 'MarkdownContent';

/**
 * Format inline markdown (bold, italic, links, inline code)
 */
function formatInlineContent(text: string): React.ReactNode {
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;

  // Pattern: **bold**, *italic*, `code`, [link](url)
  const pattern = /\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`|\[(.+?)\]\((.+?)\)/g;
  let match;

  while ((match = pattern.exec(text)) !== null) {
    // Add text before match
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }

    if (match[1]) {
      // Bold
      parts.push(
        <strong key={parts.length} className="font-bold text-slate-900">
          {match[1]}
        </strong>
      );
    } else if (match[2]) {
      // Italic
      parts.push(
        <em key={parts.length} className="italic text-slate-600">
          {match[2]}
        </em>
      );
    } else if (match[3]) {
      // Inline code
      parts.push(
        <code key={parts.length} className="bg-slate-100 border border-slate-200 px-2 py-0.5 rounded text-xs font-mono text-slate-700">
          {match[3]}
        </code>
      );
    } else if (match[4] && match[5]) {
      // Link
      parts.push(
        <a
          key={parts.length}
          href={match[5]}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-400 hover:text-blue-300 underline transition-colors"
        >
          {match[4]}
        </a>
      );
    }

    lastIndex = pattern.lastIndex;
  }

  // Add remaining text
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length > 0 ? parts : text;
}

/**
 * Main ChatMessage component
 */
export const ChatMessage = memo(function ChatMessage({
  message,
  onRegenerate,
  onDelete,
  isStreaming = false,
  isMobile = false,
}: ChatMessageProps) {
  const [copied, setCopied] = useState(false);
  const [showActions, setShowActions] = useState(false);
  const isUser = message.role === 'user';

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }, [message.content]);

  const handleDelete = useCallback(() => {
    if (onDelete && confirm('Delete this message?')) {
      onDelete(message.id);
    }
  }, [message.id, onDelete]);

  const handleRegenerate = useCallback(() => {
    if (onRegenerate) {
      onRegenerate(message.id);
    }
  }, [message.id, onRegenerate]);

  const timeLabel = new Date(message.timestamp).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <div
      className={cn('flex gap-3 mb-4 group', isUser ? 'flex-row-reverse' : 'flex-row')}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => !isMobile && setShowActions(false)}
    >
      {/* Avatar */}
      <div
        className={cn(
          'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-1',
          isUser
            ? 'bg-blue-600 text-white text-xs font-bold'
            : 'bg-slate-100 border border-slate-200 text-slate-500 text-xs'
        )}
      >
        {isUser ? 'U' : 'A'}
      </div>

      {/* Message bubble */}
      <div className={cn('flex flex-col gap-2 flex-1', isUser ? 'items-end' : 'items-start')}>
        {/* Timestamp */}
        <div className="text-xs text-slate-400 px-2 group-hover:text-slate-500 transition-colors">
          <time
            dateTime={new Date(message.timestamp).toISOString()}
            title={new Date(message.timestamp).toLocaleString()}
          >
            {timeLabel}
          </time>
        </div>

        {/* Tool calls display */}
        {message.tool_calls && message.tool_calls.length > 0 && (
          <div className={cn('flex flex-col gap-2 w-full', isUser ? 'items-end' : 'items-start')}>
            {message.tool_calls.map((tool) => (
              <ToolIndicator key={tool.tool_id} {...tool} />
            ))}
          </div>
        )}

        {/* Message bubble content */}
        <div
          className={cn(
            'rounded-2xl px-4 py-3 max-w-xs md:max-w-2xl break-words',
            isUser
              ? 'bg-blue-600 text-white rounded-br-none'
              : 'bg-white border border-slate-200 text-slate-800 rounded-bl-none shadow-sm'
          )}
        >
          <MarkdownContent content={message.content} isStreaming={isStreaming && isUser === false} />
        </div>

        {/* Message actions */}
        {(showActions || isMobile) && (
          <div className="flex gap-2 px-2 py-1 bg-white border border-slate-200 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity shadow-sm">
            <button
              onClick={handleCopy}
              className="p-1.5 hover:bg-slate-100 rounded transition-colors"
              title="Copy message"
              aria-label="Copy message"
            >
              {copied ? (
                <Check className="w-4 h-4 text-green-500" />
              ) : (
                <Copy className="w-4 h-4 text-slate-400 hover:text-slate-600" />
              )}
            </button>

            {!isUser && onRegenerate && (
              <button
                onClick={handleRegenerate}
                className="p-1.5 hover:bg-slate-100 rounded transition-colors"
                title="Regenerate response"
                aria-label="Regenerate response"
              >
                <RotateCcw className="w-4 h-4 text-slate-400 hover:text-slate-600" />
              </button>
            )}

            {onDelete && (
              <button
                onClick={handleDelete}
                className="p-1.5 hover:bg-slate-100 rounded transition-colors"
                title="Delete message"
                aria-label="Delete message"
              >
                <Trash2 className="w-4 h-4 text-slate-400 hover:text-red-500" />
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
});

ChatMessage.displayName = 'ChatMessage';
