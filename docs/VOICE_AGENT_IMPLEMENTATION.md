# Voice Agent Implementation Notes

## Current Pipeline

The app currently uses this voice path:

```text
Browser mic
  -> LiveKit room connection and browser microphone publish
  -> ElevenLabs Realtime Scribe STT WebSocket with VAD commit strategy
  -> dedicated voice session / low-latency AgentCore voice call
  -> ElevenLabs TTS through backend streaming proxy
  -> browser audio element playback
  -> LangSmith voice telemetry events
```

LiveKit is currently used as the realtime room/session transport, short-lived token boundary, microphone publication layer, and room/connection telemetry source. ElevenLabs is used for both STT and TTS. The same AgentCore search/browser capabilities are reused, but voice mode calls a separate low-latency agent path instead of rendering the chat SSE stream.

Important current boundary: this app does not yet run a separate LiveKit Agent worker that owns the whole audio pipeline. The browser joins a LiveKit room and publishes the microphone, while the browser also sends PCM audio directly to the ElevenLabs Realtime STT WebSocket using a single-use token minted by the backend.

Chat mode and voice mode use separate conversation sessions in the Agent page. The sidebar filters sessions by mode:

* Chat sessions are normal conversation sessions.
* Voice sessions are created with title `Voice agent session` and description `Dedicated voice-agent testing session`.

The chat tab keeps the existing text stream and mic-enabled chat composer. The voice tab sends spoken turns to `POST /v1/chat/voice/message` and receives one final JSON answer rather than rendering SSE tokens. AgentCore receives `mode=voice`, uses a short spoken-answer prompt, disables model streaming for that graph, and caps generation for lower latency.

When an existing voice session is selected, the voice cards hydrate from the latest persisted user and assistant messages in that voice session. Live turns still update the cards immediately from local state.

## Current Voice Turn Details

### STT and VAD

STT is handled by ElevenLabs Realtime Scribe from the browser:

* Backend endpoint: `POST /v1/chat/voice/stt-token`
* Provider WebSocket: `wss://api.elevenlabs.io/v1/speech-to-text/realtime`
* Audio sent by browser: PCM 16-bit, downsampled to `16000` Hz
* Configured model: `ELEVENLABS_STT_MODEL_ID`, currently `scribe_v2_realtime`
* Configured format: `ELEVENLABS_STT_AUDIO_FORMAT`, currently `pcm_16000`

The current VAD configuration is passed as ElevenLabs STT WebSocket query parameters:

| Parameter | Current value | Purpose |
| --- | --- | --- |
| `commit_strategy` | `vad` | Commit a transcript when voice activity ends |
| `vad_silence_threshold_secs` | `1.2` | Silence window before committing a turn |
| `vad_threshold` | `0.4` | Voice activity sensitivity |
| `min_speech_duration_ms` | `100` | Ignore very short non-speech bursts |
| `min_silence_duration_ms` | `100` | Minimum silence segment considered by VAD |
| `no_verbatim` | `true` | Prefer cleaner transcription text |

The frontend listens for `partial_transcript` events to update status text and for `committed_transcript` or `committed_transcript_with_timestamps` to finalize the user turn. When a committed transcript arrives, local mic capture and the STT socket are closed, `stt_committed` is recorded, and the text is sent to the voice agent endpoint.

### Browser Audio Capture

The browser captures microphone audio with:

* `echoCancellation: true`
* `noiseSuppression: true`
* `autoGainControl: true`
* `channelCount: 1`

Audio is read through a `ScriptProcessorNode`, downsampled to 16 kHz, converted to 16-bit PCM, base64 encoded, and sent as ElevenLabs `input_audio_chunk` messages.

### Voice Agent LLM Turn

The backend endpoint `POST /v1/chat/voice/message`:

* validates the selected voice session
* loads the latest six persisted messages for short-term context
* initializes request-scoped AgentCore memory
* saves the user transcript as a normal `user` message
* invokes AgentCore with `mode="voice"` and context flags: `request_scope=voice`, `agent_mode=voice`, `response_style=one_spoken_paragraph`, and `latency_priority=high`
* saves the final assistant response as a normal `assistant` message
* records `agent_turn_completed` in LangSmith
* returns one JSON response with `content`, `latency_ms`, `input_chars`, and `output_chars`

The backend timeout for this voice agent turn is currently 90 seconds. The UI shows this returned `latency_ms` in the voice console. This latency is the backend voice-agent turn duration, not full mouth-to-ear audio latency.

### TTS and Playback

TTS is handled by ElevenLabs through the backend:

* Frontend API: `POST /v1/chat/voice/speech`
* Provider endpoint: `https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream`
* Configured model: `ELEVENLABS_TTS_MODEL_ID`, currently `eleven_flash_v2_5`
* Configured output: `ELEVENLABS_TTS_OUTPUT_FORMAT`, currently `mp3_44100_128`

The backend proxies ElevenLabs streaming bytes with `StreamingResponse`, keeping the long-lived API key server-side. The current frontend implementation calls `response.blob()` and then plays the resulting object URL through an `HTMLAudioElement`. That means the provider/backend path is streaming, but browser playback currently starts after the frontend has received the TTS blob.

Before sending text to TTS, markdown-heavy formatting is stripped and the speech payload is capped to 1200 characters.

## Deployment Configuration

Production ECS tasks receive voice-agent configuration from two places:

* Non-secret runtime flags are injected by Terraform in `infra/terraform/ecs.tf`.
* Sensitive values are loaded from the app Secrets Manager JSON secret.

Required Secrets Manager JSON keys:

| Secret key | Purpose |
| --- | --- |
| `LANGSMITH_API_KEY` | LangSmith trace ingestion for voice metrics |
| `ELEVENLABS_API_KEY` | ElevenLabs realtime STT and streaming TTS |
| `ELEVENLABS_VOICE_ID` | ElevenLabs TTS voice identity |
| `LIVEKIT_API_KEY` | LiveKit token minting |
| `LIVEKIT_API_SECRET` | LiveKit token signing |

Production runtime values currently wired by Terraform:

| Env var | Value |
| --- | --- |
| `LANGSMITH_TRACING` | `true` |
| `LANGSMITH_ENDPOINT` | `https://api.smith.langchain.com` |
| `LANGSMITH_PROJECT` | `tech-news-voice` |
| `ELEVENLABS_STT_MODEL_ID` | `scribe_v2_realtime` |
| `ELEVENLABS_STT_AUDIO_FORMAT` | `pcm_16000` |
| `ELEVENLABS_TTS_MODEL_ID` | `eleven_flash_v2_5` |
| `ELEVENLABS_TTS_OUTPUT_FORMAT` | `mp3_44100_128` |
| `ELEVENLABS_TIMEOUT` | `45` |
| `LIVEKIT_URL` | `wss://virtual-interview-191g0s6f.livekit.cloud` |
| `LIVEKIT_AGENT_NAME` | `tech-news-voice-agent` |
| `LIVEKIT_TOKEN_TTL_SECONDS` | `900` |

Use `infra/terraform/scripts/put-app-secret-from-env.ps1` to sync local `.env` values into the app secret without committing raw credentials. The helper strips surrounding single or double quotes from `.env` values before uploading them.

The GitHub Actions deploy workflow also syncs these values from GitHub Actions secrets before Terraform applies new ECS task definitions. This matters because ECS resolves JSON keys from Secrets Manager while placing a task; if a new key is missing, the task never starts and the deploy waiter eventually fails.

Required GitHub Actions secrets for the voice feature:

| Secret | Purpose |
| --- | --- |
| `LANGSMITH_API_KEY` | LangSmith trace ingestion |
| `ELEVENLABS_API_KEY` | ElevenLabs STT/TTS API access |
| `ELEVENLABS_VOICE_ID` | ElevenLabs TTS voice |
| `LIVEKIT_API_KEY` | LiveKit token signing public key |
| `LIVEKIT_API_SECRET` | LiveKit token signing secret |

Related existing app secrets such as `SECRET_KEY`, `JWT_SECRET_KEY`, `OPENAI_API_KEY`, `QDRANT_URL`, and `QDRANT_API_KEY` must also be present either in GitHub Actions secrets or already in the app Secrets Manager JSON payload.

## LiveKit Capabilities Used

* Tokenized room access with short-lived JWTs from `/v1/chat/voice/livekit-session`.
* Browser room connection via `livekit-client`.
* Local microphone publishing with echo-cancellation-capable browser capture.
* Connection lifecycle events such as disconnect and connection quality changes.
* Room metadata ties each voice session to the chat session, agent name, ElevenLabs model IDs, and LangSmith project.

Currently not implemented:

* A separate LiveKit Agent worker that performs STT, LLM, TTS, turn detection, and audio frame flushing server-side.
* LiveKit-native automatic barge-in based on continuous remote VAD.
* LiveKit data-channel transcript streaming between the agent worker and UI.

Those are viable future upgrades, but the present implementation intentionally keeps the voice pipeline in the browser plus backend proxy layer.

## Critical Voice Metrics

The implementation records these phases through `/v1/chat/voice/events` for LangSmith tracing:

* `livekit_room_ready`
* `livekit_connection_quality`
* `stt_committed`
* `tts_playback_started`
* `tts_playback_ended`
* `voice_interrupted`
* `tts_playback_failed`
* `agent_turn_completed`
* `voice_input_failed`

The voice UI currently shows the backend voice-agent `latency_ms` on the voice console after a completed spoken turn. LangSmith receives additional phase events for STT commit latency, TTS playback start/end, interruption, and failures where available.

The chat UI also shows compact message metrics on hover:

* Estimated input/output token split.
* Estimated cost.
* Total response latency.
* Time to first token.
* Tool call count.

Cost is marked as estimated because the runtime can use multiple provider/model paths. The current voice endpoint returns character counts rather than exact provider token usage or ElevenLabs billing units.

Current metric gaps:

* Full user-finished-speaking to first-audio-playback latency is not yet computed as one unified metric.
* The frontend does not yet measure first decoded audio frame playback.
* LiveKit connection quality is traced as an event, but quality values are not yet displayed in the UI.

## Voice Controls

* Chat mode keeps the original composer mic behavior.
* Voice mode has its own large `Start voice` / `Speak now` control and dedicated voice session list.
* While TTS is speaking, the main control changes to `Interrupt`.
* Pressing `Interrupt` stops current ElevenLabs playback, records `voice_interrupted`, and starts a fresh STT turn.
* While listening, the main control shows `Finish turn`; this stops listening and lets the committed transcript flow continue.
* The `End voice` control fully turns voice mode off, closes STT, stops playback, and disconnects LiveKit.
* After a TTS response finishes, voice mode automatically re-arms listening for the next conversational turn.

## Agent Prompt and Tool Mode

The standard chat agent keeps the full analyst prompt and streaming response path. The voice agent uses a separate prompt:

* one natural spoken paragraph
* direct answer first
* no markdown, headings, bullets, emojis, or tool explanations
* compact spoken citations
* short generation cap for latency

Code Interpreter is parked for now. The implementation remains in the codebase, but it is commented out of active tool registration in `agent_core/tools.py` and the backend tool registry. A deployment or AgentCore runtime restart is required after prompt/tool changes; otherwise the running runtime may still serve the old prompt and mention Code Interpreter.

## Edge Cases and Handling

### Barge-in / User Interrupts Agent Speech

Risk: the user starts a new query while TTS is still playing.

Current handling:

* While TTS is active, the UI shows an `Interrupt` button.
* Pressing `Interrupt` stops current playback and starts a fresh STT turn.
* `stopPlayback()` aborts the active TTS request/audio element before starting STT.
* `voice_interrupted` is recorded for observability.

Future improvement:

* A production LiveKit Agent worker can keep turn detection active continuously and perform automatic barge-in without requiring a click.
* If the frontend keeps the current browser-owned pipeline, add client-side continuous VAD during TTS to trigger interruption automatically.

### No Speech Detected

Risk: VAD closes a turn with no committed transcript.

Current handling:

* The UI shows `No speech detected`.
* No empty chat message is sent.

### Microphone Permission Denied

Risk: browser denies mic access.

Current handling:

* Voice startup catches the error and shows the browser/provider error message.
* A `voice_input_failed` telemetry event is recorded.

### LiveKit Disconnects Mid-turn

Risk: room disconnects while the user is speaking.

Current handling:

* LiveKit disconnect events update status.
* STT cleanup runs independently so dangling local audio processors are stopped.

Future improvement:

* Attempt automatic room reconnect with exponential backoff and keep the same room when possible.

### ElevenLabs STT WebSocket Failure

Risk: STT socket fails or the single-use token expires.

Current handling:

* STT token is requested just-in-time.
* WebSocket errors surface in the status line.
* Local audio resources are cleaned up.

### ElevenLabs TTS Failure

Risk: TTS request fails after the LLM response is ready.

Current handling:

* The text response remains visible.
* Playback status shows failure.
* `tts_playback_failed` is traced.

### Agent Takes Too Long

Risk: latency feels unnatural after the user finishes speaking.

Current handling:

* Voice mode avoids frontend SSE rendering and returns a single short answer.
* AgentCore voice graph disables model streaming and uses a lower max-token cap.
* The voice endpoint returns `latency_ms` for the backend voice turn.
* The backend voice endpoint times out after 90 seconds.

Future improvement:

* Compute a unified voice latency metric from VAD commit to first playable audio.
* Start browser playback from a streaming source instead of waiting for `response.blob()`.

### Markdown Sounds Bad When Spoken

Risk: code blocks, bullets, and links are read aloud awkwardly.

Current handling:

* TTS text is sanitized to strip markdown-heavy formatting.
* Speech payload is capped to keep replies concise.

### Echo / Feedback

Risk: TTS audio is picked up by the microphone.

Current handling:

* Browser mic capture requests echo cancellation, noise suppression, and auto gain control.
* Starting a new STT turn stops current TTS playback first.

Future improvement:

* Route all realtime audio through a LiveKit Agent worker with built-in turn detection, echo control, and interruption semantics.

## References

* LangChain voice agent guide: https://docs.langchain.com/oss/python/langchain/voice-agent
* LangChain voice agent LangSmith section: https://docs.langchain.com/oss/python/langchain/voice-agent#langsmith
* LangSmith LiveKit tracing: https://docs.langchain.com/langsmith/trace-with-livekit
* LiveKit voice AI quickstart: https://docs.livekit.io/agents/start/voice-ai/
* LiveKit LangChain integration: https://docs.livekit.io/agents/models/llm/langchain/
* LiveKit token docs: https://docs.livekit.io/frontends/authentication/tokens
* ElevenLabs realtime STT: https://elevenlabs.io/docs/api-reference/speech-to-text/v-1-speech-to-text-realtime
* ElevenLabs STT commit strategies: https://elevenlabs.io/docs/eleven-api/guides/how-to/speech-to-text/realtime/transcripts-and-commit-strategies
* ElevenLabs streaming TTS: https://elevenlabs.io/docs/api-reference/text-to-speech/stream

## Deployment Troubleshooting Notes

### ECS Waiter: `ServicesStable` Max Attempts Exceeded

Observed failure:

```text
aws ecs wait services-stable --cluster "$ECS_CLUSTER" --services api frontend worker beat clustering
Waiter ServicesStable failed: Max attempts exceeded
```

Root cause found in ECS service events:

```text
ResourceInitializationError: unable to retrieve secret from asm:
retrieved secret from Secrets Manager did not contain json key LANGSMITH_API_KEY
```

Meaning: Terraform registered new task definitions that reference the voice-agent secret keys, but the production app secret did not yet contain those JSON keys. The old tasks stayed running, while the new `api`, `worker`, `beat`, and `clustering` deployments remained in progress with failed task placements.

Fix path:

1. Add the required voice secrets to GitHub Actions secrets.
2. Re-run the deploy workflow so `Sync production app secret` updates `tech-news-mystery-prod/app` before Terraform applies ECS task definitions.
3. If fixing manually, run `infra/terraform/scripts/put-app-secret-from-env.ps1` from a trusted local machine with the complete `.env`.

Useful diagnostic command:

```bash
aws ecs describe-services \
  --cluster tech-news-mystery-prod \
  --services api frontend worker beat clustering \
  --region us-west-2 \
  --query 'services[].{service:serviceName,desired:desiredCount,running:runningCount,deployments:deployments[].{status:status,rolloutState:rolloutState,failed:failedTasks,taskDef:taskDefinition},events:events[0:5].message}'
```
