# Dialable Voice Agent Blueprint

This blueprint documents the target architecture for upgrading the current browser voice-test mode into a polished, dialable voice agent. It is written against the current Tech News Mystery implementation as of 2026-06-03.

## Current State

The current app already has a working voice path:

```text
Browser mic
  -> LiveKit room connection and microphone publish
  -> ElevenLabs Realtime Scribe STT WebSocket
  -> backend voice turn endpoint
  -> Agent Core LangGraph voice graph
  -> ElevenLabs TTS proxy
  -> browser audio playback
  -> LangSmith voice telemetry events
```

Important boundary: LiveKit is currently used for room/session transport, tokenized access, microphone publication, and metadata. It does not yet run a LiveKit Agent worker that owns the whole STT -> LLM -> TTS loop. The existing implementation is documented in [Voice Agent Implementation](VOICE_AGENT_IMPLEMENTATION.md).

## Target Experience

The product should support two voice entry points:

1. Web voice bot: a responsive floating bot in the lower-right corner of the app. It should feel like a compact call console, not a marketing widget.
2. Phone voice bot: a real phone number that callers can dial to speak with the same voice agent through LiveKit SIP.

The web bot and phone bot should share the same cognitive layer: Agent Core, LangGraph state, tool policy, user/session persistence, and observability. They should differ only in transport and audio ownership.

## Recommended Target Architecture

For production telephony, add a LiveKit SIP transport adapter under the backend worker layer:

```text
Caller / browser
  -> LiveKit room or SIP participant
  -> backend/app/workers/livekit_voice_agent.py
  -> LiveKit AgentSession
     -> VAD + turn detector + interruption handling + noise cancellation
     -> STT
     -> async Agent Core / LangGraph call
     -> streaming ElevenLabs TTS
  -> LiveKit audio playout
```

LiveKit should own transport, media lifecycle, turn detection, interruptions, DTMF, and call-room dispatch. ElevenLabs should own expressive low-latency TTS. Agent Core/LangGraph should own state, workflow routing, tools, article search, and memory.

Do not run heavy LangGraph/tool work inside audio frame callbacks. The LiveKit worker should enqueue user turns into an async task and stream back speech as soon as the graph/LLM emits usable text.

## Web Corner Bot Design

The frontend should expose a persistent voice affordance in the lower-right corner on desktop and as a bottom-safe control on mobile.

Recommended states:

| State | UI behavior |
| --- | --- |
| Idle | Small circular voice button with tooltip and connection status. |
| Connecting | Compact panel with spinner, provider/room status, and cancel button. |
| Listening | Expanded compact console with waveform/mic level, `Finish turn`, and `End voice`. |
| Thinking | Show transcript, short status, and agent latency timer. |
| Speaking | Show assistant text, animated voice level, `Interrupt`, and `End voice`. |
| Error | Show short actionable error and retry/end controls. |

Responsive rules:

- Desktop: fixed lower-right panel, max width around 360-420 px, never blocking article cards or chat input.
- Mobile: bottom sheet or docked panel above browser safe area, full width minus page padding.
- Keep controls icon-led and predictable: microphone, phone, hang-up, interrupt/stop, minimize.
- Do not put explanatory how-to text inside the panel. Status labels should reflect the actual state.
- Always expose a manual interrupt. Automatic barge-in is valuable, but a visible escape hatch matters.

## Dialable Phone Flow

### Inbound Calls

Target inbound flow:

```text
Caller
  -> PSTN provider / LiveKit phone number
  -> LiveKit inbound SIP trunk
  -> dispatch rule creates an isolated room
  -> LiveKit dispatches the voice agent into that room
  -> AgentSession starts
  -> agent greets caller after room/call readiness
```

Implementation notes:

- Use an individual SIP dispatch rule so each caller gets a dedicated room. Use a `roomPrefix` such as `call-`.
- Include `roomConfig.agents` in the dispatch rule or explicitly dispatch the agent from the backend, passing session metadata.
- Persist phone-call sessions as voice sessions in the existing conversation tables.
- Store SIP metadata on the session: room name, caller number if available, called number, SIP participant identity, trunk ID, dispatch rule ID, and trace ID.
- For inbound calls, greet quickly after the SIP participant and agent are ready. Avoid waiting for the user to speak first unless the product flow demands it.

### Outbound Calls

For future outbound calling, create a LiveKit SIP participant from the backend using an outbound trunk. The backend should dispatch the agent into a room first, then dial the phone number into that room.

For outbound calls, do not play the greeting while the call is still ringing. Wait until the SIP participant is answered and fully joined, then start the agent session.

## Turn-Taking, Interruption, and Noise Cancellation

This is the highest-risk part of the feature. Good phone UX depends on treating turn handling as a first-class system, not a side effect of transcription.

### Recommended LiveKit AgentSession Settings

Use this as the starting point for the LiveKit Agent worker:

```python
from livekit.agents import AgentSession, TurnHandlingOptions
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from livekit.plugins.elevenlabs import TTS

session = AgentSession(
    vad=silero.VAD.load(),
    turn_handling=TurnHandlingOptions(
        turn_detection=MultilingualModel(),
        interruption={
            "enabled": True,
            "mode": "adaptive",
            "min_duration": 0.25,
            "min_words": 1,
            "resume_false_interruption": True,
            "false_interruption_timeout": 2.0,
        },
    ),
    tts=TTS(
        model="eleven_flash_v2_5",
        voice_id=settings.elevenlabs_voice_id,
    ),
    ivr_detection=True,
)
```

Tune after collecting call traces. The exact thresholds should be measured with real phone audio, laptop speakers, and noisy-room tests.

### Turn-Taking Rules

- Use semantic/context-aware turn detection plus VAD, not VAD alone, for production calls.
- Keep VAD enabled even when using STT endpointing, because VAD is needed for responsive barge-in.
- Enable adaptive interruption handling so backchannels like "yeah" or incidental sounds do not always kill the agent response.
- Configure false-interruption resume so the agent can continue when the caller coughs or produces non-word audio.
- Cap user turns with `max_duration` or `max_words` for voicemail, rambling callers, or accidental open lines.
- Track end-of-user-speech to first-playable-agent-audio as the primary latency metric.

### Barge-In Rules

When the caller speaks while the agent is talking:

1. LiveKit detects speech.
2. Agent speech is interrupted immediately.
3. Buffered TTS audio is dropped.
4. LangGraph/Agent Core receives an interruption marker.
5. Any read-only tool result can be ignored if it completes later.
6. Any mutating tool must either be non-interruptible or use an explicit confirmation step before the mutation.

For the current browser implementation, keep the manual `Interrupt` button and browser talk-over monitor. For the LiveKit worker, rely on LiveKit session interruption plus telemetry events.

### Noise Cancellation

- Enable LiveKit Cloud noise cancellation for telephony rooms when available.
- Keep browser capture constraints for web calls: `echoCancellation`, `noiseSuppression`, and `autoGainControl`.
- Prefer server-side LiveKit noise cancellation for phone/SIP calls because browser constraints do not apply to PSTN audio.
- Test with background speech, laptop speakers, headphones, car noise, and low-volume callers.

## ElevenLabs TTS Guidance

Use `eleven_flash_v2_5` as the default low-latency TTS model. It is the right first choice for realtime voice because it balances speed and quality.

Important text handling:

- Normalize phone numbers, dates, currencies, and abbreviations before sending to TTS.
- Avoid markdown, bullets, URLs, and long nested clauses.
- Keep spoken answers short, usually one paragraph.
- Stream text to TTS incrementally in the LiveKit worker. The current browser path buffers the TTS blob before playback, which is acceptable for test mode but not the final low-latency phone experience.

## LangGraph and Agent Core Integration

The LiveKit SIP adapter should call the existing backend voice-agent path asynchronously. Recommended flow:

```text
committed user turn
  -> build voice request payload
  -> include call/session metadata and interruption state
  -> invoke Agent Core / LangGraph
  -> stream or chunk returned text to TTS
  -> save final transcript and assistant text
```

State strategy:

- Keep the voice graph lightweight.
- Pass only the latest 3-5 turns plus a compact session summary.
- Use LangGraph checkpointing for thread-level state if the future call workflow becomes multi-step, such as collecting caller details or scheduling a handoff.
- Keep durable product history in DynamoDB as the source of truth for the UI.
- Do not load full chat history into every phone turn.

Tool strategy:

- Read-only tools can be interruptible.
- Mutating tools require confirmation and should call `disallow_interruptions()` or equivalent protection while the mutation is committed.
- Long-running tools should emit filler speech quickly, such as "Let me pull that up," before starting the slow operation.
- Every tool call should carry the current `session_id`, `call_id`, `trace_id`, and user identity when available.

## DTMF and IVR

Phone users press keys. The dialable agent should support both spoken intent and keypad intent.

Recommended behavior:

- Enable `ivr_detection=True` on `AgentSession`.
- Listen for DTMF events in the room and route digits to the same LangGraph state machine as speech.
- Support simple command mappings:
  - `0`: human handoff or fallback.
  - `1`: latest AI news.
  - `2`: summarize trending topics.
  - `#`: finish digit entry.
  - `*`: cancel current digit entry.
- Store DTMF inputs as structured events, not plain chat text only.

## Handoffs and Failure Recovery

Production phone agents need a graceful way out.

Handoff triggers:

- caller asks for a human;
- repeated ASR failure;
- repeated tool failure;
- safety or policy uncertainty;
- account/private-data request that the agent cannot satisfy;
- call duration exceeds expected window.

Target behavior:

- Summarize the call so far.
- Attach the summary to the session record.
- Transfer to a human queue or SIP trunk when available.
- If transfer is unavailable, offer to save the request and end cleanly.

## Observability

Continue using LangSmith for voice telemetry, but upgrade the LiveKit worker path to OpenTelemetry spans so the trace shows the full chain:

```text
call
  -> LiveKit room/job
  -> STT
  -> turn detection
  -> Agent Core / LangGraph
  -> tool calls
  -> TTS
  -> playback
  -> interruption / handoff / hangup
```

Required metrics:

| Metric | Why it matters |
| --- | --- |
| User end-of-speech to first audio | Main perceived latency metric. |
| STT partial latency | Detect transcription provider lag. |
| End-of-turn decision latency | Detect VAD/semantic endpointing lag. |
| LLM/graph latency | Detect Agent Core or tool delays. |
| TTS time to first byte | Detect voice synthesis delay. |
| Interruption detection latency | Measures barge-in quality. |
| False interruption count | Detects overly sensitive VAD/noise settings. |
| Resume-after-false-interruption count | Confirms recovery behavior. |
| DTMF events | Debugs phone keypad flows. |
| SIP call status and hangup reason | Debugs carrier/trunk failures. |

## Implementation Plan

### Phase 1: Web Bot Polish

- Replace the voice tab dependency with a reusable floating voice bot component.
- Keep existing backend endpoints.
- Preserve current browser STT/TTS implementation.
- Improve responsive placement, status states, manual interrupt, and telemetry display.
- Compute a unified frontend metric from STT commit to TTS playback start.

### Phase 2: Backend LiveKit SIP Adapter Prototype

- Add the backend LiveKit SIP transport adapter.
- Configure Silero VAD, multilingual turn detector, adaptive interruption handling, and ElevenLabs TTS.
- Route committed turns to the existing backend or Agent Core.
- Emit LangSmith/OpenTelemetry spans.
- Test locally in LiveKit console mode before SIP.

Prototype location: [../backend/app/workers/livekit_voice_agent.py](../backend/app/workers/livekit_voice_agent.py), with run instructions in [../backend/LIVEKIT_VOICE_WORKER.md](../backend/LIVEKIT_VOICE_WORKER.md). This is a transport adapter for LiveKit-owned phone media, not a second voice-agent brain.

The backend service-token bridge for phone turns is `POST /v1/chat/voice/sip/message`. It requires `VOICE_WORKER_SERVICE_TOKEN` and creates a phone voice session automatically when the worker does not provide one.

### Phase 3: Inbound SIP

- Configure LiveKit phone number or inbound SIP trunk.
- Add individual dispatch rule with `call-` room prefix and agent dispatch.
- Persist call metadata in voice sessions.
- Handle DTMF and call hangup events.
- Add production telemetry dashboards.

### Phase 4: Production Hardening

- Add human handoff path.
- Add call-recording/transcript retention policy if required.
- Add load/concurrency tests for simultaneous calls.
- Add latency and false-interruption evaluation set.
- Add compliance checks for consent, recording, and outbound calling rules before enabling broad phone use.

## Open Decisions

- Whether the phone agent should eventually call Agent Core directly or keep using the backend SIP bridge `/v1/chat/voice/sip/message`.
- Whether to keep ElevenLabs STT for web mode or standardize STT inside LiveKit Agent workers.
- Whether phone calls should be anonymous sessions or require account linking.
- Which SIP provider/phone number path to use: LiveKit phone numbers, Twilio, Telnyx, or another trunk provider.
- Whether to implement human transfer now or initially provide only transcript capture and callback.

## Researched References

These references were searched and reviewed while preparing this blueprint:

- LiveKit turns overview, turn detection, interruptions, false interruption handling, and noise cancellation: https://docs.livekit.io/agents/logic/turns/
- LiveKit turn-taking tuning: https://docs.livekit.io/agents/logic/turns/tuning/
- LiveKit adaptive interruption handling: https://docs.livekit.io/agents/logic/turns/adaptive-interruption-handling/
- LiveKit SIP dispatch rules and agent dispatch via room configuration: https://docs.livekit.io/telephony/accepting-calls/dispatch-rule/
- LiveKit agent dispatch and metadata: https://docs.livekit.io/agents/server/agent-dispatch/
- LiveKit telephony overview and noise cancellation for calls: https://docs.livekit.io/telephony/
- LiveKit DTMF handling and IVR detection: https://docs.livekit.io/telephony/features/dtmf/
- LiveKit outbound calls and SIP participant creation: https://docs.livekit.io/telephony/making-calls/outbound-calls/
- LiveKit function tools and interruption behavior for long-running tools: https://docs.livekit.io/agents/logic/tools/definition/
- LiveKit ElevenLabs TTS plugin and default model parameters: https://docs.livekit.io/agents/models/tts/elevenlabs/
- ElevenLabs model overview, Flash v2.5 latency guidance, and text-normalization warning: https://elevenlabs.io/docs/overview/models
- LangGraph persistence and checkpointing: https://docs.langchain.com/oss/python/langgraph/persistence
- LangSmith LiveKit tracing with OpenTelemetry: https://docs.langchain.com/langsmith/trace-with-livekit
