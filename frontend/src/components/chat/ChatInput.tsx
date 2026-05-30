'use client';

import React, { useState, useRef, useCallback, memo } from 'react';
import { Send, Square } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ChatInputProps } from '@/types/chat';

export const ChatInput = memo(function ChatInput({
  onSubmit,
  isLoading = false,
  disabled = false,
  placeholder = 'Message Tech News Mystery',
  onCancel,
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

  return (
    <div className="w-full">
      <div className="rounded-[26px] border border-black/8 border-t-white/70 bg-white/76 p-2.5 shadow-[0_18px_44px_rgba(15,23,42,0.12),inset_0_1px_0_rgba(255,255,255,0.75)] backdrop-blur-3xl transition-all focus-within:border-[#007AFF]/45 focus-within:bg-white/86 focus-within:shadow-[0_20px_52px_rgba(15,23,42,0.14),0_0_0_4px_rgba(0,122,255,0.12),inset_0_1px_0_rgba(255,255,255,0.8)]">
        <div className="flex items-end gap-2">
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
              className="mb-0.5 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-slate-950 text-white shadow-[0_10px_22px_rgba(15,23,42,0.2)] transition-transform active:scale-95"
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
                'mb-0.5 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full transition-all',
                isSubmitDisabled
                  ? 'bg-slate-200 text-slate-400'
                  : 'bg-[#007AFF] text-white shadow-[0_12px_26px_rgba(0,122,255,0.28)] hover:bg-[#0A84FF] active:scale-95'
              )}
              title="Send message"
              aria-label="Send message"
            >
              <Send className="h-4 w-4" aria-hidden="true" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
});

ChatInput.displayName = 'ChatInput';
