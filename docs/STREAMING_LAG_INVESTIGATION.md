# Streaming Lag Investigation (May 31, 2026)

## Current Status
Token-by-token streaming is **working end-to-end** but has **~2500ms buffering lag** between when backend timestamps tokens and when browser receives them.

## Observed Behavior
- **Real-time SSE streaming**: Backend properly receives tokens from Agent Core and forwards to frontend
- **Progressive rendering**: Browser receives tokens and renders progressively (not all at once)
- **Lag pattern**: Consistent ~2500ms lag on mid-stream tokens, reducing to ~1400ms on final done event
- **Token interval**: Tokens are generated at 25-30ms intervals by Agent Core
- **Visual effect**: Acceptable. While technically buffered, the user perceives streaming because tokens render progressively once received

### Timeline Example (May 31 test)
```
Server timestamps:  1780162235082 → 1780162235230 (tokens in 148ms)
Browser receives:   +2500ms lag   → +2490ms lag
Done event:         +1400ms lag
```

## Root Cause Analysis

### What's NOT the issue
✗ React rendering (removed flushSync, using native batching)
✗ Markdown parsing (memoized, only re-parses on content change)  
✗ Frontend SSE parser (correctly uses readline, no buffering)
✗ Backend router SSE flushing (5ms pause between frames)

### What's likely buffering
The ~2500ms consistent delay across all tokens suggests buffering at one of these layers:

1. **BedrockAgentCoreApp response buffering** (agent_core/server.py)
   - Uvicorn/Starlette may be buffering chunks before sending
   - HTTP response body might require certain buffer size before flushing

2. **httpx client stream buffering** (backend/app/integrations/agent_core_client.py)
   - `response.aiter_lines()` may wait for internal buffer threshold
   - Per-request AsyncClient setup is correct, but stream reading might still buffer

3. **Network/TCP buffering**
   - Unlikely for localhost, but possible in production

## Workaround Attempts & Results

| Attempt | Result | Notes |
|---------|--------|-------|
| Remove flushSync | No improvement (still 2500ms) | React batching is fine, issue is HTTP-level |
| Memoize markdown parsing | No improvement | Parsing is fast, not the bottleneck |
| 5ms SSE flush pause | No improvement | Already in place |
| Restart Agent Core | No improvement | New process, same lag pattern |

## Production Impact
- **Acceptable**: Visual streaming effect is preserved (tokens appear progressively)
- **Not ideal**: 2.5s initial lag before first token visible (could feel sluggish)
- **Baseline**: First token still takes ~2.5s, then tokens arrive every 25-30ms after that

## Recommendations for Future Work

### High Priority
1. **Enable HTTP/2 or WebSocket streaming** to bypass HTTP/1.1 buffering
2. **Check Starlette/Uvicorn response body size threshold** — if < 4KB buffering, increase

### Medium Priority  
3. **Add explicit stream flushing at ASGI level** — set `send({"type": "http.response.body", ...})` with `more_body=True` immediately after each frame
4. **Profile with Network tab** — capture exact timings at HTTP level (TLS, TCP, buffering)

### Low Priority
5. Explore httpx chunk size configuration
6. Add distributed tracing (OpenTelemetry) to track lag across backend→agent→browser

## Code References
- Frontend streaming consumer: [frontend/src/lib/api/chat.ts](../../frontend/src/lib/api/chat.ts)
- Frontend hook: [frontend/src/hooks/useStreamChat.ts](../../frontend/src/hooks/useStreamChat.ts)  
- Backend router: [backend/app/api/v1/chat/router.py](../../backend/app/api/v1/chat/router.py)
- Agent Core server: [agent_core/server.py](../../agent_core/server.py)

## Testing Notes
- Tested May 30-31, 2026 with Agent Core running on localhost
- Consistent lag across multiple queries
- Streaming works correctly in production (AWS Bedrock), lag may differ due to network factors
