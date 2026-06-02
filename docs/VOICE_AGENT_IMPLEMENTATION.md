# Voice Agent Implementation Notes

## Current Pipeline

The app now uses this voice path:

```text
Browser mic
  -> LiveKit room connection and microphone publish
  -> ElevenLabs Realtime Scribe STT over WebSocket
  -> existing chat SSE / LLM agent / tools
  -> ElevenLabs streaming TTS
  -> browser audio playback
  -> LangSmith voice telemetry events
```

LiveKit is used as the realtime room/session transport and microphone publication layer. ElevenLabs is used for both STT and TTS. The core LLM agent remains the existing chat streaming path, so search/tools/history behavior is preserved.

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

Use `infra/terraform/scripts/put-app-secret-from-env.ps1` to sync local `.env`
values into the app secret without committing raw credentials. The helper strips
surrounding single or double quotes from `.env` values before uploading them.

The GitHub Actions deploy workflow also syncs these values from GitHub Actions
secrets before Terraform applies new ECS task definitions. This matters because
ECS resolves JSON keys from Secrets Manager while placing a task; if a new key is
missing, the task never starts and the deploy waiter eventually fails.

Required GitHub Actions secrets for the voice feature:

| Secret | Purpose |
| --- | --- |
| `LANGSMITH_API_KEY` | LangSmith trace ingestion |
| `ELEVENLABS_API_KEY` | ElevenLabs STT/TTS API access |
| `ELEVENLABS_VOICE_ID` | ElevenLabs TTS voice |
| `LIVEKIT_API_KEY` | LiveKit token signing public key |
| `LIVEKIT_API_SECRET` | LiveKit token signing secret |

Related existing app secrets such as `SECRET_KEY`, `JWT_SECRET_KEY`,
`OPENAI_API_KEY`, `QDRANT_URL`, and `QDRANT_API_KEY` must also be present either
in GitHub Actions secrets or already in the app Secrets Manager JSON payload.

## LiveKit Capabilities Used

* Tokenized room access with short-lived JWTs from `/v1/chat/voice/livekit-session`.
* Browser room connection via `livekit-client`.
* Local microphone publishing with echo-cancellation-capable browser capture.
* Connection lifecycle events such as disconnect and connection quality changes.
* Room metadata ties each voice session to the chat session, agent name, ElevenLabs model IDs, and LangSmith project.

## Critical Voice Metrics

The implementation records these phases through `/v1/chat/voice/events` for LangSmith tracing:

* `livekit_room_ready`
* `livekit_connection_quality`
* `stt_committed`
* `tts_playback_started`
* `tts_playback_failed`
* `voice_input_failed`

The chat UI also shows compact message metrics on hover:

* Estimated input/output token split.
* Estimated cost.
* Total response latency.
* Time to first token.
* Tool call count.

Cost is marked as estimated because the runtime can use multiple provider/model paths.

## Voice Controls

* The main mic button starts voice mode when off.
* While voice is enabled, the main mic button starts listening, pauses listening, or interrupts current TTS playback and begins a new turn.
* The `End voice` control fully turns voice mode off, closes STT, stops playback, and disconnects LiveKit.
* After a TTS response finishes, voice mode automatically re-arms listening for the next conversational turn.

## Edge Cases and Handling

### Barge-in / User Interrupts Agent Speech

Risk: the user starts a new query while TTS is still playing.

Current handling:

* Pressing the mic while voice mode is enabled stops current playback and starts a fresh STT turn.
* `stopPlayback()` aborts the active TTS request/audio element before starting STT.

Future improvement:

* A production LiveKit Agent worker can keep turn detection active continuously and perform automatic barge-in without requiring a click.

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

* Existing chat SSE stream keeps visual output moving.
* Message metrics display TTFT and total latency.
* Backend stream timeout and error handling remain active.

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

Meaning: Terraform registered new task definitions that reference the voice-agent
secret keys, but the production app secret did not yet contain those JSON keys.
The old tasks stayed running, while the new `api`, `worker`, `beat`, and
`clustering` deployments remained in progress with failed task placements.

Fix path:

1. Add the required voice secrets to GitHub Actions secrets.
2. Re-run the deploy workflow so `Sync production app secret` updates
   `tech-news-mystery-prod/app` before Terraform applies ECS task definitions.
3. If fixing manually, run `infra/terraform/scripts/put-app-secret-from-env.ps1`
   from a trusted local machine with the complete `.env`.

Useful diagnostic command:

```bash
aws ecs describe-services \
  --cluster tech-news-mystery-prod \
  --services api frontend worker beat clustering \
  --region us-west-2 \
  --query 'services[].{service:serviceName,desired:desiredCount,running:runningCount,deployments:deployments[].{status:status,rolloutState:rolloutState,failed:failedTasks,taskDef:taskDefinition},events:events[0:5].message}'
```
