# Voice Agent System Flow - Design Documentation

**Purpose:** Complete architectural flow for Tech News Mystery voice agent system. This document is designed for designers and visual architects to create diagrams and understand data flows.

---

## 1. System Overview

The voice agent system allows users to have spoken conversations with an AI assistant. The system handles:
- Speech capture from user's microphone
- Converting speech to text (STT)
- Processing user query through an intelligent agent
- Converting agent response back to speech (TTS)
- Managing interruptions when user talks over the agent

**Key Principle:** Low-latency, natural conversation flow optimized for voice interaction.

---

## 2. System Components

### 2.1 Frontend Components (Browser)

| Component | Technology | Responsibility |
|-----------|----------|-----------------|
| **Microphone Manager** | WebAudio API (ScriptProcessorNode) | Capture raw audio from user's mic |
| **Audio Processor** | JavaScript | Downsample audio to 16kHz, convert to 16-bit PCM mono |
| **STT Manager** | ElevenLabs WebSocket Client | Connect to STT service, send audio, receive transcripts |
| **Voice UI Controller** | React | Manage voice button states (Start, Speaking, Interrupt, End) |
| **Talk-over Detector** | WebAudio Analyser | Detect if user is speaking while TTS is playing |
| **Audio Playback** | HTMLAudioElement | Play TTS response audio |
| **LiveKit Client** | livekit-client SDK | Manage room connection and microphone publishing |

### 2.2 Backend Components (FastAPI/Python)

| Component | Technology | Responsibility |
|-----------|----------|-----------------|
| **Voice Endpoints** | FastAPI Routes | HTTP API for voice operations |
| **STT Token Generator** | ElevenLabs API | Mint single-use tokens for STT WebSocket |
| **Voice Message Processor** | Python Async | Receive transcript, call agent, save messages |
| **TTS Proxy** | FastAPI StreamingResponse | Forward text to ElevenLabs, stream audio back |
| **Event Recorder** | LangSmith Client | Record voice telemetry events |
| **Session Manager** | DynamoDB | Store voice sessions and messages |
| **AgentCore Client** | boto3 + bedrock-agentcore | Invoke agent runtime |

### 2.3 External Services

| Service | Purpose | Protocol | Notes |
|---------|---------|----------|-------|
| **ElevenLabs STT** | Speech-to-text | WebSocket (browser direct) | Model: scribe_v2_realtime |
| **ElevenLabs TTS** | Text-to-speech | HTTP Streaming (backend proxy) | Model: eleven_flash_v2_5 |
| **AWS Bedrock AgentCore** | Managed LLM agent service | boto3 (backend only) | Orchestrates LangGraph agent |
| **LangGraph** | Agent orchestration framework | In-process (AgentCore) | ReAct agent loop |
| **Claude LLM** | Language model | Bedrock API (AgentCore) | Temperature: 0.25 |
| **Qdrant** | Vector database | In-process tool | Semantic search over articles |
| **Playwright/CDP** | Web browser automation | In-process tool | Browse web for real-time info |
| **LiveKit** | Realtime communication | WebSocket + HTTPS (browser) | Room management & tokens |
| **LangSmith** | Observability platform | HTTPS (backend) | Trace events and metrics |
| **DynamoDB** | Session storage | boto3 (backend) | Stores messages and sessions |

---

## 3. Complete Data Flow - Phase by Phase

### Phase 1: User Speaks & Audio Capture
**Duration:** Variable (user speaking duration)

```
USER speaks into microphone
         ↓
Browser WebAudio API (ScriptProcessorNode)
   • Capture PCM audio at native browser sample rate
   • Echo cancellation enabled
   • Noise suppression enabled
   • Auto gain control enabled
         ↓
Audio Processor
   • Downsample to 16kHz (standard for speech)
   • Convert to 16-bit PCM
   • Convert to mono (single channel)
   • Encode to Base64
         ↓
Store in browser memory buffer
(Audio is NOT sent yet - waiting for STT connection)
```

**Key Parameters:**
- Audio format: PCM 16-bit mono
- Sample rate: 16kHz
- Encoding: Base64

---

### Phase 2: STT (Speech-to-Text) Connection & Transmission
**Duration:** User speaking + 1.2s silence detection

```
Before STT starts:
   Frontend calls: POST /v1/chat/voice/stt-token
         ↓
   Backend receives request from authenticated user
         ↓
   Backend calls ElevenLabs API to mint single-use token
         ↓
   Returns token to frontend
   (Token expires after one STT session)

STT Connection Establishment:
   Frontend opens WebSocket to ElevenLabs Realtime Scribe
   Endpoint: wss://api.elevenlabs.io/v1/speech-to-text/realtime
   Query Parameters:
      • commit_strategy=vad (use voice activity detection)
      • vad_silence_threshold_secs=1.2 (silence window)
      • vad_threshold=0.4 (voice sensitivity)
      • min_speech_duration_ms=100 (ignore micro-bursts)
      • no_verbatim=true (clean transcription)
         ↓
   Send Authorization header with single-use token

Audio Streaming:
   Frontend sends buffered PCM audio chunks via WebSocket
         ↓
   ElevenLabs Scribe processes each chunk
         ↓
   Emits real-time events:
      • partial_transcript: "The tech news..." (user can see live)
      • partial_transcript: "The tech news today is..." (updates)

VAD Detection (1.2 seconds of silence):
   User stops speaking
         ↓
   ElevenLabs detects 1.2 seconds of silence
         ↓
   Emits committed_transcript: "The tech news today is interesting"
         ↓
   Frontend receives committed_transcript event
         ↓
   Frontend closes STT WebSocket
         ↓
   Frontend records telemetry: stt_committed
```

**Data Emitted:**
```
{
  "transcript": "The tech news today is interesting",
  "confidence": 0.95,
  "timestamps": {...}
}
```

---

### Phase 3: Backend Voice Processing
**Duration:** 1-90 seconds (agent processing timeout: 90s max)

```
Frontend has: committed_transcript = "The tech news today is interesting"
         ↓
Frontend sends HTTP POST to Backend:
   Endpoint: POST /v1/chat/voice/message
   Payload:
   {
     "session_id": "voice-session-123",
     "content": "The tech news today is interesting"
   }
         ↓
Backend FastAPI endpoint receives request:
   Step 1: Validate user is authenticated
   Step 2: Validate session belongs to user
   Step 3: Load last 6 messages from DynamoDB
         ↓
   recent_messages = [
     {role: "user", content: "...", timestamp: "..."},
     {role: "assistant", content: "...", timestamp: "..."},
     ...
   ]
         ↓
   Step 4: Initialize RequestAgentMemory
           (AWS Bedrock AgentCore Memory)
         ↓
   Step 5: Save user message to DynamoDB
           {
             session_id: "voice-session-123",
             role: "user",
             content: "The tech news today is interesting",
             timestamp: "2026-06-03T10:30:00Z"
           }
         ↓
   Step 6: Log message to RequestAgentMemory
```

---

### Phase 4: LLM Agent Processing (AWS Bedrock AgentCore)
**Duration:** 5-60 seconds (typical)

```
Backend calls AWS Bedrock AgentCore:
   Service: aws_bedrockagentcore_agent_runtime
   Method: invoke_agent_runtime()
   
   Input:
   {
     "session_id": "voice-session-123",
     "user_message": "The tech news today is interesting",
     "context": {
       "recent_events": [last 6 messages],
       "request_scope": "voice",
       "agent_mode": "voice",
       "response_style": "one_spoken_paragraph",
       "latency_priority": "high"
     }
   }
         ↓
AgentCore → LangGraph ReAct Agent Execution:

   Component: LangGraph ReAct Agent
   Framework: langgraph.prebuilt.create_react_agent
   
   LLM Configuration:
   • Model: ChatBedrockConverse (AWS Bedrock Claude)
   • Temperature: 0.25 (low variance, focused)
   • Max tokens: 420 (short response for voice)
   • Streaming: Disabled (returns full text at end)
   
   System Prompt (Voice-Optimized):
   ┌─────────────────────────────────────────────┐
   │ You are the Tech News Mystery voice agent.  │
   │                                             │
   │ Answer in ONE natural spoken paragraph.     │
   │ • Direct answer first                       │
   │ • No markdown, bullets, emojis              │
   │ • Compact spoken citations                  │
   │   e.g., "according to The Verge"           │
   │ • No tool explanations                      │
   │ • No Code Interpreter mentions              │
   │                                             │
   │ For news/trends/people/events:              │
   │  1. Call semantic_search first              │
   │  2. If <2 results, call browse_web          │
   │                                             │
   │ For specific URLs: browse_web directly      │
   └─────────────────────────────────────────────┘
         ↓
Agent Processing Loop:

   1. REASONING PHASE
      LLM reads user query + context
      LLM decides: What tools do I need?
      Decision tree:
         • Is this about tech news? → semantic_search
         • Is this about a specific URL? → browse_web
         • Is this a calculation? → reason directly
         ↓
   2. TOOL SELECTION PHASE
      LLM chooses tool(s) to call
      
      Available Tools:
      a) semantic_search
         • Query: Qdrant vector database
         • Database: All tech news articles
         • Returns: Top 3 most relevant articles
      
      b) browse_web
         • Tool: Playwright Browser (Chrome CDP)
         • Capability: Visit URL, extract text
         • Fallback: DuckDuckGo HTML search
         • Returns: Cleaned webpage text
      ↓
   3. TOOL EXECUTION PHASE
      Backend executes selected tools
      
      Example:
         Tool Call: semantic_search("latest AI news")
         ↓
         Qdrant Query Engine
         ↓
         Returns: [article1, article2, article3]
         ↓
         Tool Result: {
           "articles": [
             {
               "title": "OpenAI releases GPT-5",
               "source": "The Verge",
               "url": "...",
               "summary": "..."
             },
             ...
           ]
         }
      ↓
   4. REASONING PHASE (Continued)
      LLM sees tool results
      LLM generates final answer
      
      Example Answer:
      "OpenAI just released GPT-5 according to The Verge,
       which shows significant improvements in reasoning and
       long-context understanding compared to GPT-4."
         ↓
   5. RESPONSE GENERATION
      LLM outputs final text
      Text is collected (token by token)
      
      Output:
      "OpenAI just released GPT-5 according to The Verge..."
```

**AgentCore Response Events:**
```json
[
  {"type": "token", "content": "Open"},
  {"type": "token", "content": "AI"},
  {"type": "token", "content": " just"},
  ...
  {"type": "tool_invocation", "tool_name": "semantic_search", "tool_id": "abc123", "tool_args": {"query": "latest AI news"}},
  {"type": "tool_result", "tool_name": "semantic_search", "status": "completed", "result_summary": "Found 3 articles about AI news"},
  ...
  {"type": "done"}
]
```

---

### Phase 5: Backend Processes Agent Response
**Duration:** < 1 second

```
Backend collects all token events:
   "OpenAI just released GPT-5 according to The Verge..."
         ↓
Backend validates response:
   • Check response is not empty
   • Check response is under max length
   • Check latency is acceptable
         ↓
Backend saves response to DynamoDB:
   {
     session_id: "voice-session-123",
     role: "assistant",
     content: "OpenAI just released GPT-5 according to The Verge...",
     timestamp: "2026-06-03T10:30:15Z",
     latency_ms: 12500,
     input_chars: 45,
     output_chars: 120
   }
         ↓
Backend logs to RequestAgentMemory
         ↓
Backend sends response to frontend:
   HTTP 200 OK
   {
     "success": true,
     "data": {
       "content": "OpenAI just released GPT-5...",
       "latency_ms": 12500,
       "input_chars": 45,
       "output_chars": 120
     }
   }
         ↓
Backend records telemetry in LangSmith:
   Event: voice.agent_turn.completed
   Metadata:
   {
     "phase": "agent_turn_completed",
     "provider": "agentcore",
     "transport": "livekit",
     "output_chars": 120,
     "latency_ms": 12500,
     "agent_mode": "voice",
     "streaming_disabled_for_latency": true
   }
```

---

### Phase 6: Text-to-Speech (TTS)
**Duration:** 2-10 seconds (depends on text length)

```
Frontend receives agent response:
   content = "OpenAI just released GPT-5 according to The Verge..."
         ↓
Frontend sends to Backend:
   Endpoint: POST /v1/chat/voice/speech
   Payload:
   {
     "text": "OpenAI just released GPT-5 according to The Verge...",
     "voice_id": "pNInz6obpgDQGcFmaJgB"
   }
         ↓
Backend TTS Processor:
   Step 1: Clean text
           • Strip markdown (**, ##, [], etc.)
           • Remove code blocks
           • Remove emojis
   
   Step 2: Validate text length
           • Cap at 1200 characters
           • Truncate if needed
   
   Step 3: Forward to ElevenLabs
           • Endpoint: https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream
           • Model: eleven_flash_v2_5 (low-latency)
           • Output format: mp3_44100_128
           ↓
ElevenLabs TTS Engine:
   Receives: "OpenAI just released GPT-5..."
         ↓
   Synthesizes speech:
   • Analyzes text structure
   • Generates audio stream
   • Returns MP3 audio chunks
         ↓
Backend Proxy:
   Receives MP3 stream from ElevenLabs
         ↓
   Forwards to Frontend:
   HTTP 200
   Content-Type: audio/mpeg
   Transfer-Encoding: chunked
   [Audio stream bytes...]
         ↓
Frontend receives audio stream:
   • Accumulates bytes into Blob
   • Creates object URL: blob:http://localhost/abc123
   • Sets HTMLAudioElement.src = object URL
   • Calls audio.play()
         ↓
Browser Audio Output:
   Audio plays through user's speakers
         ↓
Frontend records telemetry:
   Events: tts_playback_started → tts_playback_ended
```

---

### Phase 7: Active Listening (After TTS)
**Duration:** Until next user input

```
After TTS playback ends:
         ↓
Frontend automatically re-arms:
   UI returns to: "Start voice" / "Speak now" button
         ↓
Frontend opens new STT WebSocket connection
   (Waits for next user input)
         ↓
Ready for next turn of conversation
```

---

### Phase 8: Interruption Handling (Barge-in)
**Duration:** Real-time detection

```
While TTS is playing:
         ↓
Parallel Monitoring:

   A. MANUAL INTERRUPT
      User clicks: [Interrupt] button
         ↓
      Frontend calls: stopPlayback()
         ↓
      stopPlayback() Action:
      • Abort active TTS HTTP request
      • Stop HTMLAudioElement playback
      • Clear audio buffer
         ↓
      Frontend records telemetry: voice_interrupted
         ↓
      Frontend restarts STT WebSocket
         ↓
   B. AUTOMATIC TALK-OVER DETECTION
      Browser runs lightweight energy monitor
         ↓
      Monitor listens to microphone in parallel
         ↓
      Detection Algorithm:
      • Measure audio energy level
      • Ignore first 300ms (grace period)
      • Wait for sustained high energy (3+ consecutive frames)
      • Threshold: 0.6 (normalized RMS energy)
         ↓
      If Talk-over Detected:
      • Call stopPlayback() (same as manual)
      • Record telemetry: voice_interrupted
      • Restart STT WebSocket
      • Show: "Interrupt - Starting over"

Echo Prevention:
   • Browser mic has echoCancellation enabled
   • Before starting new STT turn, stop current TTS
   • Talk-over monitor has grace period (not ultra-sensitive)
   • Prevents feedback loop
```

---

## 4. Communication Channels (Current Implementation)

```
┌─ Browser ─────────────────────┐
│                               │
│  WebSocket (LiveKit)          │
│  └─ Room/Token Management     │
│  └─ Microphone Publishing     │
│     (Audio NOT sent via here) │
│                               │
│  WebSocket (ElevenLabs STT)   │
│  └─ DIRECT STT               │
│  └─ PCM audio chunks          │
│  └─ Committed transcripts     │
│                               │
│  HTTP POST /v1/chat/voice/... │
│  └─ stt-token request         │
│  └─ voice/message (transcript)│
│  └─ voice/speech (text)       │
│  └─ voice/events (telemetry)  │
│                               │
└───────────┬────────────────────┘
            │
            ├─→ Backend (FastAPI)
            │   └─→ AWS Bedrock AgentCore
            │       └─→ LangGraph Agent
            │
            ├─→ ElevenLabs STT (WebSocket - DIRECT)
            ├─→ ElevenLabs TTS (HTTP - via Backend Proxy)
            ├─→ LiveKit (WebSocket - Session/Tokens)
            └─→ LangSmith (HTTP - Telemetry)
```

**Key Note:** 
- **STT:** Direct browser-to-ElevenLabs WebSocket (NOT through backend)
- **TTS:** Browser requests → Backend proxies → ElevenLabs
- **LiveKit:** Session management only (NOT audio)

---

## 5. Data Models

### 5.1 Voice Session
```
VoiceSession {
  session_id: string (UUID)
  user_id: string
  title: "Voice agent session"
  description: "Dedicated voice-agent testing session"
  created_at: timestamp
  updated_at: timestamp
  messages: [Message, ...]
}
```

### 5.2 Voice Message
```
Message {
  message_id: string (UUID)
  session_id: string
  user_id: string
  role: "user" | "assistant"
  content: string
  timestamp: timestamp
  metadata: {
    latency_ms: number (assistant only)
    input_chars: number
    output_chars: number
  }
}
```

### 5.3 Voice Event (Telemetry)
```
VoiceEvent {
  event_name: string (e.g., "stt_committed", "tts_playback_started")
  user_id: string
  session_id: string
  timestamp: timestamp
  data: {
    phase: string
    latency_ms: number
    character_count: number
    ...
  }
}
```

---

## 6. Timeouts & Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| **STT Commitment Latency** | 1.2s silence | VAD auto-detection |
| **Backend Agent Timeout** | 90 seconds max | Hard limit, returns 504 |
| **Time-to-First-Audio (TTFA)** | < 800ms | VAD commit to playback start |
| **Agent Response Latency** | 5-60s typical | Depends on tool complexity |
| **TTS Streaming Start** | 1-3 seconds | Audio buffer filling |
| **User Message Save** | < 100ms | DynamoDB write |

---

## 7. Error Handling & Edge Cases

| Scenario | Current Handling |
|----------|-----------------|
| **No speech detected** | UI shows "No speech detected", no empty message sent |
| **Microphone permission denied** | UI shows browser error message, records `voice_input_failed` |
| **STT WebSocket fails** | Error surfaces in status line, cleanup runs, user can retry |
| **Agent takes too long** | 90 second timeout, returns 504 Gateway Timeout |
| **TTS request fails** | Text answer remains visible, playback status shows failure |
| **LiveKit disconnects** | Disconnect event logged, STT cleanup runs independently |
| **User talks over agent** | Auto-detect via talk-over monitor or manual interrupt button |
| **Agent returns empty** | Returns error, "Voice agent returned empty response" |

---

## 8. System Limitations & Future Improvements

### Current Limitations:
1. **No LiveKit Agent Worker** - Audio pipeline split between browser + backend (not unified server-side)
2. **No Full Mouth-to-Ear Latency Metric** - Only backend agent latency is measured
3. **Browser Playback Buffering** - TTS streams to browser but playback waits for full blob
4. **Energy-Based Barge-in** - Talk-over detection uses audio energy (can have false positives)
5. **Code Interpreter Parked** - Not currently available in agent

### Future Upgrades:
1. **LiveKit Agent Worker** - Server-side STT + LLM + TTS + turn detection
2. **Continuous VAD** - Keep turn detection active, improve barge-in
3. **Streaming Playback** - Start audio playback while TTS is still streaming
4. **Model-Based Barge-in** - Replace energy detection with proper VAD
5. **Code Interpreter** - Re-enable with proper safeguards
6. **Multi-turn Memory** - Longer conversation context (currently 6 messages)

---

## 9. Glossary for Designers

| Term | Meaning |
|------|---------|
| **VAD** | Voice Activity Detection - automatically detects when user stops speaking |
| **STT** | Speech-to-Text - converts audio to text |
| **TTS** | Text-to-Speech - converts text to audio |
| **Barge-in** | User interrupts agent while it's speaking |
| **Latency** | Time delay between steps |
| **PCM** | Pulse Code Modulation - uncompressed audio format |
| **WebSocket** | Bidirectional persistent connection (vs HTTP request/response) |
| **Streaming Response** | Data sent in chunks (not all at once) |
| **LangGraph** | Framework for building agent logic flows |
| **ReAct Agent** | Agent that Reasons + Acts (decides tools, calls them, reasons about results) |
| **Qdrant** | Vector database for semantic search |
| **Playwright** | Browser automation tool |
| **AgentCore** | AWS managed service for running agents |
| **LangSmith** | Observability/tracing platform |
| **Echo Cancellation** | Technology to remove mic picking up speaker audio |

---

## 10. Ready-for-Design Diagrams Needed

Based on this flow, designer should create:

1. **System Architecture Diagram**
   - All components (Frontend, Backend, External Services)
   - Communication channels
   - Data flow directions

2. **User Journey Flow**
   - Main happy path (speak → hear response)
   - Decision points (tool selection, voice detection)
   - Branches (manual interrupt vs auto-detect)

3. **Timeline Diagram**
   - Phases and their duration
   - Parallel operations (TTS while listening for barge-in)
   - Latency checkpoints

4. **Data Model Diagram**
   - VoiceSession, Message, Event entities
   - Relationships
   - Storage location (DynamoDB vs in-memory)

5. **Channel/Transport Diagram**
   - Which channels do what
   - Direct vs proxied connections
   - Protocol types (WebSocket vs HTTP)

6. **Agent Decision Tree**
   - Tool selection logic
   - Reasoning flow
   - Example decision paths

---

**End of Design Documentation**

Document version: 1.0  
Last updated: 2026-06-03  
Created for: Designer visualization and diagram creation
