'use client';

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { usePathname } from 'next/navigation';
import {
  Bot,
  Loader2,
  Mic,
  MicOff,
  Minus,
  Phone,
  PhoneOff,
  Radio,
  RefreshCw,
  Volume2,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { createSession, listSessions, sendVoiceAgentMessage } from '@/lib/api/chat';
import { useAuthStore } from '@/lib/stores/authStore';
import { useVoiceAgent } from '@/hooks/useVoiceAgent';
import type { ChatSession } from '@/types/chat';

const VOICE_SESSION_DESCRIPTION = 'Dedicated voice-agent testing session';

type BotStage = 'idle' | 'preparing' | 'listening' | 'thinking' | 'speaking' | 'ready' | 'error';

function isVoiceSession(session: ChatSession): boolean {
  return session.description === VOICE_SESSION_DESCRIPTION;
}

export function FloatingVoiceBot() {
  const pathname = usePathname();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const isHydrated = useAuthStore((state) => state.isHydrated);
  const [isOpen, setIsOpen] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionsLoaded, setSessionsLoaded] = useState(false);
  const [isPreparing, setIsPreparing] = useState(false);
  const [autoStartToken, setAutoStartToken] = useState(0);

  const hiddenRoute = pathname?.startsWith('/login') || pathname?.startsWith('/register');

  useEffect(() => {
    if (!isHydrated || !isAuthenticated || hiddenRoute || sessionsLoaded) return;

    let cancelled = false;
    void (async () => {
      try {
        const response = await listSessions(1, 50);
        if (cancelled) return;
        const existing = response.sessions.find(isVoiceSession);
        if (existing) {
          setSessionId(existing.id);
        }
      } finally {
        if (!cancelled) setSessionsLoaded(true);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [hiddenRoute, isAuthenticated, isHydrated, sessionsLoaded]);

  const ensureVoiceSession = useCallback(async () => {
    if (sessionId) return sessionId;

    setIsPreparing(true);
    try {
      const session = await createSession({
        title: 'Voice agent session',
        description: VOICE_SESSION_DESCRIPTION,
      });
      setSessionId(session.id);
      return session.id;
    } finally {
      setIsPreparing(false);
    }
  }, [sessionId]);

  const openAndStart = useCallback(async () => {
    setIsOpen(true);
    await ensureVoiceSession();
    setAutoStartToken((value) => value + 1);
  }, [ensureVoiceSession]);

  if (!isHydrated || !isAuthenticated || hiddenRoute) {
    return null;
  }

  return (
    <div className="fixed bottom-[max(1rem,env(safe-area-inset-bottom))] right-4 z-40 sm:right-5">
      {isOpen && sessionId ? (
        <FloatingVoicePanel
          sessionId={sessionId}
          autoStartToken={autoStartToken}
          onMinimize={() => setIsOpen(false)}
        />
      ) : (
        <button
          type="button"
          onClick={openAndStart}
          disabled={isPreparing}
          className="group relative flex h-14 w-14 items-center justify-center rounded-full border border-white/70 bg-slate-950 text-white shadow-[0_22px_48px_rgba(15,23,42,0.28),inset_0_1px_0_rgba(255,255,255,0.22)] transition-all hover:-translate-y-0.5 hover:bg-slate-800 active:scale-95 disabled:opacity-60"
          aria-label="Open voice agent"
          title="Open voice agent"
        >
          <span className="absolute -inset-1 rounded-full border border-blue-400/25 opacity-0 transition-opacity group-hover:opacity-100" />
          {isPreparing ? <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" /> : <Phone className="h-5 w-5" aria-hidden="true" />}
        </button>
      )}
    </div>
  );
}

function FloatingVoicePanel({
  sessionId,
  autoStartToken,
  onMinimize,
}: {
  sessionId: string;
  autoStartToken: number;
  onMinimize: () => void;
}) {
  const [transcript, setTranscript] = useState<string | null>(null);
  const [answer, setAnswer] = useState<string | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [mouthToEarMs, setMouthToEarMs] = useState<number | null>(null);
  const [isThinking, setIsThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const autoStartedRef = useRef(0);
  const spokenAnswerRef = useRef<string | null>(null);
  const transcriptCommittedAtRef = useRef<number | null>(null);

  const handleTranscript = useCallback(
    (text: string) => {
      setTranscript(text);
      setAnswer(null);
      setLatencyMs(null);
      setMouthToEarMs(null);
      setError(null);
      setIsThinking(true);
      transcriptCommittedAtRef.current = performance.now();

      void (async () => {
        try {
          const response = await sendVoiceAgentMessage({
            session_id: sessionId,
            content: text,
          });
          setAnswer(response.content);
          setLatencyMs(response.latency_ms);
        } catch (requestError) {
          setError(requestError instanceof Error ? requestError.message : 'Voice agent response failed');
          setAnswer('I could not get a voice response just now. Please try again.');
        } finally {
          setIsThinking(false);
        }
      })();
    },
    [sessionId]
  );

  const voice = useVoiceAgent(handleTranscript, sessionId, {
    onPlaybackStarted: () => {
      if (transcriptCommittedAtRef.current) {
        setMouthToEarMs(Math.round(performance.now() - transcriptCommittedAtRef.current));
      }
    },
    onInterrupted: () => {
      setMouthToEarMs(null);
    },
  });

  const {
    enabled,
    isListening,
    isSpeaking,
    isSupported,
    status,
    toggleVoice,
    startListening,
    stopListening,
    speak,
  } = voice;

  useEffect(() => {
    if (!answer || isThinking || !enabled) return;
    if (spokenAnswerRef.current === answer) return;
    spokenAnswerRef.current = answer;
    void speak(answer);
  }, [answer, enabled, isThinking, speak]);

  useEffect(() => {
    if (!autoStartToken || autoStartedRef.current === autoStartToken) return;
    autoStartedRef.current = autoStartToken;
    if (!enabled) {
      toggleVoice();
      window.setTimeout(() => {
        void startListening();
      }, 150);
      return;
    }
    void startListening();
  }, [autoStartToken, enabled, startListening, toggleVoice]);

  const stage: BotStage = error
    ? 'error'
    : isListening
      ? 'listening'
      : isThinking
        ? 'thinking'
        : isSpeaking
          ? 'speaking'
          : enabled
            ? 'ready'
            : 'idle';

  const actionLabel = isListening
    ? 'Finish turn'
    : isSpeaking
      ? 'Interrupt'
      : enabled
        ? 'Speak now'
        : 'Start voice';

  const stageLabel = useMemo(() => {
    if (!isSupported) return 'Unavailable';
    if (stage === 'listening') return 'Listening';
    if (stage === 'thinking') return 'Thinking';
    if (stage === 'speaking') return 'Speaking';
    if (stage === 'ready') return 'Ready';
    if (stage === 'error') return 'Needs retry';
    return 'Idle';
  }, [isSupported, stage]);

  const handlePrimary = useCallback(() => {
    if (!isSupported) return;
    if (!enabled) {
      toggleVoice();
      window.setTimeout(() => {
        void startListening();
      }, 140);
      return;
    }
    if (isListening) {
      stopListening();
      return;
    }
    void startListening();
  }, [enabled, isListening, isSupported, startListening, stopListening, toggleVoice]);

  const handleEnd = useCallback(() => {
    if (enabled) toggleVoice();
    onMinimize();
  }, [enabled, onMinimize, toggleVoice]);

  return (
    <section className="w-[calc(100vw-2rem)] max-w-[390px] overflow-hidden rounded-[26px] border border-white/70 bg-white/78 shadow-[0_28px_90px_rgba(15,23,42,0.25),inset_0_1px_0_rgba(255,255,255,0.88)] backdrop-blur-3xl">
      <div className="border-b border-white/65 bg-slate-950 px-4 py-3 text-white">
        <div className="flex items-center gap-3">
          <div className="relative flex h-10 w-10 items-center justify-center rounded-2xl bg-white/12">
            <Bot className="h-5 w-5" aria-hidden="true" />
            <span className={cn('absolute -right-0.5 -top-0.5 h-3 w-3 rounded-full border-2 border-slate-950', stage === 'listening' ? 'animate-pulse bg-emerald-400' : stage === 'speaking' ? 'animate-pulse bg-amber-300' : enabled ? 'bg-blue-400' : 'bg-slate-400')} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-bold">Tech News Voice</div>
            <div className="mt-0.5 flex items-center gap-1.5 text-[11px] font-semibold text-white/62">
              <Radio className="h-3 w-3" aria-hidden="true" />
              <span className="truncate">LiveKit + ElevenLabs</span>
            </div>
          </div>
          <button
            type="button"
            onClick={onMinimize}
            className="rounded-full p-2 text-white/68 transition-colors hover:bg-white/10 hover:text-white"
            aria-label="Minimize voice agent"
            title="Minimize"
          >
            <Minus className="h-4 w-4" aria-hidden="true" />
          </button>
          <button
            type="button"
            onClick={handleEnd}
            className="rounded-full p-2 text-white/68 transition-colors hover:bg-white/10 hover:text-white"
            aria-label="Close voice agent"
            title="Close"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      </div>

      <div className="p-4">
        <div className="mb-3 flex items-center gap-2 rounded-2xl border border-white/70 bg-white/64 px-3 py-2 text-xs text-slate-600 shadow-[inset_0_1px_0_rgba(255,255,255,0.86)]">
          {stage === 'thinking' && <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-600" aria-hidden="true" />}
          <span className="font-bold text-slate-950">{stageLabel}</span>
          <span className="text-slate-300">/</span>
          <span className="min-w-0 flex-1 truncate">{status || (isSupported ? 'Voice line ready' : 'Browser voice unsupported')}</span>
        </div>

        <VoiceWave active={isListening || isSpeaking || isThinking} stage={stage} />

        <div className="mt-4 grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={handlePrimary}
            disabled={!isSupported}
            className={cn(
              'inline-flex h-11 items-center justify-center gap-2 rounded-2xl px-3 text-sm font-bold text-white shadow-[0_14px_30px_rgba(15,23,42,0.18)] transition-all active:scale-95 disabled:cursor-not-allowed disabled:opacity-45',
              isListening ? 'bg-emerald-600 hover:bg-emerald-500' : isSpeaking ? 'bg-amber-600 hover:bg-amber-500' : 'bg-slate-950 hover:bg-slate-800'
            )}
          >
            {isListening || isSpeaking ? <Volume2 className="h-4 w-4" aria-hidden="true" /> : <Mic className="h-4 w-4" aria-hidden="true" />}
            {actionLabel}
          </button>
          <button
            type="button"
            onClick={handleEnd}
            className="inline-flex h-11 items-center justify-center gap-2 rounded-2xl border border-white/75 bg-white/70 px-3 text-sm font-bold text-slate-700 shadow-[inset_0_1px_0_rgba(255,255,255,0.86)] transition-all hover:bg-white hover:text-slate-950 active:scale-95"
          >
            {enabled ? <PhoneOff className="h-4 w-4" aria-hidden="true" /> : <MicOff className="h-4 w-4" aria-hidden="true" />}
            End
          </button>
        </div>

        {(latencyMs !== null || mouthToEarMs !== null) && (
          <div className="mt-3 flex flex-wrap gap-2 text-[11px] font-semibold text-slate-500">
            {latencyMs !== null && (
              <span className="rounded-full border border-white/70 bg-white/64 px-2 py-1">Agent {latencyMs} ms</span>
            )}
            {mouthToEarMs !== null && (
              <span className="rounded-full border border-white/70 bg-white/64 px-2 py-1">First audio {mouthToEarMs} ms</span>
            )}
          </div>
        )}

        <div className="mt-4 space-y-2">
          <TurnPreview label="You" content={transcript} empty="No question yet." />
          <TurnPreview label="Agent" content={isThinking ? null : answer} empty={isThinking ? 'Working...' : 'No reply yet.'} />
        </div>

        {error && (
          <div className="mt-3 flex items-center justify-between gap-3 rounded-2xl border border-red-200/70 bg-red-50/76 px-3 py-2 text-xs text-red-700">
            <span className="line-clamp-2">{error}</span>
            <button
              type="button"
              onClick={() => {
                setError(null);
                void startListening();
              }}
              className="rounded-full p-1.5 transition-colors hover:bg-red-100"
              aria-label="Retry voice turn"
              title="Retry"
            >
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
            </button>
          </div>
        )}
      </div>
    </section>
  );
}

function VoiceWave({ active, stage }: { active: boolean; stage: BotStage }) {
  const bars = [0.45, 0.8, 0.55, 1, 0.62, 0.9, 0.5, 0.72, 0.48, 0.84, 0.58, 0.7];
  const color = stage === 'listening' ? 'bg-emerald-500' : stage === 'speaking' ? 'bg-amber-500' : 'bg-blue-500';

  return (
    <div className="flex h-20 items-center justify-center rounded-[22px] border border-white/70 bg-slate-950 shadow-[inset_0_1px_0_rgba(255,255,255,0.12)]">
      <div className="flex h-12 items-center gap-1.5">
        {bars.map((scale, index) => (
          <span
            key={index}
            className={cn('block w-1.5 rounded-full opacity-80 transition-all', color, active && 'animate-pulse')}
            style={{
              height: `${Math.round(34 * scale)}px`,
              animationDelay: `${index * 75}ms`,
            }}
          />
        ))}
      </div>
    </div>
  );
}

function TurnPreview({
  label,
  content,
  empty,
}: {
  label: string;
  content: string | null;
  empty: string;
}) {
  return (
    <div className="rounded-2xl border border-white/70 bg-white/58 px-3 py-2 shadow-[inset_0_1px_0_rgba(255,255,255,0.86)]">
      <div className="mb-1 text-[10px] font-bold uppercase tracking-[0.08em] text-slate-400">{label}</div>
      <p className={cn('line-clamp-3 text-xs leading-5', content ? 'text-slate-700' : 'text-slate-400')}>
        {content || empty}
      </p>
    </div>
  );
}
