# LiveKit SIP Voice Transport

This worker is the phone-call transport for the existing Tech News Mystery voice agent. It is not a separate agent brain.

Browser voice remains:

```text
frontend useVoiceAgent
  -> /v1/chat/voice/*
  -> Agent Core voice graph
```

Dialable phone voice adds only this transport adapter:

```text
phone caller
  -> LiveKit SIP room
  -> app.workers.livekit_voice_agent
  -> /v1/chat/voice/sip/message
  -> the same Agent Core voice graph
```

## Run Locally

Run from the `backend/` folder so `backend/.env` is loaded:

Install/update the normal backend dependencies first if needed:

```powershell
pip install -r backend/requirements.txt
```

Then install only the LiveKit worker extras:

```powershell
pip install -r backend/requirements-livekit.txt -c backend/constraints.txt
```

`backend/requirements-livekit.txt` is intentionally separate from `backend/requirements.txt`. The base backend dependency set is large and historically difficult for pip to resolve with the LiveKit plugins in one pass. CI and the backend Docker image install both files, using `backend/constraints.txt` for the LiveKit extras.

Run the worker:

```powershell
cd backend
python -m app.workers.livekit_voice_agent dev
```

Run with Docker Compose:

```powershell
docker compose -f infra/docker-compose.yml up api livekit-voice-worker
```

Inside compose, `VOICE_BACKEND_BASE_URL` is `http://api:8000/v1` because `localhost` would point at the worker container itself.

Console test:

```powershell
cd backend
python -m app.workers.livekit_voice_agent console
```

## Production Deployment

The backend Docker image installs both dependency files:

```text
backend/requirements.txt
backend/requirements-livekit.txt -c backend/constraints.txt
```

Terraform creates a dedicated ECS service named `livekit-voice-worker` from the same backend image. Its command is:

```text
python -m app.workers.livekit_voice_agent start
```

Required production secret keys in the app Secrets Manager JSON:

```text
LIVEKIT_API_KEY
LIVEKIT_API_SECRET
ELEVENLABS_API_KEY
ELEVENLABS_VOICE_ID
VOICE_WORKER_SERVICE_TOKEN
```

GitHub Actions syncs those keys from repository secrets and waits for `livekit-voice-worker` with the other ECS services.

## LiveKit CLI On Windows

If PowerShell says `lk` is not recognized, install the official LiveKit CLI:

```powershell
winget install LiveKit.LiveKitCLI
```

Then open a new PowerShell window and run:

```powershell
lk cloud auth
```

LiveKit CLI setup reference: https://docs.livekit.io/reference/developer-tools/livekit-cli/

Required values live in `backend/.env`:

```text
LIVEKIT_URL=...
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
LIVEKIT_AGENT_NAME=tech-news-voice-agent
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=...
ELEVENLABS_TTS_MODEL_ID=eleven_flash_v2_5
VOICE_WORKER_SERVICE_TOKEN=...
VOICE_BACKEND_BASE_URL=http://localhost:8000/v1
```

The worker explicitly loads both the repo root `.env` and `backend/.env` before starting LiveKit, because LiveKit's worker CLI reads `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET` from process environment variables.

The same `VOICE_WORKER_SERVICE_TOKEN` must be configured in the backend API process, because the worker calls `POST /v1/chat/voice/sip/message`.

## Turn Detector Model

If startup logs show:

```text
Could not find file "model_q8.onnx"
Use `python -m livekit.agents download-files` to download the model.
```

Stop the worker and run this once from the activated backend venv:

```powershell
cd backend
python -m livekit.agents download-files
python -m app.workers.livekit_voice_agent dev
```

If the model download is blocked and you only want a quick phone smoke test, temporarily set:

```text
LIVEKIT_TURN_DETECTOR_ENABLED=false
```

That keeps Silero VAD and interruption handling active, but disables semantic turn detection until the model is downloaded.

## Real Phone Call Diagnostics

Current LiveKit Phone Number wiring:

```text
Phone number: +14842707189
Phone number ID: PN_PPN_cVdPArHxVVGu
Dispatch rule ID: SDR_r43xk6pwMwz6
Dispatch agent: tech-news-voice-agent
```

Verify the number is assigned to the dispatch rule:

```powershell
lk number list
lk sip dispatch list
```

Expected:

```text
+14842707189 -> SIP Dispatch Rules: SDR_r43xk6pwMwz6
SDR_r43xk6pwMwz6 -> SipTrunks: PN_PPN_cVdPArHxVVGu
SDR_r43xk6pwMwz6 -> Agents: tech-news-voice-agent
```

Then place a real inbound test call. Immediately after the call attempt, check whether LiveKit created a room:

```powershell
lk room list
```

Interpretation:

- No `call-...` room appears: the call did not reach LiveKit dispatch. Open LiveKit Cloud -> Telephony -> Calls and inspect the failed call record. The key question is whether an inbound SIP `INVITE` was recorded. If no INVITE appears, the problem is upstream of LiveKit or the LiveKit Phone Number provisioning/routing layer.
- A `call-...` room appears but the agent does not answer: inspect the worker logs and confirm it says `registered worker` with `agent_name` equal to `tech-news-voice-agent`.
- A room appears with a SIP participant but no agent participant: the dispatch rule matched, but the agent was unavailable or registered under a different name.
- The call connects but audio is missing: inspect the LiveKit Cloud Session and Telephony Call details for SIP status, media, and participant track events.
- Worker logs show `RuntimeError: trying to generate reply without an LLM model`: do not use `session.generate_reply(...)` unless the `AgentSession` has a LiveKit-managed LLM configured. This worker uses the existing backend voice agent as the brain, so transport-owned greetings must use `session.say(...)`, and substantive caller turns go through `/v1/chat/voice/sip/message`.
- Worker logs show `AttributeError: 'JobContext' object has no attribute 'wait_for_disconnect'`: LiveKit Agents `1.5.x` does not expose that helper on `JobContext`. Keep the job alive by waiting on `ctx.room.on("disconnected")` instead.
- Worker logs show `RuntimeError: inference of lk_end_of_utterance_multilingual failed: no inference executor`: the local `dev` worker does not have LiveKit's turn-detector inference executor available. Set `LIVEKIT_TURN_DETECTOR_ENABLED=false` for local testing. Silero VAD and interruption handling remain active. Re-enable the multilingual turn detector only when running in a deployment with a LiveKit inference executor or remote inference URL.
- Worker logs show `interruption_detection is provided, but it's not compatible`: adaptive interruption requires compatible semantic turn detection. For local testing with `LIVEKIT_TURN_DETECTOR_ENABLED=false`, the worker uses VAD interruption mode instead.
- Worker logs show `engine is closed` while publishing transcription or binary stream messages: this can happen while the SIP room is closing. The phone worker disables room transcription publishing and IVR detection for inbound human calls to avoid noisy post-disconnect stream writes.
- Worker logs show `received user transcript` but no backend call: final phone transcripts must be bridged explicitly with `session.on("user_input_transcribed", ...)`. This worker does not rely on LiveKit's automatic LLM pipeline because the backend API is the agent brain.
- Barge-in test: if the caller interrupts while the agent is speaking, the worker listens to `user_state_changed` and force-interrupts current playback immediately. When the final transcript arrives, it cancels any superseded backend/speech task and speaks only the newest answer. Expected logs include `Cancelling active phone response because caller started speaking` or `Cancelling active phone response before turn ...`.

For LiveKit Phone Numbers, LiveKit's docs say inbound calls only require a phone number and a dispatch rule; there is no third-party SIP provider dashboard to inspect. Failed-connect call diagnostics live in LiveKit Cloud Telephony -> Calls.

### International Caller Checks

LiveKit Phone Numbers currently provides US local/toll-free phone numbers. If a caller in Vietnam hears an operator message like "the number does not exist" and `lk room list` stays empty, verify the PSTN path before debugging the backend:

1. Dial the US number in E.164 format: `+14842707189`.
2. If the phone does not accept `+`, dial with Vietnam's international prefix: `00 1 484 270 7189`.
3. Confirm the same Vietnamese SIM can call another known US phone number. Some mobile plans require international direct dialing to be enabled.
4. Test the LiveKit number from a US-based caller or US VoIP service. If a US call reaches LiveKit but Vietnam does not, this is an international carrier routing/reachability issue, not an agent issue.
5. In LiveKit Cloud -> Telephony -> Calls, check whether the Vietnam call creates any call record. No record means no SIP `INVITE` reached LiveKit.

If international reachability is required and LiveKit's first-party US number is not reachable from the target country/carrier, use a third-party SIP provider with proven Vietnam-to-US inbound routing, then connect that provider to LiveKit with an inbound SIP trunk and dispatch rule.

If a Vietnam caller appears in logs as `sip_+84...`, the call reached LiveKit successfully. At that point, debug the worker or backend logs instead of the carrier route.

References:

- https://docs.livekit.io/telephony/testing/
- https://docs.livekit.io/reference/telephony/troubleshooting/
- https://docs.livekit.io/telephony/start/phone-numbers/
- https://livekit.com/products/livekit-phone-numbers
