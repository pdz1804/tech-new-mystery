'use client';

import React, { memo, useEffect } from 'react';
import { Bot, PanelLeftClose } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useStreamChat } from '@/hooks/useStreamChat';
import type { ChatSession } from '@/types/chat';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';

interface ChatInterfaceProps {
  session: ChatSession;
  onSessionUpdate?: () => void;
  onCloseSidebar?: () => void;
  className?: string;
}

export const ChatInterface = memo(function ChatInterface({
  session,
  onSessionUpdate,
  onCloseSidebar,
  className,
}: ChatInterfaceProps) {
  const {
    messages,
    isLoading,
    isLoadingHistory,
    error,
    sendMessage,
    cancelMessage,
    regenerateMessage,
    deleteMessage,
    clearError,
  } = useStreamChat(session.id);

  useEffect(() => {
    if (!isLoading) {
      onSessionUpdate?.();
    }
  }, [isLoading, onSessionUpdate]);

  const visibleCount = messages.filter((message) => message.role === 'user' || message.role === 'assistant').length;

  return (
    <div className={cn('flex h-full flex-col overflow-hidden bg-transparent', className)}>
      <div className="border-b border-black/5 bg-white/48 px-4 py-3 backdrop-blur-3xl md:px-6">
        <div className="mx-auto flex max-w-4xl items-center justify-between">
          <div className="flex min-w-0 items-center gap-3 flex-1">
            <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-2xl border border-black/5 border-t-white/70 bg-white/70 text-[#007AFF] shadow-[inset_0_1px_0_rgba(255,255,255,0.75),0_10px_24px_rgba(15,23,42,0.08)] backdrop-blur-2xl">
              <Bot className="h-[18px] w-[18px]" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <h1 className="truncate text-[15px] font-semibold text-slate-950">{session.title}</h1>
              <p className="mt-0.5 text-xs text-slate-500">
                {isLoadingHistory ? 'Loading...' : `${visibleCount} messages`}
              </p>
            </div>
          </div>

          {onCloseSidebar && (
            <button
              type="button"
              onClick={onCloseSidebar}
              className="ml-3 hidden rounded-full border border-black/5 bg-white/60 p-2 text-slate-600 shadow-sm backdrop-blur-xl transition-colors hover:bg-white/85 hover:text-slate-950 md:inline-flex"
              title="Hide sidebar"
              aria-label="Hide sidebar"
            >
              <PanelLeftClose className="h-4 w-4" aria-hidden="true" />
            </button>
          )}
        </div>
      </div>

      <div className="min-h-0 flex-1">
        <MessageList
          messages={messages}
          isLoading={isLoading || isLoadingHistory}
          error={error}
          onRegenerate={regenerateMessage}
          onDelete={deleteMessage}
        />
      </div>

      {/* Error message */}
      {error && (
        <div className="border-t border-red-200/50 bg-red-50/80 px-4 py-3 backdrop-blur-sm md:px-8">
          <div className="mx-auto max-w-4xl flex items-center justify-between">
            <p className="text-sm text-red-700">{error}</p>
            <button
              type="button"
              onClick={clearError}
              className="ml-4 text-xs font-medium text-red-600 hover:text-red-700"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      <div className="bg-gradient-to-t from-white/82 via-white/58 to-transparent px-3 pb-4 pt-3 backdrop-blur-2xl sm:px-6">
        <div className="mx-auto max-w-3xl">
          <ChatInput
            onSubmit={sendMessage}
            isLoading={isLoading}
            disabled={isLoadingHistory}
            onCancel={cancelMessage}
            placeholder="Message Tech News Mystery"
          />
        </div>
      </div>
    </div>
  );
});

ChatInterface.displayName = 'ChatInterface';
