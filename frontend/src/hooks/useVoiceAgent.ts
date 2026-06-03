'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  createVoiceLiveKitSession,
  createVoiceSttToken,
  recordVoiceEvent,
  synthesizeVoiceSpeech,
} from '@/lib/api/chat';
import type { Room as LiveKitRoom } from 'livekit-client';

const STT_SAMPLE_RATE = 16000;
const ELEVENLABS_STT_WS_URL = 'wss://api.elevenlabs.io/v1/speech-to-text/realtime';
const BARGE_IN_GRACE_MS = 700;
const BARGE_IN_RMS_THRESHOLD = 0.06;
const BARGE_IN_HOT_FRAMES = 5;

type ElevenLabsRealtimeEvent = {
  message_type?: string;
  text?: string;
  error?: string;
  message?: string;
};

type AudioPipeline = {
  context: AudioContext;
  source: MediaStreamAudioSourceNode;
  processor: ScriptProcessorNode;
  stream: MediaStream;
};

type BargeInMonitor = {
  context: AudioContext;
  source: MediaStreamAudioSourceNode;
  analyser: AnalyserNode;
  stream: MediaStream;
  frameId: number;
};

type LiveKitVoiceSession = {
  room: string;
  serverUrl: string;
  participantToken: string;
  traceId?: string | null;
};

function stripForSpeech(text: string): string {
  return text
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`([^`]*)`/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/[*_#>-]{1,3}/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 1200);
}

function downsampleTo16k(input: Float32Array, inputSampleRate: number): Int16Array {
  if (inputSampleRate === STT_SAMPLE_RATE) {
    return floatTo16BitPcm(input);
  }

  const ratio = inputSampleRate / STT_SAMPLE_RATE;
  const outputLength = Math.floor(input.length / ratio);
  const output = new Float32Array(outputLength);

  for (let i = 0; i < outputLength; i += 1) {
    const start = Math.floor(i * ratio);
    const end = Math.min(Math.floor((i + 1) * ratio), input.length);
    let sum = 0;
    for (let j = start; j < end; j += 1) {
      sum += input[j];
    }
    output[i] = sum / Math.max(1, end - start);
  }

  return floatTo16BitPcm(output);
}

function floatTo16BitPcm(input: Float32Array): Int16Array {
  const output = new Int16Array(input.length);
  for (let i = 0; i < input.length; i += 1) {
    const sample = Math.max(-1, Math.min(1, input[i]));
    output[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
  }
  return output;
}

function pcmToBase64(pcm: Int16Array): string {
  const bytes = new Uint8Array(pcm.buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i += 1) {
    binary += String.fromCharCode(bytes[i]);
  }
  return window.btoa(binary);
}

export function useVoiceAgent(
  onTranscript: (text: string) => void,
  sessionId: string,
  options: {
    onPlaybackStarted?: (meta: { outputChars: number; latencyMs?: number }) => void;
    onPlaybackEnded?: (meta: { outputChars: number; latencyMs?: number }) => void;
    onInterrupted?: (meta: { latencyMs?: number }) => void;
  } = {}
) {
  const [enabled, setEnabled] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const pipelineRef = useRef<AudioPipeline | null>(null);
  const bargeInMonitorRef = useRef<BargeInMonitor | null>(null);
  const livekitRoomRef = useRef<LiveKitRoom | null>(null);
  const livekitSessionRef = useRef<LiveKitVoiceSession | null>(null);
  const turnStartedAtRef = useRef<number | null>(null);
  const finalTranscriptRef = useRef('');
  const submittedTranscriptRef = useRef(false);
  const enabledRef = useRef(false);
  const startListeningRef = useRef<(() => Promise<void>) | null>(null);

  const isSupported = useMemo(() => {
    if (typeof window === 'undefined') return false;
    return (
      typeof navigator.mediaDevices?.getUserMedia === 'function' &&
      typeof window.AudioContext === 'function' &&
      typeof window.WebSocket === 'function'
    );
  }, []);

  const cleanupBargeInMonitor = useCallback(() => {
    const monitor = bargeInMonitorRef.current;
    if (!monitor) return;

    window.cancelAnimationFrame(monitor.frameId);
    monitor.source.disconnect();
    monitor.stream.getTracks().forEach((track) => track.stop());
    void monitor.context.close();
    bargeInMonitorRef.current = null;
  }, []);

  const stopPlayback = useCallback(() => {
    cleanupBargeInMonitor();
    abortRef.current?.abort();
    abortRef.current = null;
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = '';
      audioRef.current = null;
    }
    setIsSpeaking(false);
  }, [cleanupBargeInMonitor]);

  const cleanupAudioPipeline = useCallback(() => {
    const pipeline = pipelineRef.current;
    if (!pipeline) return;

    pipeline.processor.disconnect();
    pipeline.source.disconnect();
    pipeline.stream.getTracks().forEach((track) => track.stop());
    void pipeline.context.close();
    pipelineRef.current = null;
  }, []);

  const disconnectLiveKit = useCallback(() => {
    const room = livekitRoomRef.current;
    if (!room) return;
    room.localParticipant.setMicrophoneEnabled(false).catch(() => undefined);
    room.disconnect();
    livekitRoomRef.current = null;
  }, []);

  const stopListening = useCallback(() => {
    socketRef.current?.close();
    socketRef.current = null;
    cleanupAudioPipeline();
    setIsListening(false);
  }, [cleanupAudioPipeline]);

  const startBargeInMonitor = useCallback(async () => {
    if (!isSupported || bargeInMonitorRef.current || !enabledRef.current) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
        },
      });
      const context = new window.AudioContext();
      const source = context.createMediaStreamSource(stream);
      const analyser = context.createAnalyser();
      analyser.fftSize = 1024;
      source.connect(analyser);

      const samples = new Float32Array(analyser.fftSize);
      const startedAt = performance.now();
      let hotFrames = 0;
      let triggered = false;

      const tick = () => {
        const monitor = bargeInMonitorRef.current;
        if (!monitor || triggered) return;

        if (!enabledRef.current || !audioRef.current) {
          cleanupBargeInMonitor();
          return;
        }

        if (performance.now() - startedAt > BARGE_IN_GRACE_MS) {
          analyser.getFloatTimeDomainData(samples);
          let sum = 0;
          for (let index = 0; index < samples.length; index += 1) {
            sum += samples[index] * samples[index];
          }
          const rms = Math.sqrt(sum / samples.length);
          hotFrames = rms >= BARGE_IN_RMS_THRESHOLD ? hotFrames + 1 : Math.max(0, hotFrames - 1);

          if (hotFrames >= BARGE_IN_HOT_FRAMES) {
            triggered = true;
            setStatus('Interrupt detected. Listening...');
            cleanupBargeInMonitor();
            void startListeningRef.current?.();
            return;
          }
        }

        monitor.frameId = window.requestAnimationFrame(tick);
      };

      const frameId = window.requestAnimationFrame(tick);
      bargeInMonitorRef.current = { context, source, analyser, stream, frameId };
    } catch {
      // Manual interrupt still works if the browser cannot open a second mic monitor.
    }
  }, [cleanupBargeInMonitor, isSupported]);

  const shutdownVoice = useCallback(() => {
    enabledRef.current = false;
    socketRef.current?.close();
    socketRef.current = null;
    cleanupAudioPipeline();
    cleanupBargeInMonitor();
    disconnectLiveKit();
    livekitSessionRef.current = null;
    stopPlayback();
    setIsListening(false);
    setStatus(null);
  }, [cleanupAudioPipeline, cleanupBargeInMonitor, disconnectLiveKit, stopPlayback]);

  const submitTranscript = useCallback(() => {
    if (submittedTranscriptRef.current) return;
    const text = finalTranscriptRef.current.trim();
    if (!text) {
      setStatus(enabled ? 'No speech detected' : null);
      return;
    }

    submittedTranscriptRef.current = true;
    setStatus('Sending voice message...');
    void recordVoiceEvent({
      session_id: sessionId,
      phase: 'stt_committed',
      provider: 'elevenlabs',
      transport: 'livekit',
      livekit_room: livekitSessionRef.current?.room ?? null,
      transcript_chars: text.length,
      latency_ms: turnStartedAtRef.current ? Math.round(performance.now() - turnStartedAtRef.current) : undefined,
    });
    onTranscript(text);
  }, [enabled, onTranscript, sessionId]);

  const startListening = useCallback(async () => {
    if (!isSupported || isListening) return;

    const interruptedPlayback = Boolean(audioRef.current || abortRef.current);
    stopPlayback();
    if (interruptedPlayback) {
      const latencyMs = turnStartedAtRef.current ? Math.round(performance.now() - turnStartedAtRef.current) : undefined;
      void recordVoiceEvent({
        session_id: sessionId,
        phase: 'voice_interrupted',
        provider: 'elevenlabs',
        transport: 'livekit',
        livekit_room: livekitSessionRef.current?.room ?? null,
        latency_ms: latencyMs,
      });
      options.onInterrupted?.({ latencyMs });
    }
    finalTranscriptRef.current = '';
    submittedTranscriptRef.current = false;
    turnStartedAtRef.current = performance.now();
    setStatus('Preparing LiveKit voice session...');

    try {
      let livekitSession = livekitSessionRef.current;
      if (!livekitRoomRef.current || !livekitSession) {
        const createdSession = await createVoiceLiveKitSession(sessionId);
        livekitSession = {
          room: createdSession.room,
          serverUrl: createdSession.server_url,
          participantToken: createdSession.participant_token,
          traceId: createdSession.trace_id,
        };
        livekitSessionRef.current = livekitSession;
        setStatus('Connecting LiveKit room...');
        const { Room, RoomEvent } = await import('livekit-client');
        const room = new Room({
          adaptiveStream: true,
          dynacast: true,
        });
        room.on(RoomEvent.Disconnected, () => {
          setStatus((current) => current?.includes('Listening') ? 'LiveKit disconnected' : current);
        });
        room.on(RoomEvent.ConnectionQualityChanged, () => {
          void recordVoiceEvent({
            session_id: sessionId,
            phase: 'livekit_connection_quality',
            provider: 'livekit',
            transport: 'livekit',
            livekit_room: livekitSession?.room ?? null,
          });
        });
        await room.connect(createdSession.server_url, createdSession.participant_token);
        await room.localParticipant.setMicrophoneEnabled(true);
        livekitRoomRef.current = room;
        void recordVoiceEvent({
          session_id: sessionId,
          phase: 'livekit_room_ready',
          provider: 'livekit',
          transport: 'livekit',
          livekit_room: createdSession.room,
        });
      }
      setStatus('LiveKit room ready. Connecting ElevenLabs STT...');

      const token = await createVoiceSttToken();
      const params = new URLSearchParams({
        token: token.token,
        model_id: token.model_id,
        audio_format: token.audio_format,
        commit_strategy: 'vad',
        vad_silence_threshold_secs: '1.2',
        vad_threshold: '0.4',
        min_speech_duration_ms: '100',
        min_silence_duration_ms: '100',
        no_verbatim: 'true',
      });

      const socket = new WebSocket(`${ELEVENLABS_STT_WS_URL}?${params.toString()}`);
      socketRef.current = socket;

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as ElevenLabsRealtimeEvent;
          if (data.message_type === 'partial_transcript' && data.text) {
            setStatus(data.text);
            return;
          }
          if (
            (data.message_type === 'committed_transcript' ||
              data.message_type === 'committed_transcript_with_timestamps') &&
            data.text
          ) {
            finalTranscriptRef.current = `${finalTranscriptRef.current} ${data.text}`.trim();
            setStatus(data.text);
            stopListening();
          }
          if (data.message_type?.includes('error')) {
            setStatus(data.error || data.message || 'ElevenLabs STT error');
          }
        } catch {
          // Ignore malformed vendor events.
        }
      };

      socket.onclose = () => {
        cleanupAudioPipeline();
        setIsListening(false);
        submitTranscript();
      };

      await new Promise<void>((resolve, reject) => {
        socket.onopen = () => resolve();
        socket.onerror = () => reject(new Error('ElevenLabs STT connection failed'));
      });
      socket.onerror = () => {
        setStatus('ElevenLabs STT connection failed');
      };

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
        },
      });
      const AudioContextCtor = window.AudioContext;
      const context = new AudioContextCtor();
      const source = context.createMediaStreamSource(stream);
      const processor = context.createScriptProcessor(4096, 1, 1);

      processor.onaudioprocess = (event) => {
        if (socket.readyState !== WebSocket.OPEN) return;
        const input = event.inputBuffer.getChannelData(0);
        const pcm = downsampleTo16k(input, context.sampleRate);
        socket.send(
          JSON.stringify({
            message_type: 'input_audio_chunk',
            audio_base_64: pcmToBase64(pcm),
            sample_rate: STT_SAMPLE_RATE,
          })
        );
      };

      source.connect(processor);
      processor.connect(context.destination);
      pipelineRef.current = { context, source, processor, stream };
      setIsListening(true);
      setStatus(`Listening through LiveKit + ElevenLabs (${livekitSession.room})`);
    } catch (error) {
      cleanupAudioPipeline();
      socketRef.current?.close();
      socketRef.current = null;
      setIsListening(false);
      setStatus(error instanceof Error ? error.message : 'Voice input failed');
      void recordVoiceEvent({
        session_id: sessionId,
        phase: 'voice_input_failed',
        provider: 'elevenlabs',
        transport: 'livekit',
        livekit_room: livekitSessionRef.current?.room ?? null,
      });
    }
  }, [cleanupAudioPipeline, isListening, isSupported, options, sessionId, stopListening, stopPlayback, submitTranscript]);

  useEffect(() => {
    startListeningRef.current = startListening;
  }, [startListening]);

  const toggleVoice = useCallback(() => {
    if (!isSupported) {
      setStatus('ElevenLabs voice mode needs microphone and WebSocket support');
      return;
    }

    setEnabled((current) => {
      const next = !current;
      if (!next) {
        shutdownVoice();
      } else {
        enabledRef.current = true;
        setStatus('Voice mode ready');
      }
      return next;
    });
  }, [isSupported, shutdownVoice]);

  const speak = useCallback(
    async (text: string) => {
      if (!enabled) return;

      const speakable = stripForSpeech(text);
      if (!speakable) return;

      stopPlayback();
      const abortController = new AbortController();
      abortRef.current = abortController;
      setStatus('Preparing ElevenLabs voice reply...');

      try {
        const blob = await synthesizeVoiceSpeech(speakable, abortController.signal);
        const audioUrl = URL.createObjectURL(blob);
        const audio = new Audio(audioUrl);
        audioRef.current = audio;
        audio.onended = () => {
          const latencyMs = turnStartedAtRef.current ? Math.round(performance.now() - turnStartedAtRef.current) : undefined;
          URL.revokeObjectURL(audioUrl);
          cleanupBargeInMonitor();
          audioRef.current = null;
          abortRef.current = null;
          setIsSpeaking(false);
          setStatus('Voice mode ready');
          void recordVoiceEvent({
            session_id: sessionId,
            phase: 'tts_playback_ended',
            provider: 'elevenlabs',
            transport: 'livekit',
            livekit_room: livekitSessionRef.current?.room ?? null,
            output_chars: speakable.length,
            latency_ms: latencyMs,
          });
          options.onPlaybackEnded?.({ outputChars: speakable.length, latencyMs });
          if (enabledRef.current) {
            window.setTimeout(() => {
              void startListening();
            }, 350);
          }
        };
        audio.onerror = () => {
          URL.revokeObjectURL(audioUrl);
          cleanupBargeInMonitor();
          audioRef.current = null;
          abortRef.current = null;
          setIsSpeaking(false);
          setStatus('ElevenLabs voice playback failed');
        };
        setStatus('Speaking with ElevenLabs...');
        setIsSpeaking(true);
        const playbackStartLatencyMs = turnStartedAtRef.current ? Math.round(performance.now() - turnStartedAtRef.current) : undefined;
        void recordVoiceEvent({
          session_id: sessionId,
          phase: 'tts_playback_started',
          provider: 'elevenlabs',
          transport: 'livekit',
          livekit_room: livekitSessionRef.current?.room ?? null,
          output_chars: speakable.length,
          latency_ms: playbackStartLatencyMs,
        });
        options.onPlaybackStarted?.({ outputChars: speakable.length, latencyMs: playbackStartLatencyMs });
        await audio.play();
        void startBargeInMonitor();
      } catch {
        cleanupBargeInMonitor();
        setIsSpeaking(false);
        if (abortController.signal.aborted) return;
        setStatus('ElevenLabs voice playback is unavailable');
        void recordVoiceEvent({
          session_id: sessionId,
          phase: 'tts_playback_failed',
          provider: 'elevenlabs',
          transport: 'livekit',
          livekit_room: livekitSessionRef.current?.room ?? null,
          output_chars: speakable.length,
        });
      }
    },
    [cleanupBargeInMonitor, enabled, options, sessionId, startBargeInMonitor, startListening, stopPlayback]
  );

  useEffect(() => {
    return () => {
      socketRef.current?.close();
      cleanupAudioPipeline();
      cleanupBargeInMonitor();
      disconnectLiveKit();
      stopPlayback();
    };
  }, [cleanupAudioPipeline, cleanupBargeInMonitor, disconnectLiveKit, stopPlayback]);

  return {
    enabled,
    isListening,
    isSpeaking,
    isSupported,
    status,
    toggleVoice,
    startListening,
    stopListening,
    speak,
  };
}
