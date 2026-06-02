/**
 * Chat and messaging types used by the frontend chatbot.
 */

export type ChatRole = 'user' | 'assistant' | 'tool' | 'error';

/** One item in the ordered stream: either a text block or a tool invocation. */
export interface MessageSegment {
  type: 'text' | 'tool';
  content?: string;
  toolCall?: ToolCall;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  user_id: string;
  role: ChatRole;
  content: string;
  timestamp: number;
  tool_calls?: ToolCall[];
  /** Ordered segments preserving the interleaved token/tool sequence during streaming. */
  segments?: MessageSegment[];
  tokens?: number;
  metrics?: ChatMessageMetrics;
}

export interface ChatMessageMetrics {
  input_tokens_est?: number;
  output_tokens?: number;
  total_tokens_est?: number;
  estimated_cost_usd?: number;
  latency_ms?: number;
  time_to_first_token_ms?: number;
  tool_calls?: number;
  voice_turn?: boolean;
  livekit_room?: string | null;
}

export interface ToolCall {
  tool_id: string;
  tool_name: string;
  status: 'executing' | 'completed' | 'failed';
  args?: Record<string, unknown>;
  result?: unknown;
  artifacts?: ToolArtifact[];
  results_count?: number;
  execution_time_ms?: number;
}

export interface ToolArtifact {
  name: string;
  path?: string;
  mime_type?: string;
  data_url?: string;
  too_large?: boolean;
}

export type ToolResult = ToolCall;

export interface ChatSession {
  id: string;
  user_id: string;
  title: string;
  description?: string | null;
  created_at: number;
  updated_at: number;
  last_message_at: number;
  message_count: number;
  preview: string;
  status: 'active' | 'archived';
}

export interface ApiSession {
  session_id: string;
  user_id: string;
  title: string;
  description?: string | null;
  message_count?: number;
  created_at: number;
  updated_at?: number;
  last_message_at?: number;
}

export interface ApiMessage {
  message_id: string;
  session_id: string;
  user_id: string;
  role: string;
  content: string;
  timestamp: number;
  token_count?: number | null;
  model_used?: string | null;
  tool_calls_json?: string | null;
  segments_json?: string | null;
}

export interface ApiListMeta {
  page: number;
  limit: number;
  total?: number | null;
  last_key?: string | null;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  meta?: ApiListMeta;
}

export interface SSEEvent {
  type:
    | 'token'
    | 'tool_invocation'
    | 'tool_result'
    | 'done'
    | 'error'
    | 'warning'
    | 'stream_diagnostic';
  content?: string;
  phase?: 'start' | 'complete';
  real_streaming_required?: boolean;
  real_streaming_used?: boolean;
  fallback_blocked?: boolean;
  stream_chunk_events?: number;
  stream_text_events?: number;
  diagnostics?: Record<string, unknown>;
  tool_name?: string;
  tool_id?: string;
  tool_args?: Record<string, unknown>;
  status?: 'completed' | 'failed';
  message_id?: string;
  tokens?: number;
  error?: string;
  message?: string;
  error_code?: string;
  code?: string;
  results_count?: number;
  result_summary?: string;
  result_artifacts?: ToolArtifact[];
  recoverable?: boolean;
  _server_sent_at_ms?: number;
}

export interface CreateSessionRequest {
  title: string;
  description?: string;
}

export type CreateSessionResponse = ChatSession;

export interface ListSessionsResponse {
  sessions: ChatSession[];
  pagination: {
    total: number;
    page: number;
    page_size: number;
  };
}

export interface ListMessagesResponse {
  messages: ChatMessage[];
  pagination: {
    total: number;
    page: number;
    page_size: number;
  };
}

export interface ChatMessageRequest {
  session_id: string;
  user_message: string;
  context?: Record<string, unknown>;
}

export interface MessageListProps {
  messages: ChatMessage[];
  isLoading: boolean;
  error?: string | null;
  onRegenerate?: (messageId: string) => void;
  onDelete?: (messageId: string) => void;
}

export interface ChatInputProps {
  onSubmit: (message: string) => void;
  isLoading: boolean;
  disabled?: boolean;
  placeholder?: string;
  onCancel?: () => void;
  voiceEnabled?: boolean;
  voiceListening?: boolean;
  voiceSupported?: boolean;
  voiceStatus?: string | null;
  voiceTransport?: string | null;
  onToggleVoice?: () => void;
  onEndVoice?: () => void;
}

export interface ToolIndicatorProps {
  tool_name: string;
  tool_id: string;
  status: 'executing' | 'completed' | 'failed';
  args?: Record<string, unknown>;
  result?: unknown;
  artifacts?: ToolArtifact[];
}
