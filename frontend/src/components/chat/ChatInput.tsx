'use client';

/**
 * ChatInput component with auto-expanding textarea,
 * character counter, and smart submit button.
 */

import React, { useState, useRef, useCallback, useEffect, memo } from 'react';
import { Send, Paperclip, Smile, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ChatInputProps } from '@/types/chat';

/**
 * Common command suggestions for the chat
 */
const COMMAND_SUGGESTIONS = [
  { prefix: '/search', label: 'Search articles', description: 'Search for articles' },
  { prefix: '/analyze', label: 'Analyze', description: 'Analyze selected content' },
  { prefix: '/compare', label: 'Compare', description: 'Compare articles or topics' },
];

/**
 * ChatInput component
 */
export const ChatInput = memo(function ChatInput({
  onSubmit,
  isLoading = false,
  disabled = false,
  placeholder = 'Ask about news, search articles, or analyze content...',
}: ChatInputProps) {
  const [value, setValue] = useState('');
  const [charCount, setCharCount] = useState(0);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [filteredSuggestions, setFilteredSuggestions] = useState(COMMAND_SUGGESTIONS);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const maxChars = 2000;

  // Auto-expand textarea as user types
  const adjustTextareaHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      const newHeight = Math.min(textarea.scrollHeight, 200);
      textarea.style.height = `${newHeight}px`;
    }
  }, []);

  // Handle input change
  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const newValue = e.target.value.slice(0, maxChars);
      setValue(newValue);
      setCharCount(newValue.length);
      adjustTextareaHeight();

      // Show suggestions if typing command
      if (newValue.startsWith('/')) {
        const cmd = newValue.toLowerCase();
        const filtered = COMMAND_SUGGESTIONS.filter((s) =>
          s.prefix.toLowerCase().startsWith(cmd)
        );
        setFilteredSuggestions(filtered);
        setShowSuggestions(filtered.length > 0);
      } else {
        setShowSuggestions(false);
      }
    },
    [adjustTextareaHeight]
  );

  // Handle form submission
  const handleSubmit = useCallback(() => {
    const trimmedValue = value.trim();
    if (trimmedValue && !isLoading && !disabled) {
      onSubmit(trimmedValue);
      setValue('');
      setCharCount(0);
      setShowSuggestions(false);
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  }, [value, onSubmit, isLoading, disabled]);

  // Handle keyboard events
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        handleSubmit();
      }

      if (e.key === 'Escape') {
        setShowSuggestions(false);
      }
    },
    [handleSubmit]
  );

  // Handle suggestion click
  const handleSuggestionClick = useCallback((prefix: string) => {
    setValue(prefix + ' ');
    setShowSuggestions(false);
    textareaRef.current?.focus();
    adjustTextareaHeight();
  }, [adjustTextareaHeight]);

  // Handle clear
  const handleClear = useCallback(() => {
    setValue('');
    setCharCount(0);
    setShowSuggestions(false);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.focus();
    }
  }, []);

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const isSubmitDisabled = !value.trim() || isLoading || disabled;
  const charCountPercent = (charCount / maxChars) * 100;

  return (
    <div ref={containerRef} className="w-full">
      {/* Input area */}
      <div className="relative bg-white border border-slate-200 rounded-2xl p-4 focus-within:border-blue-400 focus-within:ring-2 focus-within:ring-blue-100 transition-all shadow-sm">
        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onFocus={() => value.startsWith('/') && setShowSuggestions(true)}
          placeholder={placeholder}
          disabled={disabled || isLoading}
          rows={1}
          maxLength={maxChars}
          className={cn(
            'w-full bg-transparent text-slate-900 placeholder-slate-400 resize-none outline-none',
            'text-base leading-relaxed',
            'disabled:opacity-50 disabled:cursor-not-allowed'
          )}
          style={{
            maxHeight: '200px',
            minHeight: '44px',
          }}
          aria-label="Message input"
        />

        {/* Command suggestions dropdown */}
        {showSuggestions && filteredSuggestions.length > 0 && (
          <div className="absolute bottom-full left-4 right-4 mb-2 bg-white border border-slate-200 rounded-xl overflow-hidden shadow-lg z-50">
            {filteredSuggestions.map((suggestion) => (
              <button
                key={suggestion.prefix}
                onClick={() => handleSuggestionClick(suggestion.prefix)}
                className="w-full text-left px-3 py-2 hover:bg-slate-50 transition-colors border-b border-slate-100 last:border-b-0"
              >
                <div className="flex items-center gap-2">
                  <code className="text-sm font-mono text-blue-600">
                    {suggestion.prefix}
                  </code>
                  <span className="text-xs text-slate-500">
                    {suggestion.description}
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}

        {/* Bottom controls */}
        <div className="flex items-center justify-between gap-2 mt-3 pt-3 border-t border-slate-100">
          {/* Left side - action buttons */}
          <div className="flex gap-2">
            <button
              disabled={disabled || isLoading}
              className="p-2 hover:bg-slate-100 rounded-lg transition-colors text-slate-400 hover:text-slate-600 disabled:opacity-50 disabled:cursor-not-allowed"
              title="Attach file (coming soon)"
              aria-label="Attach file"
            >
              <Paperclip className="w-4 h-4" />
            </button>

            <button
              disabled={disabled || isLoading}
              className="p-2 hover:bg-slate-100 rounded-lg transition-colors text-slate-400 hover:text-slate-600 disabled:opacity-50 disabled:cursor-not-allowed"
              title="Open emoji picker (coming soon)"
              aria-label="Open emoji picker"
            >
              <Smile className="w-4 h-4" />
            </button>
          </div>

          {/* Right side - character count and send button */}
          <div className="flex items-center gap-3">
            {/* Character counter */}
            {charCount > maxChars * 0.8 && (
              <span
                className={cn(
                  'text-xs font-medium',
                  charCount > maxChars * 0.95
                    ? 'text-red-500'
                    : 'text-amber-500'
                )}
              >
                {charCount}/{maxChars}
              </span>
            )}

            {/* Character progress bar */}
            {charCount > 0 && (
              <div className="w-6 h-1 bg-slate-200 rounded-full overflow-hidden">
                <div
                  className={cn(
                    'h-full transition-all',
                    charCountPercent > 95
                      ? 'bg-red-500'
                      : charCountPercent > 80
                        ? 'bg-amber-500'
                        : 'bg-blue-500'
                  )}
                  style={{ width: `${charCountPercent}%` }}
                />
              </div>
            )}

            {/* Clear button (visible when there's text) */}
            {value && !isLoading && (
              <button
                onClick={handleClear}
                className="p-2 hover:bg-slate-100 rounded-lg transition-colors text-slate-400 hover:text-slate-600"
                title="Clear input"
                aria-label="Clear input"
              >
                <X className="w-4 h-4" />
              </button>
            )}

            {/* Send button */}
            <button
              onClick={handleSubmit}
              disabled={isSubmitDisabled}
              className={cn(
                'p-2 rounded-lg transition-all flex items-center gap-2',
                isSubmitDisabled
                  ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                  : 'bg-blue-600 text-white hover:bg-blue-700 active:scale-95 shadow-sm'
              )}
              title={isLoading ? 'Waiting for response...' : 'Send (Ctrl+Enter)'}
              aria-label="Send message"
            >
              {isLoading ? (
                <div className="w-4 h-4 border-2 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Helper text */}
      <p className="text-xs text-slate-400 mt-2">
        Type <code className="bg-slate-100 px-1 rounded text-slate-600">/</code> for commands · Press{' '}
        <kbd className="bg-slate-100 px-1.5 py-0.5 rounded text-xs font-mono text-slate-600">Ctrl+Enter</kbd>{' '}
        to send
      </p>
    </div>
  );
});

ChatInput.displayName = 'ChatInput';
