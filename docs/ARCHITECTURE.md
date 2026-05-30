# Architecture

## Services

- `frontend` (Next.js): web UI including `/chatbot`, `/topics`, `/clusters/[slug]`.
- `api` (FastAPI): `/v1` endpoints for auth, articles, search, clustering, chat.
- `worker` (Celery): background processing including clustering jobs.
- `beat` (Celery Beat): schedules periodic jobs.
- `agent-core` (FastAPI/BedrockAgentCoreApp): separate runtime for chatbot agent orchestration. Run locally with `python -m agent_core.server` (port 8080).

## Chatbot Feature

### Request Flow

1. Frontend sends message to `POST /v1/chat/sessions/{session_id}/stream`.
2. API validates ownership/auth and saves user message in DynamoDB.
3. API loads recent messages as context and calls `agent-core` via:
   - **Production**: `boto3.client('bedrock-agentcore').invoke_agent_runtime()` (configured via `AGENT_CORE_RUNTIME_ARN`)
   - **Local dev**: direct HTTP POST to `http://localhost:8080/invocations` (configured via `AGENT_CORE_BASE_URL`)
4. Agent runtime executes a LangGraph `create_react_agent` flow backed by AWS Bedrock Converse (`ChatBedrockConverse`) and streams `astream_events` back.
5. API relays SSE events to frontend via a per-request `httpx.AsyncClient` (avoids connection-pool contention) and saves the assistant response in DynamoDB.

### Agent Tools

- `semantic_search` — Qdrant vector search over the article corpus (`asyncio.to_thread` wraps the sync Qdrant client).
- `browse_web` — AWS Bedrock AgentCore managed Browser (Playwright/CDP); requires `BROWSER_ID` env var.
- `execute_code` — AWS Bedrock AgentCore managed Code Interpreter; requires `CODE_INTERPRETER_ID` env var.

### Circuit Breaker

A module-level `AgentCoreCircuitBreaker` (threshold 5 failures, 30 s recovery) protects the API from a degraded agent-core. State is exposed at `GET /health/agent-core`.

### Chat Persistence

- Sessions table: `tech-news-conversation_sessions`
- Messages table: `tech-news-conversation_messages`
- TTL: 90 days
- Session metadata (`last_message_at`, `message_count`) updates on every persisted message.

### Long-term Memory (production only)

`AgentMemory` wraps `bedrock_agentcore.memory.client.MemoryClient`. When `MEMORY_ID` is set it loads the last 5 turns before each agent call and persists each completed exchange. When `MEMORY_ID` is absent (local dev) it is a no-op and the agent falls back to the DynamoDB `recent_events` passed in the payload context.

## Clustering Feature

### Clustering Flow

1. Celery worker fetches recent articles from DynamoDB.
2. Embedding service generates (or reuses cached) OpenAI `text-embedding-3-small` vectors via Qdrant.
3. `ClusteringEngine` runs HDBSCAN with cosine distance (`algorithm="generic"`) and configurable `min_cluster_size` / `min_samples`.
4. Evaluation pipeline computes three metrics per run:
   - Silhouette score (higher is better)
   - Davies-Bouldin index (lower is better)
   - Calinski-Harabasz index (higher is better)
5. Cluster metadata, article assignments, and evaluation results are written to DynamoDB for topic browsing and admin review.

### Admin Clustering API (`/v1/admin`)

- `GET/PUT /admin/clustering/config` — read/update HDBSCAN parameters and metric weights.
- `GET /admin/clustering/evaluations` — browse historical evaluation runs.
- `POST /admin/clustering/trigger` — manually trigger a clustering job.

## Data Stores

- DynamoDB: core entities, chat sessions/messages, cluster metadata/evaluations, clustering config/evaluations.
- Redis: Celery broker/backend and caching.
- Qdrant: semantic vector retrieval (articles corpus, embedding cache).
- S3: media assets (presigned URLs, 24 h TTL).

