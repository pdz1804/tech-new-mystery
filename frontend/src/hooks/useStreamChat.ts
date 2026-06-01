'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { getSessionMessages, readChatMessageStream } from '@/lib/api/chat';
import type { ChatMessage, MessageSegment, ToolCall } from '@/types/chat';

function logRenderedStreamEvent(type: string, detail?: unknown) {
  if (process.env.NODE_ENV !== 'development') return;
  console.debug('[chat-render]', type, detail);
}

export interface UseStreamChatReturn {
  messages: ChatMessage[];
  isLoading: boolean;
  isLoadingHistory: boolean;
  error: string | null;
  sendMessage: (userMessageOrSessionId: string, maybeUserMessage?: string) => Promise<void>;
  cancelMessage: () => void;
  clearMessages: () => void;
  deleteMessage: (messageId: string) => void;
  regenerateMessage: (messageId: string) => Promise<void>;
  clearError: () => void;
}

export function useStreamChat(sessionId?: string, onError?: (error: string) => void): UseStreamChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const streamingSessionRef = useRef<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadMessages() {
      if (!sessionId) {
        setMessages([]);
        return;
      }

      setIsLoadingHistory(true);
      setError(null);

      try {
        const response = await getSessionMessages(sessionId);
        if (!cancelled && streamingSessionRef.current !== sessionId) {
          setMessages(response.messages);
        }
      } catch (err) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : 'Failed to load chat history';
          setError(message);
          onError?.(message);
        }
      } finally {
        if (!cancelled) {
          setIsLoadingHistory(false);
        }
      }
    }

    loadMessages();

    return () => {
      cancelled = true;
      abortControllerRef.current?.abort();
    };
  }, [sessionId, onError]);

  const sendMessage = useCallback(
    async (userMessageOrSessionId: string, maybeUserMessage?: string) => {
      const activeSessionId = maybeUserMessage ? userMessageOrSessionId : sessionId;
      const userMessage = maybeUserMessage ?? userMessageOrSessionId;

      if (!activeSessionId || !userMessage.trim()) return;

      setIsLoading(true);
      setError(null);
      streamingSessionRef.current = activeSessionId;

      const now = Date.now();
      const assistantMessageId = `local-assistant-${now}`;

      setMessages((prev) => [
        ...prev,
        {
          id: `local-user-${now}`,
          session_id: activeSessionId,
          user_id: '',
          role: 'user',
          content: userMessage,
          timestamp: now,
        },
        {
          id: assistantMessageId,
          session_id: activeSessionId,
          user_id: '',
          role: 'assistant',
          content: '',
          timestamp: now,
          tool_calls: [],
          segments: [],
        },
      ]);

      abortControllerRef.current?.abort();
      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      let assistantContent = '';
      const toolCalls = new Map<string, ToolCall>();
      const segments: MessageSegment[] = [];
      let currentTextSegIdx = -1;
      let streamError: Error | null = null;

      const flush = (patch: Partial<ChatMessage>) => {
        setMessages((prev) => {
          let found = false;
          const next = prev.map((message) => {
            if (message.id !== assistantMessageId) return message;
            found = true;
            return { ...message, ...patch };
          });

          if (found) return next;

          let lastAssistantIndex = -1;
          for (let index = next.length - 1; index >= 0; index -= 1) {
            const message = next[index];
            if (message.role === 'assistant' && message.session_id === activeSessionId) {
              lastAssistantIndex = index;
              break;
            }
          }
          if (lastAssistantIndex >= 0) {
            const repaired = [...next];
            repaired[lastAssistantIndex] = {
              ...repaired[lastAssistantIndex],
              id: assistantMessageId,
              ...patch,
            };
            return repaired;
          }

          return [
            ...next,
            {
              id: assistantMessageId,
              session_id: activeSessionId,
              user_id: '',
              role: 'assistant',
              content: '',
              timestamp: now,
              tool_calls: [],
              segments: [],
              ...patch,
            },
          ];
        });
      };

      try {
        await readChatMessageStream(
          { session_id: activeSessionId, user_message: userMessage },
          (event) => {
            if (abortController.signal.aborted || streamError) return;

            if (event.type === 'token') {
              const chunk = event.content ?? '';
              assistantContent += chunk;
              if (currentTextSegIdx >= 0) {
                segments[currentTextSegIdx] = {
                  type: 'text',
                  content: (segments[currentTextSegIdx].content ?? '') + chunk,
                };
              } else {
                currentTextSegIdx = segments.length;
                segments.push({ type: 'text', content: chunk });
              }
              flush({ content: assistantContent, segments: [...segments] });
              logRenderedStreamEvent('token', { chunk, totalChars: assistantContent.length });
            } else if (event.type === 'tool_invocation') {
              const toolId = event.tool_id ?? `${event.tool_name ?? 'tool'}-${toolCalls.size}`;
              const toolCall: ToolCall = {
                tool_id: toolId,
                tool_name: event.tool_name ?? 'tool',
                status: 'executing',
                args: event.tool_args,
              };
              toolCalls.set(toolId, toolCall);
              currentTextSegIdx = -1;
              segments.push({ type: 'tool', toolCall });
              flush({ tool_calls: Array.from(toolCalls.values()), segments: [...segments] });
              logRenderedStreamEvent('tool_invocation', { tool: event.tool_name, toolId });
            } else if (event.type === 'tool_result') {
              const toolIds = Array.from(toolCalls.keys());
              const toolId = event.tool_id ?? toolIds[toolIds.length - 1] ?? 'tool';
              const current = toolCalls.get(toolId) ?? {
                tool_id: toolId,
                tool_name: event.tool_name ?? 'tool',
                status: 'executing' as const,
              };
              const updated: ToolCall = {
                ...current,
                status: event.status === 'failed' ? 'failed' : 'completed',
                result: event.result_summary,
                artifacts: event.result_artifacts,
                results_count: event.results_count,
              };
              toolCalls.set(toolId, updated);
              const segIdx = segments.findIndex(
                (s) => s.type === 'tool' && s.toolCall?.tool_id === toolId
              );
              if (segIdx >= 0) segments[segIdx] = { type: 'tool', toolCall: updated };
              flush({ tool_calls: Array.from(toolCalls.values()), segments: [...segments] });
              logRenderedStreamEvent('tool_result', { tool: event.tool_name, toolId, status: event.status });
            } else if (event.type === 'done') {
              flush({
                content: assistantContent,
                tokens: event.tokens,
                tool_calls: Array.from(toolCalls.values()),
                segments: [...segments],
              });
            } else if (event.type === 'error') {
              streamError = new Error(event.error ?? event.message ?? 'Stream error');
            }
          },
          abortController.signal
        );
      } catch (err) {
        if (!(err instanceof Error && err.name === 'AbortError')) {
          streamError = err instanceof Error ? err : new Error('Chat error occurred');
        }
      } finally {
        setIsLoading(false);
        if (streamingSessionRef.current === activeSessionId) {
          streamingSessionRef.current = null;
        }
        abortControllerRef.current = null;
      }

      if (streamError && streamError.name !== 'AbortError') {
        const msg = streamError.message;
        setError(msg);
        onError?.(msg);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMessageId ? { ...m, role: 'error', content: msg } : m
          )
        );
      }
    },
    [sessionId, onError]
  );

  const cancelMessage = useCallback(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setIsLoading(false);
  }, []);

  const deleteMessage = useCallback((messageId: string) => {
    setMessages((prev) => prev.filter((message) => message.id !== messageId));
  }, []);

  const regenerateMessage = useCallback(
    async (messageId: string) => {
      const messageIndex = messages.findIndex((message) => message.id === messageId);
      if (messageIndex <= 0) return;

      const previousUserMessage = messages
        .slice(0, messageIndex)
        .reverse()
        .find((message) => message.role === 'user');

      if (!previousUserMessage) return;

      setMessages((prev) => prev.slice(0, messageIndex));
      await sendMessage(previousUserMessage.content);
    },
    [messages, sendMessage]
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  const clearError = useCallback(() => setError(null), []);

  return {
    messages,
    isLoading,
    isLoadingHistory,
    error,
    sendMessage,
    cancelMessage,
    clearMessages,
    deleteMessage,
    regenerateMessage,
    clearError,
  };
}
