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

## Voice Agent Endpoints

Voice endpoints use the same JWT bearer auth and base path `/v1`. Voice turns are stored as normal chat messages, but the frontend keeps voice-test sessions separate from text-chat sessions.

- `POST /chat/voice/stt-token`: mint a single-use ElevenLabs Realtime Scribe token. Returns `token`, `model_id`, and `audio_format`.
- `POST /chat/voice/livekit-session`: mint a LiveKit room token for a voice session. Request body includes `session_id`. Returns `transport`, `server_url`, `room`, `participant_token`, `agent_name`, `trace_id`, and `expires_in`.
- `POST /chat/voice/message`: run one non-streaming voice-agent turn. Request body includes `session_id` and `content`. Returns the assistant `content`, `latency_ms`, `input_chars`, and `output_chars`.
- `POST /chat/voice/speech`: proxy ElevenLabs TTS for a spoken answer. Request body includes `text`; response is `audio/mpeg`.
- `POST /chat/voice/events`: record voice telemetry. Request body can include `session_id`, `phase`, `provider`, `transport`, `livekit_room`, `transcript_chars`, `output_chars`, and `latency_ms`. Returns `trace_id` and `tracing_enabled`.

The browser sends microphone audio directly to ElevenLabs STT over WebSocket after receiving the token, joins LiveKit with the room token for transport/session metadata, and uses `/chat/voice/speech` for TTS playback. During TTS playback, the frontend can stop audio and reopen STT when the local echo-cancelled talk-over monitor detects a sustained user interruption.

## Clustering Endpoints

- `GET /clusters`: list clusters
- `GET /clusters/pca-map`: cached article embedding PCA map; queues worker generation on cache miss
- `GET /clusters/trending`: trending clusters
- `GET /clusters/{cluster_id}`: cluster detail
- `GET /clusters/{cluster_id}/articles`: cluster article list

### `GET /clusters/pca-map`

Query parameters:

- `limit` (int, optional): maximum article nodes to project. Default `250`, max `500`.
- `cluster_ids` (string, repeated, optional): cluster IDs to include.

Response status values:

- `ready`: map payload is cached and ready to render.
- `queued`: worker generation has been queued; client should poll again.
- `unavailable`: cache or worker dispatch failed; page should remain usable.

The response contains article-level PCA points. Each point includes `article_id`, `slug`, `title`, `cluster_id`, `cluster_label`, normalized `x/y` coordinates, and `confidence_score`.

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
