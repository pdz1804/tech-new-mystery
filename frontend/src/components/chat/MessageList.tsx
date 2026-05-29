'use client';

/**
 * MessageList component with virtualization for performance.
 * Renders only visible messages to improve performance with large message histories.
 */

import React, { useEffect, useRef, useCallback, memo, useMemo } from 'react';
import { AlertCircle, MessageCircle } from 'lucide-react';
import { ChatMessage } from './ChatMessage';
import { MessageListProps } from '@/types/chat';

/**
 * Simple virtualization hook - keeps track of visible range
 */
function useVirtualization(
  itemCount: number,
  itemHeight: number,
  containerHeight: number,
  scrollTop: number
) {
  return useMemo(() => {
    const visibleStart = Math.floor(scrollTop / itemHeight);
    const visibleEnd = Math.ceil((scrollTop + containerHeight) / itemHeight);

    return {
      visibleStart: Math.max(0, visibleStart - 1),
      visibleEnd: Math.min(itemCount, visibleEnd + 1),
      offsetY: visibleStart * itemHeight,
    };
  }, [itemCount, itemHeight, containerHeight, scrollTop]);
}

/**
 * Empty state for no messages
 */
const EmptyState = memo(() => (
  <div className="flex flex-col items-center justify-center h-full gap-4 text-slate-400">
    <div className="w-16 h-16 rounded-full bg-blue-50 flex items-center justify-center">
      <MessageCircle className="h-7 w-7 text-blue-500" aria-hidden="true" />
    </div>
    <div className="text-center">
      <p className="font-semibold text-slate-700 mb-1">No messages yet</p>
      <p className="text-sm text-slate-500">Start a conversation to get insights about articles</p>
    </div>
  </div>
));

EmptyState.displayName = 'EmptyState';

/**
 * Error state
 */
const ErrorState = memo(({ error }: { error: string }) => (
  <div className="flex items-center gap-3 p-4 bg-red-900/20 border border-red-700 rounded-lg">
    <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
    <div>
      <p className="font-semibold text-red-300 text-sm">Error</p>
      <p className="text-red-200 text-xs">{error}</p>
    </div>
  </div>
));

ErrorState.displayName = 'ErrorState';

/**
 * Loading state
 */
const LoadingState = memo(() => (
  <div className="flex items-center gap-3 p-4">
    <div className="w-6 h-6 rounded-full border-2 border-slate-200 border-t-blue-500 animate-spin" />
    <p className="text-slate-500 text-sm">Loading messages...</p>
  </div>
));

LoadingState.displayName = 'LoadingState';

/**
 * Main MessageList component
 */
export const MessageList = memo(function MessageList({
  messages,
  isLoading,
  error,
  onRegenerate,
  onDelete,
}: MessageListProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = React.useState(0);
  const [containerHeight, setContainerHeight] = React.useState(0);
  const [autoScroll, setAutoScroll] = React.useState(true);

  // Estimate item height (messages vary, so this is approximate)
  const avgItemHeight = 100;

  // Calculate visible range
  const { visibleStart, visibleEnd } = useVirtualization(
    messages.length,
    avgItemHeight,
    containerHeight,
    scrollTop
  );

  // Handle scroll
  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const target = e.currentTarget;
    setScrollTop(target.scrollTop);

    // Auto-scroll is disabled if user scrolls up
    const isAtBottom =
      target.scrollHeight - target.scrollTop - target.clientHeight < 50;
    setAutoScroll(isAtBottom);
  }, []);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, autoScroll]);

  // Update container height on mount and resize
  useEffect(() => {
    const updateHeight = () => {
      if (containerRef.current) {
        setContainerHeight(containerRef.current.clientHeight);
      }
    };

    updateHeight();
    window.addEventListener('resize', updateHeight);
    return () => window.removeEventListener('resize', updateHeight);
  }, []);

  // Visible messages
  const visibleMessages = messages.slice(visibleStart, visibleEnd);

  return (
    <div
      ref={containerRef}
      className="h-full flex flex-col rounded-xl overflow-hidden"
    >
      {/* Messages container */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto p-4 space-y-2 scrollbar-thin scrollbar-thumb-slate-200 scrollbar-track-transparent"
      >
        {/* Error state */}
        {error && <ErrorState error={error} />}

        {/* Loading state */}
        {isLoading && messages.length === 0 && <LoadingState />}

        {/* Empty state */}
        {messages.length === 0 && !isLoading && !error && <EmptyState />}

        {/* Messages */}
        {messages.length > 0 && (
          <>
            {/* Spacing before virtualized content */}
            {visibleStart > 0 && (
              <div style={{ height: visibleStart * avgItemHeight }} />
            )}

            {/* Visible messages */}
            {visibleMessages.map((message) => (
              <ChatMessage
                key={message.id}
                message={message}
                onRegenerate={onRegenerate}
                onDelete={onDelete}
                isStreaming={
                  isLoading &&
                  message.id === messages[messages.length - 1].id &&
                  message.role === 'assistant'
                }
                isMobile={false}
              />
            ))}

            {/* Spacing after virtualized content */}
            {visibleEnd < messages.length && (
              <div
                style={{
                  height: (messages.length - visibleEnd) * avgItemHeight,
                }}
              />
            )}
          </>
        )}
      </div>

      {/* Scroll to bottom indicator */}
      {!autoScroll && messages.length > 0 && (
        <div className="px-4 py-2 border-t border-slate-200 bg-white/80">
          <button
            onClick={() => {
              setAutoScroll(true);
              if (scrollRef.current) {
                scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
              }
            }}
            className="text-xs text-blue-600 hover:text-blue-700 font-medium"
          >
            Scroll to latest message
          </button>
        </div>
      )}
    </div>
  );
});

MessageList.displayName = 'MessageList';
