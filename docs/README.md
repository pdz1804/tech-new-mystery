# Documentation Index

- [API Reference](API_REFERENCE.md): current HTTP endpoints and chat/cluster APIs.
- [Architecture](ARCHITECTURE.md): runtime components, data flow, persistence.
- [Deployment Architecture](DEPLOYMENT_ARCHITECTURE.md): Terraform + ECS + CI/CD behavior.
- [Manual Startup](MANUAL_STARTUP.md): local run steps for frontend/backend/agent-core.
- [GitHub CI/CD](GITHUB_CICD.md): workflow behavior and required variables.

---

## Streaming Architecture

The chat system implements real-time token-by-token streaming via Server-Sent Events (SSE):

1. **Backend (FastAPI)**: 
   - Calls Agent Core `/chat/stream` with `ConverseStream` API
   - Streams events: `delta` (tokens), `content_block_start/stop`, `input_json_delta` (tool results)
   - Buffers tokens and sends SSE events with ~50ms latency

2. **Frontend (React)**:
   - Opens EventSource connection to `/v1/chat/sessions/{id}/stream`
   - Parses SSE events and updates React state
   - Memoized markdown parsing prevents re-renders on every token
   - Renders progressively as tokens arrive (~50-100ms first token)

3. **Tool Results**:
   - Tool execution (search, browse, code) returns JSON delta events
   - Frontend collects full tool result and displays in collapsible container
   - Final answer tokens stream after tool results

---

## Features

### Clustering

- HDBSCAN clustering on article embeddings (cosine distance, `algorithm=generic`).
- Embeddings: OpenAI `text-embedding-3-small` via Qdrant.
- Evaluation metrics per run: Silhouette, Davies-Bouldin, Calinski-Harabasz.
- Admin API for configuration, evaluation history, and manual triggering.
- Topic browsing UI at `/topics` and `/clusters/[slug]`.

**Cluster endpoints** (`/v1/clusters`):

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/clusters` | List clusters (pagination, sort by size/recency/diversity) |
| `GET` | `/clusters/trending` | Trending clusters |
| `GET` | `/clusters/{cluster_id}` | Cluster detail |
| `GET` | `/clusters/{cluster_id}/articles` | Articles in a cluster |

**Admin cluster endpoints** (`/v1/admin`):

| Method | Path | Description |
|--------|------|-------------|
| `GET/PUT` | `/admin/clustering/config` | Read/update HDBSCAN params and metric weights |
| `GET` | `/admin/clustering/evaluations` | Evaluation run history |
| `POST` | `/admin/clustering/trigger` | Manually trigger clustering |

### Chatbot

- LangGraph `create_react_agent` backed by AWS Bedrock Converse.
- Three tools: `semantic_search` (Qdrant), `browse_web` (AgentCore Browser), `execute_code` (AgentCore Code Interpreter).
- SSE streaming via per-request `httpx.AsyncClient`; circuit breaker on agent-core connection.
- Long-term memory via AWS Bedrock AgentCore Memory (`MEMORY_ID`); falls back to DynamoDB session context when absent.
- Chat sessions and messages persisted in DynamoDB (TTL 90 days).

**Chat endpoints** (`/v1/chat`):

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/chat/sessions` | Create session |
| `GET` | `/chat/sessions` | List sessions |
| `GET` | `/chat/sessions/{id}` | Get session |
| `PUT` | `/chat/sessions/{id}` | Rename session |
| `PUT` | `/chat/sessions/{id}/archive` | Archive session |
| `PUT` | `/chat/sessions/{id}/restore` | Restore session |
| `DELETE` | `/chat/sessions/{id}` | Delete session |
| `GET` | `/chat/sessions/{id}/messages` | List messages |
| `POST` | `/chat/sessions/{id}/message` | Add user message |
| `POST` | `/chat/sessions/{id}/stream` | Stream assistant response (SSE) |

---

## Agent Core Startup

**Docker (recommended):**
```powershell
cd infra && docker compose up agent-core -d
```

**Direct (local dev without Docker):**
```bash
# In the project root with venv activated
cd agent_core
python -m agent_core.server   # starts BedrockAgentCoreApp on port 8080
```

Required env vars: `OPENAI_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`.  
Optional: `MEMORY_ID` (AgentCore Memory), `BROWSER_ID`, `CODE_INTERPRETER_ID`.

See [Manual Startup](MANUAL_STARTUP.md) for full local dev instructions.

