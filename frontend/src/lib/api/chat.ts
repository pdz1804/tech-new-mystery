/**
 * Chat API functions for the backend chatbot endpoints.
 */

import { apiClient } from './client';
import { useAuthStore } from '@/lib/stores/authStore';
import type {
  ApiMessage,
  ApiResponse,
  ApiSession,
  ChatMessage,
  ChatMessageRequest,
  ChatSession,
  CreateSessionRequest,
  CreateSessionResponse,
  ListMessagesResponse,
  ListSessionsResponse,
  SSEEvent,
} from '@/types/chat';

function yieldToBrowser(): Promise<void> {
  return new Promise((resolve) => {
    if (typeof window === 'undefined') {
      resolve();
      return;
    }

    window.requestAnimationFrame(() => {
      resolve();
    });
  });
}

function normalizeSession(session: ApiSession): ChatSession {
  return {
    id: session.session_id,
    user_id: session.user_id,
    title: session.title,
    description: session.description ?? null,
    created_at: toMillis(session.created_at),
    updated_at: toMillis(session.updated_at ?? session.created_at),
    last_message_at: toMillis(session.last_message_at ?? session.updated_at ?? session.created_at),
    message_count: session.message_count ?? 0,
    preview: session.description ?? '',
    status: 'active',
  };
}

function normalizeMessage(message: ApiMessage): ChatMessage {
  const role = ['user', 'assistant', 'tool', 'error'].includes(message.role)
    ? (message.role as ChatMessage['role'])
    : 'assistant';

  let tool_calls: import('@/types/chat').ToolCall[] | undefined;
  if (message.tool_calls_json) {
    try {
      tool_calls = JSON.parse(message.tool_calls_json);
    } catch {
      // Malformed JSON from older persisted messages; ignore it.
    }
  }

  let segments: import('@/types/chat').MessageSegment[] | undefined;
  if (message.segments_json) {
    try {
      segments = JSON.parse(message.segments_json);
    } catch {
      // Malformed JSON from older persisted messages; ignore it.
    }
  }

  return {
    id: message.message_id,
    session_id: message.session_id,
    user_id: message.user_id,
    role,
    content: message.content,
    timestamp: toMillis(message.timestamp),
    tokens: message.token_count ?? undefined,
    tool_calls,
    segments,
  };
}

export async function createSession(request: CreateSessionRequest): Promise<CreateSessionResponse> {
  const response = await apiClient.post<ApiResponse<ApiSession>>('/chat/sessions', request);
  return normalizeSession(response.data.data);
}

export async function listSessions(
  page = 1,
  pageSize = 20
): Promise<ListSessionsResponse> {
  const response = await apiClient.get<ApiResponse<ApiSession[]>>('/chat/sessions', {
    params: { page, page_size: pageSize },
  });

  return {
    sessions: response.data.data.map(normalizeSession),
    pagination: {
      total: response.data.meta?.total ?? response.data.data.length,
      page: response.data.meta?.page ?? page,
      page_size: response.data.meta?.limit ?? pageSize,
    },
  };
}

export async function getSession(sessionId: string): Promise<{ session: ChatSession; messages: ChatMessage[] }> {
  const [sessionResponse, messagesResponse] = await Promise.all([
    apiClient.get<ApiResponse<ApiSession>>(`/chat/sessions/${sessionId}`),
    getSessionMessages(sessionId),
  ]);

  return {
    session: normalizeSession(sessionResponse.data.data),
    messages: messagesResponse.messages,
  };
}

export async function getSessionMessages(
  sessionId: string,
  page = 1,
  pageSize = 50
): Promise<ListMessagesResponse> {
  const response = await apiClient.get<ApiResponse<ApiMessage[]>>(
    `/chat/sessions/${sessionId}/messages`,
    { params: { page, page_size: pageSize } }
  );

  return {
    messages: response.data.data.map(normalizeMessage).sort((a, b) => a.timestamp - b.timestamp),
    pagination: {
      total: response.data.meta?.total ?? response.data.data.length,
      page: response.data.meta?.page ?? page,
      page_size: response.data.meta?.limit ?? pageSize,
    },
  };
}

export async function* streamChatMessage(
  request: ChatMessageRequest,
  signal?: AbortSignal
): AsyncGenerator<SSEEvent, void, unknown> {
  const response = await fetch(
    `${getApiBaseUrl()}/chat/sessions/${encodeURIComponent(request.session_id)}/stream`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify({ content: request.user_message }),
      signal,
    }
  );

  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || `HTTP ${response.status}: ${response.statusText}`);
  }

  if (!response.body) {
    throw new Error('No response body');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let readCount = 0;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      readCount += 1;
      const decoded = decoder.decode(value, { stream: true });
      if (process.env.NODE_ENV === 'development') {
        console.debug('[chat-read]', {
          readCount,
          bytes: value.byteLength,
          chars: decoded.length,
          at: Math.round(performance.now()),
          wallTime: new Date().toISOString(),
          preview: decoded.slice(0, 80),
        });
      }

      buffer += decoded;
      const eventTexts = buffer.split('\n\n');
      buffer = eventTexts.pop() ?? '';

      for (const eventText of eventTexts) {
        const event = parseSSEEvent(eventText);
        if (event) {
          if (process.env.NODE_ENV === 'development') {
            console.debug('[chat-event]', {
              type: event.type,
              at: Math.round(performance.now()),
              wallTime: new Date().toISOString(),
              serverSentAt: event._server_sent_at_ms,
              browserLagMs: event._server_sent_at_ms
                ? Date.now() - event._server_sent_at_ms
                : undefined,
            });
          }
          yield event;
        }
      }
    }

    if (buffer.trim()) {
      const event = parseSSEEvent(buffer);
      if (event) yield event;
    }
  } finally {
    reader.releaseLock();
  }
}

export async function readChatMessageStream(
  request: ChatMessageRequest,
  onEvent: (event: SSEEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  if (typeof window !== 'undefined' && typeof XMLHttpRequest !== 'undefined') {
    return readChatMessageStreamWithXHR(request, onEvent, signal);
  }

  return readChatMessageStreamWithFetch(request, onEvent, signal);
}

export async function synthesizeVoiceSpeech(text: string, signal?: AbortSignal): Promise<Blob> {
  const response = await fetch(`${getApiBaseUrl()}/chat/voice/speech`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeader(),
    },
    body: JSON.stringify({ text }),
    signal,
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || `HTTP ${response.status}: ${response.statusText}`);
  }

  return response.blob();
}

export async function createVoiceSttToken(): Promise<{
  token: string;
  model_id: string;
  audio_format: string;
}> {
  const response = await apiClient.post<ApiResponse<{
    token: string;
    model_id: string;
    audio_format: string;
  }>>('/chat/voice/stt-token');

  return response.data.data;
}

export async function createVoiceLiveKitSession(sessionId: string): Promise<{
  transport: 'livekit';
  server_url: string;
  room: string;
  participant_token: string;
  agent_name: string;
  trace_id?: string | null;
  expires_in: number;
}> {
  const response = await apiClient.post<ApiResponse<{
    transport: 'livekit';
    server_url: string;
    room: string;
    participant_token: string;
    agent_name: string;
    trace_id?: string | null;
    expires_in: number;
  }>>('/chat/voice/livekit-session', { session_id: sessionId });

  return response.data.data;
}

export async function sendVoiceAgentMessage(request: {
  session_id: string;
  content: string;
}): Promise<{
  content: string;
  latency_ms: number;
  input_chars: number;
  output_chars: number;
}> {
  const response = await apiClient.post<ApiResponse<{
    content: string;
    latency_ms: number;
    input_chars: number;
    output_chars: number;
  }>>('/chat/voice/message', request);

  return response.data.data;
}

export async function recordVoiceEvent(event: {
  session_id: string;
  phase: string;
  provider?: string;
  transport?: string;
  livekit_room?: string | null;
  transcript_chars?: number;
  output_chars?: number;
  latency_ms?: number;
}): Promise<{ trace_id?: string | null; tracing_enabled: boolean }> {
  const response = await apiClient.post<ApiResponse<{
    trace_id?: string | null;
    tracing_enabled: boolean;
  }>>('/chat/voice/events', event);

  return response.data.data;
}

function makeAbortError(): Error {
  const error = new Error('Aborted');
  error.name = 'AbortError';
  return error;
}

function logStreamRead(readCount: number, decoded: string, bytes?: number) {
  if (process.env.NODE_ENV !== 'development') return;
  console.debug('[chat-read]', {
    readCount,
    bytes,
    chars: decoded.length,
    at: Math.round(performance.now()),
    wallTime: new Date().toISOString(),
    preview: decoded.slice(0, 80),
  });
}

function logStreamEvent(event: SSEEvent) {
  if (process.env.NODE_ENV !== 'development') return;
  console.debug('[chat-event]', {
    type: event.type,
    at: Math.round(performance.now()),
    wallTime: new Date().toISOString(),
    serverSentAt: event._server_sent_at_ms,
    browserLagMs: event._server_sent_at_ms
      ? Date.now() - event._server_sent_at_ms
      : undefined,
  });
}

function readChatMessageStreamWithXHR(
  request: ChatMessageRequest,
  onEvent: (event: SSEEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    let seenChars = 0;
    let buffer = '';
    let readCount = 0;
    let settled = false;

    const settle = (callback: () => void) => {
      if (settled) return;
      settled = true;
      signal?.removeEventListener('abort', abort);
      callback();
    };

    const processChunk = (decoded: string) => {
      if (!decoded) return;

      readCount += 1;
      logStreamRead(readCount, decoded);

      buffer += decoded;
      const eventTexts = buffer.split('\n\n');
      buffer = eventTexts.pop() ?? '';

      for (const eventText of eventTexts) {
        const event = parseSSEEvent(eventText);
        if (!event) continue;
        logStreamEvent(event);
        onEvent(event);
      }
    };

    const abort = () => {
      xhr.abort();
      settle(() => reject(makeAbortError()));
    };

    if (signal?.aborted) {
      reject(makeAbortError());
      return;
    }

    signal?.addEventListener('abort', abort, { once: true });

    xhr.open(
      'POST',
      `${getApiBaseUrl()}/chat/sessions/${encodeURIComponent(request.session_id)}/stream`,
      true
    );
    xhr.setRequestHeader('Content-Type', 'application/json');
    const authHeader = getAuthHeader();
    for (const [key, value] of Object.entries(authHeader)) {
      xhr.setRequestHeader(key, value);
    }

    xhr.onprogress = () => {
      const decoded = xhr.responseText.slice(seenChars);
      seenChars = xhr.responseText.length;
      processChunk(decoded);
    };

    xhr.onerror = () => {
      settle(() => reject(new Error('Chat stream network error')));
    };

    xhr.onload = () => {
      const decoded = xhr.responseText.slice(seenChars);
      seenChars = xhr.responseText.length;
      processChunk(decoded);

      if (buffer.trim()) {
        const event = parseSSEEvent(buffer);
        if (event) {
          logStreamEvent(event);
          onEvent(event);
        }
      }

      if (xhr.status >= 200 && xhr.status < 300) {
        settle(resolve);
        return;
      }

      settle(() => reject(new Error(xhr.responseText || `HTTP ${xhr.status}: ${xhr.statusText}`)));
    };

    xhr.send(JSON.stringify({ content: request.user_message }));
  });
}

async function readChatMessageStreamWithFetch(
  request: ChatMessageRequest,
  onEvent: (event: SSEEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const response = await fetch(
    `${getApiBaseUrl()}/chat/sessions/${encodeURIComponent(request.session_id)}/stream`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeader(),
      },
      body: JSON.stringify({ content: request.user_message }),
      signal,
    }
  );

  if (!response.ok) {
    const error = await response.text();
    throw new Error(error || `HTTP ${response.status}: ${response.statusText}`);
  }

  if (!response.body) {
    throw new Error('No response body');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let readCount = 0;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      readCount += 1;
      const decoded = decoder.decode(value, { stream: true });
      logStreamRead(readCount, decoded, value.byteLength);

      buffer += decoded;
      const eventTexts = buffer.split('\n\n');
      buffer = eventTexts.pop() ?? '';

      for (const eventText of eventTexts) {
        const event = parseSSEEvent(eventText);
        if (!event) continue;

        logStreamEvent(event);

        onEvent(event);
        // Give React one animation frame to commit this event before draining
        // more buffered chunks from fetch. A timer-only yield can keep
        // processing queued chunks without giving the browser a paint.
        await yieldToBrowser();
      }
    }

    if (buffer.trim()) {
      const event = parseSSEEvent(buffer);
      if (event) {
        onEvent(event);
        await yieldToBrowser();
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export async function deleteSession(sessionId: string): Promise<{ success: boolean; message: string }> {
  const response = await apiClient.delete<{ success: boolean; message: string }>(
    `/chat/sessions/${encodeURIComponent(sessionId)}`
  );
  return response.data;
}

export async function archiveSession(sessionId: string): Promise<ChatSession> {
  const response = await apiClient.put<ApiResponse<ApiSession>>(
    `/chat/sessions/${encodeURIComponent(sessionId)}/archive`
  );
  return normalizeSession(response.data.data);
}

export async function renameSession(sessionId: string, title: string): Promise<ChatSession> {
  const response = await apiClient.put<ApiResponse<ApiSession>>(
    `/chat/sessions/${encodeURIComponent(sessionId)}`,
    { title }
  );
  return normalizeSession(response.data.data);
}

export async function restoreSession(sessionId: string): Promise<ChatSession> {
  const response = await apiClient.put<ApiResponse<ApiSession>>(
    `/chat/sessions/${encodeURIComponent(sessionId)}/restore`
  );
  return normalizeSession(response.data.data);
}

function parseSSEEvent(text: string): SSEEvent | null {
  const lines = text.split(/\r?\n/);
  let eventType = '';
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith('event:')) {
      eventType = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trim());
    }
  }

  const data = dataLines.join('\n');

  if (!data) return null;

  try {
    const parsed = JSON.parse(data) as SSEEvent;
    return {
      ...parsed,
      type: parsed.type ?? (eventType as SSEEvent['type']),
    };
  } catch {
    return {
      type: (eventType || 'token') as SSEEvent['type'],
      content: data,
    };
  }
}

function getApiBaseUrl(): string {
  return (process.env.NEXT_PUBLIC_API_URL ?? '/v1').replace(/\/$/, '');
}

function getAuthHeader(): Record<string, string> {
  const token = useAuthStore.getState().accessToken;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function toMillis(timestamp: number): number {
  return timestamp < 10_000_000_000 ? timestamp * 1000 : timestamp;
}
