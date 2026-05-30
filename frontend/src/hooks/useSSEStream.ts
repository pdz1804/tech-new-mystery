/**
 * useSSEStream hook for consuming Server-Sent Events
 * Handles connection, event parsing, error handling, and retry logic
 */

import { useState, useCallback, useRef } from 'react';
import { SSEEvent } from '@/types/chat';

interface UseSSEStreamOptions {
  url: string;
  method?: 'GET' | 'POST';
  body?: Record<string, unknown>;
  headers?: Record<string, string>;
  onError?: (error: string) => void;
  maxRetries?: number;
  retryDelay?: number;
}

interface UseSSEStreamResult {
  events: SSEEvent[];
  isLoading: boolean;
  error: string | null;
  cancel: () => void;
  connect: () => Promise<void>;
}

/**
 * Parse a single SSE event from text format
 */
function parseSSEEvent(text: string): SSEEvent | null {
  try {
    const lines = text.split('\n');
    let eventType = 'unknown';
    let eventData: Record<string, unknown> = {};

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        eventType = line.slice(7).trim();
      } else if (line.startsWith('data: ')) {
        const dataStr = line.slice(6);
        try {
          eventData = JSON.parse(dataStr) as Record<string, unknown>;
        } catch {
          eventData = { content: dataStr };
        }
      }
    }

    return {
      type: eventType as SSEEvent['type'],
      ...eventData,
    } as SSEEvent;
  } catch {
    return null;
  }
}

/**
 * useSSEStream hook implementation
 * Connects to an SSE endpoint and streams events
 */
export function useSSEStream(options: UseSSEStreamOptions): UseSSEStreamResult {
  const {
    url,
    method = 'POST',
    body,
    headers,
    onError,
    maxRetries = 3,
    retryDelay = 1000,
  } = options;

  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const retryCountRef = useRef(0);
  const cancelledRef = useRef(false);

  /**
   * Establish SSE connection and stream events
   */
  const connect = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setEvents([]);
    cancelledRef.current = false;

    try {
      const fetchOptions: RequestInit = {
        method,
        headers: {
          'Content-Type': 'application/json',
          ...headers,
        },
      };

      if (body && method !== 'GET') {
        fetchOptions.body = JSON.stringify(body);
      }

      const response = await fetch(url, fetchOptions);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      if (!response.body) {
        throw new Error('No response body');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        if (cancelledRef.current) {
          break;
        }

        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const eventTexts = buffer.split('\n\n');

        // Keep last incomplete event in buffer
        buffer = eventTexts.pop() || '';

        for (const eventText of eventTexts) {
          if (!eventText.trim()) continue;

          const event = parseSSEEvent(eventText);
          if (event) {
            setEvents((prev) => [...prev, event]);

            // Handle error events
            if (event.type === 'error') {
              throw new Error(event.error || 'Stream error');
            }

            // Stop on done event
            if (event.type === 'done') {
              if (reader) reader.releaseLock();
              setIsLoading(false);
              retryCountRef.current = 0;
              return;
            }
          }
        }
      }

      // Process final buffer
      if (buffer.trim()) {
        const event = parseSSEEvent(buffer);
        if (event) {
          setEvents((prev) => [...prev, event]);
          if (event.type === 'error') {
            throw new Error(event.error || 'Stream error');
          }
        }
      }

      if (reader) reader.releaseLock();
      setIsLoading(false);
      retryCountRef.current = 0;
    } catch (err) {
      if (cancelledRef.current) {
        setIsLoading(false);
        return;
      }

      const errorMsg =
        err instanceof Error ? err.message : 'Unknown streaming error';

      // Retry on network failures (not on cancelled)
      if (retryCountRef.current < maxRetries) {
        retryCountRef.current += 1;
        const delay = retryDelay * Math.pow(2, retryCountRef.current - 1);

        await new Promise((resolve) => setTimeout(resolve, delay));
        await connect();
      } else {
        setError(errorMsg);
        onError?.(errorMsg);
        console.error('SSE Stream error:', err);
        setIsLoading(false);
      }
    }
  }, [url, method, body, headers, onError, maxRetries, retryDelay]);

  /**
   * Cancel the stream connection
   */
  const cancel = useCallback(() => {
    cancelledRef.current = true;
    setIsLoading(false);
    setEvents([]);
  }, []);

  return {
    events,
    isLoading,
    error,
    cancel,
    connect,
  };
}

export type { UseSSEStreamResult, UseSSEStreamOptions };
