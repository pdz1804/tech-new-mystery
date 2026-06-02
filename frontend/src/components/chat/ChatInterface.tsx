'use client';

import React, { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Bot, Loader2, MessageSquareText, Mic, PanelLeftClose, PhoneOff, Volume2, Waves } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useStreamChat } from '@/hooks/useStreamChat';
import { useVoiceAgent } from '@/hooks/useVoiceAgent';
import { sendVoiceAgentMessage } from '@/lib/api/chat';
import type { ChatSession } from '@/types/chat';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';

export type AgentMode = 'chat' | 'voice';

interface ChatInterfaceProps {
  session: ChatSession;
  onSessionUpdate?: () => void;
  onCloseSidebar?: () => void;
  mode?: AgentMode;
  onModeChange?: (mode: AgentMode) => void;
  className?: string;
}

export const ChatInterface = memo(function ChatInterface({
  session,
  onSessionUpdate,
  onCloseSidebar,
  mode: controlledMode,
  onModeChange,
  className,
}: ChatInterfaceProps) {
  const {
    messages,
    isLoading,
    isLoadingHistory,
    error,
    sendMessage,
    cancelMessage,
    regenerateMessage,
    deleteMessage,
    clearError,
  } = useStreamChat(session.id);
  const [internalMode, setInternalMode] = useState<AgentMode>('chat');
  const mode = controlledMode ?? internalMode;
  const [voiceTranscript, setVoiceTranscript] = useState<string | null>(null);
  const [voiceAnswer, setVoiceAnswer] = useState<string | null>(null);
  const [voiceLatencyMs, setVoiceLatencyMs] = useState<number | null>(null);
  const [voiceAgentLoading, setVoiceAgentLoading] = useState(false);
  const chatSpokenMessageIdRef = useRef<string | null>(null);
  const chatAwaitingVoiceReplyRef = useRef(false);
  const voiceStartedAtRef = useRef<number | null>(null);
  const spokenVoiceAnswerRef = useRef<string | null>(null);

  const handleChatVoiceTranscript = useCallback(
    (text: string) => {
      chatAwaitingVoiceReplyRef.current = true;
      void sendMessage(text);
    },
    [sendMessage]
  );

  const chatVoice = useVoiceAgent(handleChatVoiceTranscript, session.id);
  const {
    enabled: chatVoiceEnabled,
    isListening: chatVoiceListening,
    isSupported: chatVoiceSupported,
    status: chatVoiceStatus,
    toggleVoice: toggleChatVoice,
    startListening: startChatListening,
    stopListening: stopChatListening,
    speak: speakChatReply,
  } = chatVoice;

  const ensureVoiceSession = useCallback(async () => {
    return session.id;
  }, [session.id]);

  const handleVoiceOnlyTranscript = useCallback(
    (text: string) => {
      setVoiceTranscript(text);
      setVoiceAnswer(null);
      setVoiceLatencyMs(null);
      setVoiceAgentLoading(true);
      voiceStartedAtRef.current = performance.now();

      void (async () => {
        try {
          const activeVoiceSessionId = await ensureVoiceSession();
          const response = await sendVoiceAgentMessage({
            session_id: activeVoiceSessionId,
            content: text,
          });
          setVoiceAnswer(response.content);
          setVoiceLatencyMs(response.latency_ms);
        } catch {
          setVoiceAnswer('I could not get a voice response just now. Please try again.');
        } finally {
          setVoiceAgentLoading(false);
          onSessionUpdate?.();
        }
      })();
    },
    [ensureVoiceSession, onSessionUpdate]
  );

  const voiceOnly = useVoiceAgent(handleVoiceOnlyTranscript, session.id);
  const {
    enabled: voiceEnabled,
    isListening: voiceListening,
    isSpeaking: voiceSpeaking,
    isSupported: voiceSupported,
    status: voiceStatus,
    toggleVoice,
    startListening,
    stopListening,
    speak: speakVoiceAnswer,
  } = voiceOnly;

  useEffect(() => {
    if (!isLoading) {
      onSessionUpdate?.();
    }
  }, [isLoading, onSessionUpdate]);

  useEffect(() => {
    if (!chatVoiceEnabled || !chatAwaitingVoiceReplyRef.current || isLoading || isLoadingHistory) return;

    const latestAssistant = [...messages]
      .reverse()
      .find((message) => message.role === 'assistant' && message.content.trim());

    if (!latestAssistant || chatSpokenMessageIdRef.current === latestAssistant.id) return;

    chatSpokenMessageIdRef.current = latestAssistant.id;
    chatAwaitingVoiceReplyRef.current = false;
    void speakChatReply(latestAssistant.content);
  }, [chatVoiceEnabled, isLoading, isLoadingHistory, messages, speakChatReply]);

  useEffect(() => {
    if (!voiceEnabled || voiceAgentLoading || !voiceAnswer) return;
    if (spokenVoiceAnswerRef.current === voiceAnswer) return;
    spokenVoiceAnswerRef.current = voiceAnswer;
    void speakVoiceAnswer(voiceAnswer);
  }, [speakVoiceAnswer, voiceAgentLoading, voiceAnswer, voiceEnabled]);

  const visibleCount = messages.filter((message) => message.role === 'user' || message.role === 'assistant').length;
  const latestVoiceTranscript = useMemo(() => {
    return voiceTranscript ?? [...messages].reverse().find((message) => message.role === 'user')?.content ?? null;
  }, [messages, voiceTranscript]);
  const latestVoiceAnswer = useMemo(() => {
    if (voiceAgentLoading) return null;
    return voiceAnswer ?? [...messages].reverse().find((message) => message.role === 'assistant')?.content ?? null;
  }, [messages, voiceAgentLoading, voiceAnswer]);

  const switchMode = useCallback(
    (nextMode: AgentMode) => {
      if (nextMode === 'chat' && voiceEnabled) {
        toggleVoice();
      }
      if (nextMode === 'voice' && chatVoiceEnabled) {
        toggleChatVoice();
      }
      setInternalMode(nextMode);
      onModeChange?.(nextMode);
    },
    [chatVoiceEnabled, onModeChange, toggleChatVoice, toggleVoice, voiceEnabled]
  );

  return (
    <div className={cn('flex h-full flex-col overflow-hidden bg-transparent', className)}>
      <div className="border-b border-white/55 bg-white/58 px-4 py-3 backdrop-blur-3xl md:px-6">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3 flex-1">
            <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-2xl border border-blue-100/80 bg-blue-50/80 text-blue-600 shadow-[inset_0_1px_0_rgba(255,255,255,0.84),0_10px_24px_rgba(37,99,235,0.10)]">
              <Bot className="h-[18px] w-[18px]" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <h1 className="truncate font-sans text-base font-bold text-slate-950">{session.title}</h1>
              <p className="mt-0.5 text-xs font-medium text-slate-500">
                {isLoadingHistory ? 'Loading...' : `${visibleCount} messages · ${mode === 'chat' ? 'Chat' : 'Voice test'}`}
              </p>
            </div>
          </div>

          <div className="hidden rounded-2xl border border-white/65 bg-white/58 p-1 shadow-[inset_0_1px_0_rgba(255,255,255,0.82)] backdrop-blur-2xl sm:flex">
            <button
              type="button"
              onClick={() => switchMode('chat')}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-semibold transition-all',
                mode === 'chat'
                  ? 'bg-slate-950 text-white shadow-[0_10px_22px_rgba(15,23,42,0.18)]'
                  : 'text-slate-600 hover:bg-white/70 hover:text-slate-950'
              )}
            >
              <MessageSquareText className="h-3.5 w-3.5" aria-hidden="true" />
              Chat
            </button>
            <button
              type="button"
              onClick={() => switchMode('voice')}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-semibold transition-all',
                mode === 'voice'
                  ? 'bg-slate-950 text-white shadow-[0_10px_22px_rgba(15,23,42,0.18)]'
                  : 'text-slate-600 hover:bg-white/70 hover:text-slate-950'
              )}
            >
              <Waves className="h-3.5 w-3.5" aria-hidden="true" />
              Voice
            </button>
          </div>

          {onCloseSidebar && (
            <button
              type="button"
              onClick={onCloseSidebar}
              className="ml-3 hidden rounded-2xl border border-white/60 bg-white/58 p-2 text-slate-600 shadow-sm backdrop-blur-xl transition-colors hover:bg-white/82 hover:text-slate-950 md:inline-flex"
              title="Hide sidebar"
              aria-label="Hide sidebar"
            >
              <PanelLeftClose className="h-4 w-4" aria-hidden="true" />
            </button>
          )}
        </div>
        <div className="mx-auto mt-3 flex max-w-5xl rounded-2xl border border-white/65 bg-white/58 p-1 shadow-[inset_0_1px_0_rgba(255,255,255,0.82)] backdrop-blur-2xl sm:hidden">
          <button
            type="button"
            onClick={() => switchMode('chat')}
            className={cn(
              'inline-flex flex-1 items-center justify-center gap-1.5 rounded-xl px-3 py-2 text-xs font-semibold transition-all',
              mode === 'chat' ? 'bg-slate-950 text-white shadow-sm' : 'text-slate-600'
            )}
          >
            <MessageSquareText className="h-3.5 w-3.5" aria-hidden="true" />
            Chat
          </button>
          <button
            type="button"
            onClick={() => switchMode('voice')}
            className={cn(
              'inline-flex flex-1 items-center justify-center gap-1.5 rounded-xl px-3 py-2 text-xs font-semibold transition-all',
              mode === 'voice' ? 'bg-slate-950 text-white shadow-sm' : 'text-slate-600'
            )}
          >
            <Waves className="h-3.5 w-3.5" aria-hidden="true" />
            Voice
          </button>
        </div>
      </div>

      {mode === 'chat' ? (
        <div className="min-h-0 flex-1">
          <MessageList
            messages={messages}
            isLoading={isLoading || isLoadingHistory}
            error={error}
            onRegenerate={regenerateMessage}
            onDelete={deleteMessage}
          />
        </div>
      ) : (
        <VoiceAgentConsole
          disabled={isLoadingHistory}
          isLoading={voiceAgentLoading}
          voiceEnabled={voiceEnabled}
          voiceListening={voiceListening}
          voiceSpeaking={voiceSpeaking}
          voiceSupported={voiceSupported}
          voiceStatus={voiceStatus}
          latestTranscript={latestVoiceTranscript}
          latestAnswer={latestVoiceAnswer}
          latencyMs={voiceLatencyMs}
          onStart={async () => {
            const activeVoiceSessionId = await ensureVoiceSession();
            if (!voiceEnabled) {
              toggleVoice();
              window.setTimeout(() => {
                if (session.id === activeVoiceSessionId) {
                  void startListening();
                }
              }, 140);
              return;
            }
            if (voiceSpeaking) {
              void startListening();
              return;
            }
            if (voiceListening) {
              stopListening();
              return;
            }
            void startListening();
          }}
          onEnd={() => {
            if (voiceEnabled) toggleVoice();
          }}
        />
      )}

      {/* Error message */}
      {error && (
        <div className="border-t border-red-200/50 bg-red-50/80 px-4 py-3 backdrop-blur-sm md:px-8">
          <div className="mx-auto max-w-4xl flex items-center justify-between">
            <p className="text-sm text-red-700">{error}</p>
            <button
              type="button"
              onClick={clearError}
              className="ml-4 text-xs font-medium text-red-600 hover:text-red-700"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {mode === 'chat' && (
        <div className="bg-gradient-to-t from-white/76 via-white/48 to-transparent px-3 pb-4 pt-3 backdrop-blur-2xl sm:px-6">
          <div className="mx-auto max-w-3xl">
            <ChatInput
              onSubmit={sendMessage}
              isLoading={isLoading}
              disabled={isLoadingHistory}
              onCancel={cancelMessage}
              placeholder="Message Tech News Mystery"
              voiceEnabled={chatVoiceEnabled}
              voiceListening={chatVoiceListening}
              voiceSupported={chatVoiceSupported}
              voiceStatus={chatVoiceStatus}
              voiceTransport={chatVoiceEnabled ? 'LiveKit' : null}
              onToggleVoice={() => {
                if (!chatVoiceEnabled) {
                  toggleChatVoice();
                  window.setTimeout(() => startChatListening(), 120);
                  return;
                }
                if (chatVoiceListening) {
                  stopChatListening();
                  return;
                }
                void startChatListening();
              }}
              onEndVoice={toggleChatVoice}
            />
          </div>
        </div>
      )}
    </div>
  );
});

ChatInterface.displayName = 'ChatInterface';

function VoiceAgentConsole({
  disabled,
  isLoading,
  voiceEnabled,
  voiceListening,
  voiceSpeaking,
  voiceSupported,
  voiceStatus,
  latestTranscript,
  latestAnswer,
  latencyMs,
  onStart,
  onEnd,
}: {
  disabled: boolean;
  isLoading: boolean;
  voiceEnabled: boolean;
  voiceListening: boolean;
  voiceSpeaking: boolean;
  voiceSupported: boolean;
  voiceStatus: string | null;
  latestTranscript: string | null;
  latestAnswer: string | null;
  latencyMs: number | null;
  onStart: () => void;
  onEnd: () => void;
}) {
  const statusLabel = voiceListening
    ? 'Listening'
    : isLoading
      ? 'Thinking'
      : voiceSpeaking
        ? 'Speaking'
        : voiceEnabled
          ? 'Ready'
          : 'Idle';

  return (
    <div className="min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:px-6">
      <div className="mx-auto flex min-h-full max-w-5xl flex-col justify-center gap-5">
        <div className="rounded-[28px] border border-white/65 border-t-white/90 bg-white/62 p-5 shadow-[0_24px_70px_rgba(15,23,42,0.12),inset_0_1px_0_rgba(255,255,255,0.88)] backdrop-blur-3xl sm:p-7">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-center">
            <div className="flex-1">
              <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-white/70 bg-white/58 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500 shadow-[inset_0_1px_0_rgba(255,255,255,0.82)]">
                <span className={cn('h-2 w-2 rounded-full', voiceListening ? 'animate-pulse bg-emerald-500' : voiceSpeaking ? 'animate-pulse bg-amber-500' : voiceEnabled ? 'bg-blue-500' : 'bg-slate-300')} />
                LiveKit · ElevenLabs
              </div>
              <h2 className="text-2xl font-bold tracking-[-0.01em] text-slate-950 sm:text-3xl">
                Voice agent test
              </h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
                Speak a full question and let the agent answer by voice. This view keeps the text stream quiet so the spoken response stays the main experience.
              </p>
            </div>

            <div className="flex flex-col items-stretch gap-3 sm:flex-row lg:flex-col">
              <button
                type="button"
                onClick={onStart}
                disabled={!voiceSupported || disabled}
                className={cn(
                  'inline-flex min-w-[180px] items-center justify-center gap-2 rounded-2xl px-5 py-3 text-sm font-bold text-white shadow-[0_18px_38px_rgba(15,23,42,0.18)] transition-all active:scale-95 disabled:cursor-not-allowed disabled:opacity-45',
                  voiceListening ? 'bg-emerald-600 hover:bg-emerald-500' : voiceSpeaking ? 'bg-amber-600 hover:bg-amber-500' : 'bg-slate-950 hover:bg-slate-800'
                )}
              >
                {voiceListening || voiceSpeaking ? <Volume2 className="h-4 w-4" aria-hidden="true" /> : <Mic className="h-4 w-4" aria-hidden="true" />}
                {voiceListening ? 'Finish turn' : voiceSpeaking ? 'Interrupt' : voiceEnabled ? 'Speak now' : 'Start voice'}
              </button>
              {voiceEnabled && (
                <button
                  type="button"
                  onClick={onEnd}
                  className="inline-flex min-w-[180px] items-center justify-center gap-2 rounded-2xl border border-white/70 bg-white/68 px-5 py-3 text-sm font-bold text-slate-700 shadow-[inset_0_1px_0_rgba(255,255,255,0.84)] transition-all hover:bg-white/90 hover:text-slate-950 active:scale-95"
                >
                  <PhoneOff className="h-4 w-4" aria-hidden="true" />
                  End voice
                </button>
              )}
            </div>
          </div>

          <div className="mt-6 rounded-2xl border border-white/65 bg-white/50 px-4 py-3 text-sm text-slate-600 shadow-[inset_0_1px_0_rgba(255,255,255,0.82)]">
            <div className="flex items-center gap-2">
              {isLoading && <Loader2 className="h-4 w-4 animate-spin text-blue-600" aria-hidden="true" />}
              <span className="font-semibold text-slate-900">{statusLabel}</span>
              <span className="text-slate-400">/</span>
              <span className="truncate">{voiceStatus || (voiceSupported ? 'Voice session ready for testing' : 'Voice is not supported in this browser')}</span>
              {voiceSpeaking && (
                <span className="ml-auto hidden rounded-full border border-amber-200/70 bg-amber-50/70 px-2 py-0.5 text-[11px] font-semibold text-amber-700 sm:inline-flex">
                  Press Interrupt to barge in
                </span>
              )}
              {latencyMs !== null && (
                <span className={cn('hidden rounded-full border border-white/70 bg-white/64 px-2 py-0.5 text-[11px] font-semibold text-slate-500 sm:inline-flex', !voiceSpeaking && 'ml-auto')}>
                  {latencyMs} ms
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <VoiceTurnCard
            label="You said"
            empty="No spoken question yet."
            content={latestTranscript}
          />
          <VoiceTurnCard
            label="Agent reply"
            empty={isLoading ? 'Preparing spoken response...' : 'No voice reply yet.'}
            content={latestAnswer}
            muted={isLoading}
          />
        </div>
      </div>
    </div>
  );
}

function VoiceTurnCard({
  label,
  empty,
  content,
  muted = false,
}: {
  label: string;
  empty: string;
  content: string | null;
  muted?: boolean;
}) {
  return (
    <section className="min-h-[180px] rounded-[24px] border border-white/60 border-t-white/90 bg-white/56 p-5 shadow-[0_18px_48px_rgba(15,23,42,0.10),inset_0_1px_0_rgba(255,255,255,0.84)] backdrop-blur-3xl">
      <div className="mb-3 text-[11px] font-bold uppercase tracking-[0.08em] text-slate-500">{label}</div>
      <p className={cn('max-h-60 overflow-hidden text-sm leading-6', content && !muted ? 'text-slate-800' : 'text-slate-400')}>
        {content && !muted ? content : empty}
      </p>
    </section>
  );
}
