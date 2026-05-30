# Chatbot Feature Guide

## Overview

The chatbot feature provides real-time AI conversations powered by Amazon Bedrock AgentCore with LangGraph orchestration. Users interact with an intelligent agent that can search the article corpus and provide contextual answers using streaming Server-Sent Events (SSE).

## Architecture

### Components

| Component | Purpose |
| --- | --- |
| **AgentCore Runtime** | Bedrock AgentCore app with LangGraph agent orchestration |
| **LangGraph Agent** | Graph-based workflow with route → search → generate nodes |
| **Semantic Search Tool** | Queries Qdrant for relevant articles |
| **Chat Service** | Manages sessions and messages in DynamoDB |
| **AgentCore Client** | HTTP client for invoking the agent with streaming |
| **SSE Stream Handler** | Parses and forwards agent events to frontend |
| **Per-Request Memory** | Isolated context per user request |

### Data Flow

```
User Message
    ↓
Frontend sends via SSE POST /chat/sessions/{id}/stream
    ↓
Backend validates auth & session ownership
    ↓
Per-request memory loads recent messages
    ↓
User message saved immediately to DynamoDB
    ↓
Backend invokes AgentCore runtime
    ↓
AgentCore LangGraph agent routes message
    ↓
If search-needed → semantic search tool queries Qdrant
    ↓
Tool results passed to LLM
    ↓
LLM generates response (streamed as tokens)
    ↓
Tokens streamed back as SSE events
    ↓
Assistant response saved to DynamoDB
    ↓
Final "done" event sent to frontend
```

## DynamoDB Tables

### `tech-news-conversation_sessions`
Stores user chat sessions.

| Key | Type | Purpose |
| --- | --- | --- |
| `user_id` (PK) | String | User who owns session |
| `session_id` (SK) | String | Session identifier |
| `title` | String | Session title (e.g., "Discussion about LLMs") |
| `description` | String | Optional session description |
| `created_at` | Number | Session creation timestamp |
| `updated_at` | Number | Last update timestamp |
| `last_message_at` | Number | Timestamp of last message |
| `message_count` | Number | Total messages in session |
| `is_active` | Boolean | True if active, false if archived |
| `expires_at` (TTL) | Number | Auto-delete after 90 days |

**GSI:** `user-last-message-index` → sort sessions by recency

### `tech-news-conversation_messages`
Stores individual chat messages.

| Key | Type | Purpose |
| --- | --- | --- |
| `session_id` (PK) | String | Session containing message |
| `message_id` (SK) | String | Unique message identifier |
| `user_id` | String | User who sent/received message |
| `role` | String | "user" or "assistant" |
| `content` | String | Message text (up to 64KB) |
| `timestamp` | Number | When message was created |
| `token_count` | Number | Approximate LLM tokens |
| `tool_invocations` | Map | Tool calls made during response |
| `error_code` | String | Error code if message failed |
| `expires_at` (TTL) | Number | Auto-delete after 90 days |

**GSI:** `session-timestamp-index` → get messages in order

### `tech-news-chat_user_preferences`
Stores per-user chat preferences.

| Key | Type | Purpose |
| --- | --- | --- |
| `user_id` (PK) | String | User identifier |
| `search_enabled` | Boolean | Enable/disable semantic search tool |
| `response_length` | String | "concise", "detailed", "comprehensive" |
| `language` | String | "en", "es", "fr", etc. |
| `model_temperature` | Number | 0.0-1.0 (creativity level) |
| `updated_at` | Number | Last preference update |

## API Endpoints

### Create Session
**POST** `/v1/chat/sessions`

Authentication: Bearer JWT token (required)

Request:
```json
{
  "title": "Discussing AI",
  "description": "Chat about recent AI developments"
}
```

Response:
```json
{
  "success": true,
  "data": {
    "session_id": "sess-uuid",
    "user_id": "user-uuid",
    "title": "Discussing AI",
    "description": "Chat about recent AI developments",
    "created_at": 1717000000,
    "updated_at": 1717000000,
    "last_message_at": 1717000000,
    "message_count": 0,
    "is_active": true
  }
}
```

### List Sessions
**GET** `/v1/chat/sessions`

Query parameters:
- `page` (int, default 1): Page number
- `page_size` (int, default 20): Items per page

Response:
```json
{
  "success": true,
  "data": [
    {
      "session_id": "sess-uuid",
      "title": "Discussing AI",
      "message_count": 15,
      "last_message_at": 1717000000,
      "preview": "Chat about recent AI developments"
    }
  ],
  "meta": {"total": 5, "page": 1, "limit": 20}
}
```

### Get Session
**GET** `/v1/chat/sessions/{session_id}`

Response:
```json
{
  "success": true,
  "data": {
    "session_id": "sess-uuid",
    "user_id": "user-uuid",
    "title": "Discussing AI",
    "message_count": 15,
    "created_at": 1717000000,
    "last_message_at": 1717000000,
    "is_active": true
  }
}
```

### Get Messages
**GET** `/v1/chat/sessions/{session_id}/messages`

Query parameters:
- `page` (int, default 1): Page number
- `page_size` (int, default 20): Items per page

Response:
```json
{
  "success": true,
  "data": [
    {
      "message_id": "msg-uuid",
      "session_id": "sess-uuid",
      "role": "user",
      "content": "What are the latest developments in AI?",
      "timestamp": 1717000000,
      "token_count": 12
    },
    {
      "message_id": "msg-uuid-2",
      "session_id": "sess-uuid",
      "role": "assistant",
      "content": "According to recent articles...",
      "timestamp": 1717000001,
      "token_count": 156,
      "tool_invocations": {
        "semantic_search": {
          "status": "completed",
          "results_count": 5
        }
      }
    }
  ],
  "meta": {"total": 30, "page": 1, "limit": 20}
}
```

### Stream Chat Message (SSE)
**POST** `/v1/chat/sessions/{session_id}/stream`

Authentication: Bearer JWT token (required)

Request:
```json
{
  "content": "What's new in LLMs?"
}
```

Response: Server-Sent Events stream

```
event: token
data: {"type": "token", "content": "According"}

event: token
data: {"type": "token", "content": " to"}

event: tool_invocation
data: {"type": "tool_invocation", "tool_name": "semantic_search", "tool_id": "search-1"}

event: tool_result
data: {"type": "tool_result", "status": "completed", "results_count": 5}

event: token
data: {"type": "token", "content": " recent"}

...

event: done
data: {"type": "done", "message_id": "msg-uuid", "tokens": 156}
```

## Backend Implementation

### Chat Service
```python
# backend/app/services/chat_service.py
from app.services.chat_service import ChatService

service = ChatService()

# Create session
session = await service.create_session(
    user_id="user-1",
    title="My Chat",
    description="Optional"
)

# Get session
session = await service.get_session(session_id, user_id)

# List sessions (sorted by recency)
result = await service.list_sessions(user_id, page=1, page_size=20)

# Add message
message = await service.add_message(
    session_id=session_id,
    user_id=user_id,
    role="user",
    content="What's new?"
)

# Get messages
result = await service.get_messages(session_id, user_id, page=1, page_size=50)
```

### AgentCore Client
```python
# backend/app/integrations/agent_core_client.py
from app.integrations.agent_core_client import AgentCoreClient

client = AgentCoreClient(
    base_url="http://localhost:8000",
    api_key="optional-key"
)

# Stream agent response
async for event in client.invoke_agent(
    session_id="sess-1",
    user_message="Tell me about AI",
    context={"recent_events": []},
    user_id="user-1"
):
    print(event)  # {type, content, ...}

await client.close()
```

Features:
- Async streaming with NDJSON and SSE parsing
- Automatic retry on connection failures
- Connection pooling
- Timeout handling (default 60s)

### Per-Request Memory
```python
# backend/app/integrations/agent_core_memory.py
from app.integrations.agent_core_memory import RequestAgentMemory

memory = RequestAgentMemory()
await memory.initialize(
    session_id="sess-1",
    user_id="user-1",
    recent_events=[...]
)

await memory.log_message(
    session_id="sess-1",
    role="user",
    content="Hello"
)

await memory.cleanup()
```

Features:
- Loads recent messages for context
- Isolated per-request (no cross-contamination)
- Automatic cleanup after request completes

### Agent Core Runtime
```python
# agent_core/server.py
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from agent_core.graph import AgentRuntime

app = BedrockAgentCoreApp()
runtime = AgentRuntime(settings)

@app.entrypoint
async def agent_invocation(payload, context):
    # payload: {prompt, session_id, context, user_id}
    # Returns: {result: agent_response}
    ...

app.run()
```

### LangGraph Agent
```python
# agent_core/graph.py
from langchain_aws import ChatBedrockConverse
from langgraph.graph import StateGraph

class AgentRuntime:
    def _build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("route", self._route)
        workflow.add_node("search", self._search)
        workflow.add_node("generate", self._generate)
        
        # route → search (if needed) or generate → done
        workflow.set_entry_point("route")
        workflow.add_conditional_edges("route", ...)
        workflow.add_edge("search", "generate")
        workflow.add_edge("generate", END)
        
        return workflow.compile()
    
    async def _route(self, state):
        # Decide if search is needed
        
    async def _search(self, state):
        # Execute semantic search tool
        
    async def _generate(self, state):
        # Generate response via Claude
```

### Semantic Search Tool
```python
# agent_core/search.py
from agent_core.search import SemanticSearchTool

tool = SemanticSearchTool(settings)

results = await tool.execute(
    query="Latest AI developments",
    top_k=5,
    min_score=0.0
)
# Returns: [{"title": "...", "content": "...", "score": 0.95}]
```

## Frontend Implementation

### Chatbot Page
**Route:** `/chatbot`

Features:
- Session sidebar with search
- Chat interface with message list
- Real-time streaming messages
- Session management (create, select)
- Error handling with retry

### Chat Interface Component
```tsx
// frontend/src/components/chat/ChatInterface.tsx
<ChatInterface session={session} onSessionUpdate={refetch} />
```

Props:
- `session`: ChatSession object
- `onSessionUpdate`: Callback when messages added

### Chat Input Component
```tsx
// frontend/src/components/chat/ChatInput.tsx
<ChatInput
  disabled={isStreaming}
  onSubmit={(message) => handleStreamMessage(message)}
  placeholder="Ask about tech news..."
/>
```

### useStreamChat Hook
```tsx
// frontend/src/hooks/useStreamChat.ts
const {
  messages,
  isStreaming,
  error,
  sendMessage,
  retry
} = useStreamChat(sessionId);

await sendMessage("What's new in AI?");
// Streams events, updates UI in real-time
```

## Error Handling

### Backend Error Codes

| Code | HTTP | Meaning | Recovery |
| --- | --- | --- | --- |
| `INVALID_INPUT` | 400 | Message/session ID invalid | Validate input, retry |
| `SESSION_NOT_FOUND` | 404 | Session doesn't exist | Create new session |
| `UNAUTHORIZED` | 401 | Missing/invalid JWT | Re-authenticate |
| `FORBIDDEN` | 403 | User doesn't own session | Select different session |
| `AGENT_TIMEOUT` | 504 | Agent Core took > 60s | Retry or simplify prompt |
| `AGENT_UNAVAILABLE` | 503 | Agent Core unreachable | Retry with backoff |
| `MESSAGE_SAVE_DEFERRED` | 200 (warning) | Message saved locally, DB delayed | Will retry automatically |
| `INTERNAL_ERROR` | 500 | Unexpected error | Retry, contact support |

### Error Recovery Strategies

**Agent Core Timeout (60s):**
- User message saved ✓
- Friendly error sent to frontend
- Frontend shows "Try again" button
- Retry works as new request with full context

**DynamoDB Save Failure:**
- Message queued in-memory
- Streamed to user anyway (content preserved)
- Automatic exponential backoff retry
- Alert logged to CloudWatch

**Agent Core Unavailable:**
- Graceful fallback message sent
- User advised to try again
- Retry with exponential backoff

## Monitoring

### CloudWatch Metrics

```
chat/stream_duration_seconds (histogram)
chat/agent_timeout_count (counter)
chat/save_error_count (counter)
chat/message_tokens (histogram)
chat/sessions_active (gauge)
chat/streaming_errors (counter)
chat/tool_invocations (counter)
```

### CloudWatch Logs

All chat operations logged:
```
[STREAM] Stream started: session=sess-1, user=user-1
[STREAM] Memory initialized: session=sess-1
[STREAM] Agent response: tokens=150, duration=2.5s
[STREAM] Memory cleanup: session=sess-1
```

## Configuration

### Environment Variables

```bash
# Agent Core
AGENT_CORE_BASE_URL=http://agent-core:8000
AGENT_CORE_API_KEY=optional-api-key
AGENT_CORE_TIMEOUT=60

# Chat
CHAT_SESSION_TTL_DAYS=90
CHAT_MESSAGE_TTL_DAYS=90
CHAT_MAX_RETRIES=3
CHAT_RETRY_BACKOFF_BASE=100  # milliseconds

# Memory
PER_REQUEST_MEMORY_SIZE_MB=100
PER_REQUEST_MEMORY_LOAD_TIMEOUT=5000  # milliseconds

# Agent
AGENT_MODEL=us.anthropic.claude-3-5-haiku-20241022-v1:0
BEDROCK_REGION=us-west-2
```

## Testing

### Unit Tests
```bash
cd backend
pytest tests/test_chat_service.py
pytest tests/test_agent_core_client.py
pytest tests/test_chat_router.py
```

### Integration Tests
```bash
pytest tests/test_chat_integration.py
pytest tests/test_chat_streaming.py
pytest tests/test_chat_auth.py
```

### E2E Tests
```bash
pytest tests/test_chat_e2e.py
# Or manually:
# 1. Create session
# 2. Send message
# 3. Verify message saved
# 4. Check streaming works
# 5. Verify tool invocations
```

### Load Testing
```bash
cd backend
# Run 50 concurrent chat requests
locust -f tests/load_test_chat.py --host=http://localhost:8000
```

## Performance

| Operation | Time | Notes |
| --- | --- | --- |
| Create session | 50ms | DynamoDB write |
| List sessions (20) | 100ms | Query + sort |
| Save user message | 30ms | Immediate write |
| Stream to Agent Core | 100ms | HTTP POST |
| Agent response generation | 2-3s | Bedrock LLM |
| Semantic search | 500ms | Qdrant query |
| Save assistant message | 30ms | DynamoDB write |
| P95 total latency | 3s | End-to-end |

## Cost Estimation

### Monthly (100 active users, 10 messages/session)

| Service | Cost | Notes |
| --- | --- | --- |
| Bedrock (Claude 3.5 Haiku) | $50-100 | ~100K requests × 150 tokens |
| DynamoDB (on-demand) | $10-15 | 100K writes/month |
| Qdrant queries | $5-10 | Included in agent_core |
| Compute (agent_core ECS) | $20-30 | 0.5 vCPU × 730h |
| CloudWatch (logs) | $2-5 | 50GB logs |
| **Total** | **$87-160** | Scales with users |

## Troubleshooting

### Chat Not Streaming
1. Check browser console for errors
2. Verify WebSocket/SSE support in browser
3. Check firewall allows SSE connections
4. Verify backend is running: `curl localhost:8000/health`

### Messages Not Saving
1. Check DynamoDB tables exist
2. Verify IAM role has DynamoDB PutItem permission
3. Check CloudWatch logs for errors
4. Manual retry: user can resend message

### Agent Core Timeout
1. Check agent_core service is running
2. Verify network connectivity
3. Reduce prompt complexity
4. Increase timeout in config (if needed)

### High Latency (> 5s)
1. Check Bedrock API latency (CloudWatch)
2. Verify Qdrant search performance
3. Check message history size (limit to 20)
4. Monitor concurrent requests

## References

- [Bedrock AgentCore Guide](https://docs.aws.amazon.com/bedrock-agentcore/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Server-Sent Events (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [FastAPI Streaming](https://fastapi.tiangolo.com/advanced/streaming-response/)
