/**
 * Input component with standard and glass variants.
 * Supports labels, error states, and accessibility features.
 */

import { cn } from '@/lib/utils';
import { AlertCircle } from 'lucide-react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  variant?: 'default' | 'glass';
  helperText?: string;
  icon?: React.ReactNode;
}

/**
 * Input renders a text input field with optional label and error handling.
 *
 * @example
 * ```tsx
 * <Input label="Email" type="email" placeholder="you@example.com" />
 * ```
 *
 * @example
 * ```tsx
 * <Input
 *   label="Search"
 *   variant="glass"
 *   placeholder="Search articles..."
 * />
 * ```
 */
export function Input({
  label,
  error,
  className,
  id,
  variant = 'default',
  helperText,
  icon,
  ...props
}: InputProps) {
  const inputId = id || label?.toLowerCase().replace(/\s+/g, '-');
  const errorId = error ? `${inputId}-error` : undefined;

  const variantStyles = {
    default: cn(
      'input-base',
      error && 'border-error focus:border-error focus:ring-error/20'
    ),
    glass: cn(
      'input-base bg-white/50 backdrop-blur-sm border-white/50',
      error && 'border-error focus:border-error focus:ring-error/20'
    ),
  };

  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label
          htmlFor={inputId}
          className="text-sm font-medium text-text-primary"
        >
          {label}
        </label>
      )}
      <div className="relative flex items-center">
        {icon && (
          <div className="absolute left-3 flex items-center pointer-events-none text-text-secondary">
            {icon}
          </div>
        )}
        <input
          id={inputId}
          aria-invalid={error ? 'true' : 'false'}
          aria-describedby={errorId}
          className={cn(
            variantStyles[variant],
            icon && 'pl-10',
            error && 'border-status-error',
            className
          )}
          {...props}
        />
        {error && (
          <div className="absolute right-3 flex items-center text-status-error pointer-events-none">
            <AlertCircle size={18} />
          </div>
        )}
      </div>
      {error && (
        <p id={errorId} role="alert" className="text-sm text-status-error flex items-center gap-1">
          {error}
        </p>
      )}
      {helperText && !error && (
        <p className="text-xs text-text-secondary">
          {helperText}
        </p>
      )}
    </div>
  );
}
