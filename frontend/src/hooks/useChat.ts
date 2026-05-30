'use client';

import { useStreamChat } from './useStreamChat';

interface UseChatOptions {
  sessionId: string;
  onError?: (error: string) => void;
}

export function useChat({ sessionId, onError }: UseChatOptions) {
  return useStreamChat(sessionId, onError);
}
