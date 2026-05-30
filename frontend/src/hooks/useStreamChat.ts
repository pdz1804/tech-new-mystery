'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import { getSessionMessages, readChatMessageStream } from '@/lib/api/chat';
import type { ChatMessage, SSEEvent, ToolCall } from '@/types/chat';

async function yieldToPaint(): Promise<void> {
  if (typeof window === 'undefined') {
    return;
  }

  await new Promise<void>((resolve) => {
    window.requestAnimationFrame(() => resolve());
  });
}

function yieldToBrowser(): Promise<void> {
  if (typeof window === 'undefined') {
    return Promise.resolve();
  }

  return new Promise((resolve) => {
    window.setTimeout(resolve, 0);
  });
}

async function paceStreamEvent(queuedEvents: number): Promise<void> {
  if (queuedEvents > 0) {
    await yieldToBrowser();
    return;
  }

  await yieldToPaint();
}

function logRenderedStreamEvent(type: string, detail?: unknown) {
  if (process.env.NODE_ENV !== 'development') return;
  console.debug('[chat-render]', type, {
    at: Math.round(performance.now()),
    wallTime: new Date().toISOString(),
    detail,
  });
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
        if (!cancelled) {
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

      const now = Date.now();
      const userMsg: ChatMessage = {
        id: `local-user-${Date.now()}`,
        session_id: activeSessionId,
        user_id: '',
        role: 'user',
        content: userMessage,
        timestamp: now,
      };

      const assistantMessageId = `local-assistant-${Date.now()}`;
      const assistantMsg: ChatMessage = {
        id: assistantMessageId,
        session_id: activeSessionId,
        user_id: '',
        role: 'assistant',
        content: '',
        timestamp: now,
        tool_calls: [],
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);

      abortControllerRef.current?.abort();
      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      let assistantContent = '';
      const toolCalls = new Map<string, ToolCall>();

      const updateAssistantMessage = (patch: Partial<ChatMessage>) => {
        setMessages((prev) =>
          prev.map((message) =>
            message.id === assistantMessageId
              ? { ...message, ...patch }
              : message
          )
        );
      };

      const eventQueue: SSEEvent[] = [];
      let producerDone = false;
      let producerError: unknown = null;
      let wakeConsumer: (() => void) | null = null;
      let waitPromise: Promise<void> | null = null;

      const wake = () => {
        wakeConsumer?.();
        wakeConsumer = null;
        waitPromise = null;
      };

      const waitForQueuedEvent = () => {
        // Reuse promise if already created to avoid allocating new ones per cycle
        if (waitPromise) return waitPromise;
        waitPromise = new Promise<void>((resolve) => {
          wakeConsumer = resolve;
        });
        return waitPromise;
      };

      const producer = (async () => {
        try {
          await readChatMessageStream(
            {
              session_id: activeSessionId,
              user_message: userMessage,
            },
            (event) => {
              eventQueue.push(event);
              wake();
            },
            abortController.signal
          );
        } catch (err) {
          producerError = err;
        } finally {
          producerDone = true;
          wake();
        }
      })();

      const processEvent = async (event: SSEEvent) => {
          if (abortController.signal.aborted) return;

          if (event.type === 'token') {
            assistantContent += event.content ?? '';
            updateAssistantMessage({ content: assistantContent });
            logRenderedStreamEvent('token', {
              chunk: event.content,
              totalChars: assistantContent.length,
            });
            await paceStreamEvent(eventQueue.length);
          }

          if (event.type === 'tool_invocation') {
            const toolId = event.tool_id ?? `${event.tool_name ?? 'tool'}-${toolCalls.size}`;
            toolCalls.set(toolId, {
              tool_id: toolId,
              tool_name: event.tool_name ?? 'tool',
              status: 'executing',
              args: event.tool_args,
            });
            updateAssistantMessage({ tool_calls: Array.from(toolCalls.values()) });
            logRenderedStreamEvent('tool_invocation', {
              tool: event.tool_name,
              toolId,
            });
            await paceStreamEvent(eventQueue.length);
          }

          if (event.type === 'tool_result') {
            const toolIds = Array.from(toolCalls.keys());
            const toolId = event.tool_id ?? toolIds[toolIds.length - 1] ?? 'tool';
            const current = toolCalls.get(toolId) ?? {
              tool_id: toolId,
              tool_name: event.tool_name ?? 'tool',
              status: 'executing' as const,
            };

            toolCalls.set(toolId, {
              ...current,
              status: event.status === 'failed' ? 'failed' : 'completed',
              result: event.result_summary,
              results_count: event.results_count,
            });
            updateAssistantMessage({ tool_calls: Array.from(toolCalls.values()) });
            logRenderedStreamEvent('tool_result', {
              tool: event.tool_name,
              toolId,
              status: event.status,
            });
            await paceStreamEvent(eventQueue.length);
          }

          if (event.type === 'stream_diagnostic') {
            console.info('[chat-stream]', event);
          }

          if (event.type === 'error') {
            const message = event.error ?? event.message ?? 'The chat stream failed';
            throw new Error(message);
          }

          if (event.type === 'done') {
            updateAssistantMessage({
              content: assistantContent,
              tokens: event.tokens,
              tool_calls: Array.from(toolCalls.values()),
            });
          }
      };

      try {
        while (!producerDone || eventQueue.length > 0) {
          if (abortController.signal.aborted) break;

          const event = eventQueue.shift();
          if (!event) {
            await waitForQueuedEvent();
            continue;
          }

          await processEvent(event);
        }

        await producer;
        if (producerError) throw producerError;
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') return;

        const message = err instanceof Error ? err.message : 'Chat error occurred';
        setError(message);
        onError?.(message);
        setMessages((prev) =>
          prev.map((chatMessage) =>
            chatMessage.id === assistantMessageId
              ? {
                  ...chatMessage,
                  role: 'error',
                  content: message,
                }
              : chatMessage
          )
        );
      } finally {
        setIsLoading(false);
        abortControllerRef.current = null;
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
