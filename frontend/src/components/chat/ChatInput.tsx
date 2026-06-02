'use client';

import React, { useState, useRef, useCallback, memo } from 'react';
import { Mic, MicOff, Send, Square } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ChatInputProps } from '@/types/chat';

export const ChatInput = memo(function ChatInput({
  onSubmit,
  isLoading = false,
  disabled = false,
  placeholder = 'Message Tech News Mystery',
  onCancel,
  voiceEnabled = false,
  voiceListening = false,
  voiceSupported = false,
  voiceStatus,
  voiceTransport,
  onToggleVoice,
  onEndVoice,
}: ChatInputProps) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const maxChars = 2000;

  const adjustTextareaHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`;
  }, []);

  const handleChange = useCallback(
    (event: React.ChangeEvent<HTMLTextAreaElement>) => {
      setValue(event.target.value.slice(0, maxChars));
      requestAnimationFrame(adjustTextareaHeight);
    },
    [adjustTextareaHeight]
  );

  const resetInput = useCallback(() => {
    setValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = '44px';
    }
  }, []);

  const handleSubmit = useCallback(() => {
    const trimmedValue = value.trim();
    if (!trimmedValue || isLoading || disabled) return;
    onSubmit(trimmedValue);
    resetInput();
  }, [disabled, isLoading, onSubmit, resetInput, value]);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  const isSubmitDisabled = !value.trim() || isLoading || disabled;
  const showVoiceControl = Boolean(onToggleVoice);

  return (
    <div className="w-full">
      <div className="rounded-[24px] border border-white/60 border-t-white/90 bg-white/72 p-2 shadow-[0_18px_44px_rgba(15,23,42,0.12),inset_0_1px_0_rgba(255,255,255,0.88)] backdrop-blur-3xl transition-all focus-within:border-blue-400/60 focus-within:bg-white/86 focus-within:shadow-[0_20px_52px_rgba(15,23,42,0.14),0_0_0_4px_rgba(37,99,235,0.12),inset_0_1px_0_rgba(255,255,255,0.9)]">
        <div className="flex items-end gap-2">
          {showVoiceControl && (
            <button
              type="button"
              onClick={onToggleVoice}
              disabled={!voiceSupported || disabled}
              className={cn(
                'mb-0.5 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-2xl border transition-all active:scale-95 disabled:cursor-not-allowed disabled:opacity-45',
                voiceEnabled
                  ? 'border-emerald-300/70 bg-emerald-50 text-emerald-700 shadow-[0_10px_22px_rgba(16,185,129,0.16)]'
                  : 'border-white/70 bg-white/66 text-slate-500 hover:bg-white/90 hover:text-slate-900'
              )}
              title={voiceSupported ? (voiceEnabled ? 'Talk or interrupt' : 'Start voice mode') : 'Voice input is not supported'}
              aria-label={voiceEnabled ? 'Talk or interrupt' : 'Start voice mode'}
            >
              {voiceEnabled ? <Mic className="h-4 w-4" aria-hidden="true" /> : <MicOff className="h-4 w-4" aria-hidden="true" />}
            </button>
          )}

          <textarea
            ref={textareaRef}
            value={value}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            maxLength={maxChars}
            className="min-h-11 flex-1 resize-none bg-transparent px-3 py-2.5 text-[15px] leading-6 text-slate-950 outline-none placeholder:text-slate-400 disabled:cursor-not-allowed disabled:opacity-50"
            style={{ height: '44px', maxHeight: '160px' }}
            aria-label="Message input"
          />

          {isLoading ? (
            <button
              type="button"
              onClick={onCancel}
              className="mb-0.5 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-2xl bg-slate-950 text-white shadow-[0_10px_22px_rgba(15,23,42,0.2)] transition-transform active:scale-95"
              title="Stop response"
              aria-label="Stop response"
            >
              <Square className="h-4 w-4 fill-current" aria-hidden="true" />
            </button>
          ) : (
            <button
              type="button"
              onClick={handleSubmit}
              disabled={isSubmitDisabled}
              className={cn(
                'mb-0.5 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-2xl transition-all',
                isSubmitDisabled
                  ? 'bg-slate-200 text-slate-400'
                  : 'bg-blue-600 text-white shadow-[0_12px_26px_rgba(37,99,235,0.28)] hover:bg-blue-500 active:scale-95'
              )}
              title="Send message"
              aria-label="Send message"
            >
              <Send className="h-4 w-4" aria-hidden="true" />
            </button>
          )}
        </div>
      </div>
      {showVoiceControl && (voiceStatus || voiceListening) && (
        <div className="mt-2 flex items-center gap-2 px-2 text-xs font-medium text-slate-500">
          <span
            className={cn(
              'h-2 w-2 rounded-full',
              voiceListening ? 'animate-pulse bg-emerald-500' : 'bg-slate-300'
            )}
            aria-hidden="true"
          />
          {voiceTransport && (
            <span className="rounded-full border border-white/70 bg-white/62 px-2 py-0.5 text-[10px] uppercase tracking-[0.08em] text-slate-500 shadow-[inset_0_1px_0_rgba(255,255,255,0.82)]">
              {voiceTransport}
            </span>
          )}
          <span>{voiceListening ? 'Listening...' : voiceStatus}</span>
          {voiceEnabled && onEndVoice && (
            <button
              type="button"
              onClick={onEndVoice}
              className="ml-auto rounded-full border border-white/70 bg-white/62 px-2.5 py-0.5 text-[11px] font-semibold text-slate-600 shadow-[inset_0_1px_0_rgba(255,255,255,0.82)] transition-colors hover:bg-white/88 hover:text-slate-950"
            >
              End voice
            </button>
          )}
        </div>
      )}
    </div>
  );
});

ChatInput.displayName = 'ChatInput';
