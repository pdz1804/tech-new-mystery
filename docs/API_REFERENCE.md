# API Reference

Base path: `/v1`

## Chat Endpoints

- `POST /chat/sessions`: create chat session
- `GET /chat/sessions`: list sessions
- `GET /chat/sessions/{session_id}`: get session
- `PUT /chat/sessions/{session_id}`: rename session
- `PUT /chat/sessions/{session_id}/archive`: archive session
- `PUT /chat/sessions/{session_id}/restore`: restore session
- `DELETE /chat/sessions/{session_id}`: delete session and messages
- `GET /chat/sessions/{session_id}/messages`: list messages
- `POST /chat/sessions/{session_id}/message`: add user message
- `POST /chat/sessions/{session_id}/stream`: stream assistant response (SSE)

SSE event types:
- `token`
- `tool_invocation`
- `tool_result`
- `warning`
- `error`
- `done`

## Clustering Endpoints

- `GET /clusters`: list clusters
- `GET /clusters/trending`: trending clusters
- `GET /clusters/{cluster_id}`: cluster detail
- `GET /clusters/{cluster_id}/articles`: cluster article list

Admin evaluation/config endpoints are mounted under `/v1/admin`.

## Auth

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`

JWT bearer token required for authenticated routes.

---

## Health Endpoints

- `GET /health` — liveness check `{"status":"ok"}`
- `GET /health/agent-core` — circuit breaker state `{"status":"ok","circuit_state":"closed","failure_count":0}`
- `GET /health/llm` — LLM provider reachability
- `GET /health/celery` — Celery broker reachability

