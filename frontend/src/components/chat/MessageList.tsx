'use client';

import React, { memo, useEffect, useRef } from 'react';
import { AlertCircle, MessageCircle } from 'lucide-react';
import { ChatMessage } from './ChatMessage';
import { MessageListProps } from '@/types/chat';

const EmptyState = memo(() => (
  <div className="flex h-full min-h-[360px] flex-col items-center justify-center gap-4 text-center">
    <div className="flex h-14 w-14 items-center justify-center rounded-[22px] border border-black/5 border-t-white/70 bg-white/70 text-[#007AFF] shadow-[inset_0_1px_0_rgba(255,255,255,0.75),0_18px_40px_rgba(15,23,42,0.08)] backdrop-blur-2xl">
      <MessageCircle className="h-7 w-7" aria-hidden="true" />
    </div>
    <div>
      <p className="text-lg font-semibold text-slate-950">Ask anything about tech news</p>
      <p className="mt-1 text-sm text-slate-500">Search, compare, or reason over the article corpus.</p>
    </div>
  </div>
));

EmptyState.displayName = 'EmptyState';

const ErrorState = memo(({ error }: { error: string }) => (
  <div className="mx-auto my-3 flex max-w-3xl items-start gap-3 rounded-2xl border border-red-500/15 bg-red-50/80 p-4 text-sm text-red-700 backdrop-blur-xl">
    <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0" aria-hidden="true" />
    <p className="leading-6 text-red-700">{error}</p>
  </div>
));

ErrorState.displayName = 'ErrorState';

export const MessageList = memo(function MessageList({
  messages,
  isLoading,
  error,
  onRegenerate,
  onDelete,
}: MessageListProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'auto',
      });
    }
  }, [messages, isLoading]);

  return (
    <div ref={scrollRef} className="h-full overflow-y-auto px-3 py-5 sm:px-6">
      {error && <ErrorState error={error} />}

      {messages.length === 0 && !error ? (
        <EmptyState />
      ) : (
        <div className="mx-auto flex w-full max-w-3xl flex-col pb-6">
          {messages.map((message) => (
            <ChatMessage
              key={message.id}
              message={message}
              onRegenerate={onRegenerate}
              onDelete={onDelete}
              isStreaming={
                isLoading &&
                message.id === messages[messages.length - 1]?.id &&
                message.role === 'assistant'
              }
              isMobile={false}
            />
          ))}
        </div>
      )}
    </div>
  );
});

MessageList.displayName = 'MessageList';
