/**
 * Button component with 4 variants: primary, secondary, outline, glass.
 * Follows the redesign specifications with proper hover/focus states.
 */

import { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: 'primary' | 'secondary' | 'outline' | 'glass';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  ariaLabel?: string;
}

export function Button({
  children,
  className,
  variant = 'primary',
  size = 'md',
  disabled = false,
  ariaLabel,
  ...props
}: ButtonProps) {
  const baseStyles = cn(
    'font-semibold rounded-lg transition-smooth focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-600 disabled:opacity-50 disabled:cursor-not-allowed',
    {
      'px-3 py-2 text-sm': size === 'sm',
      'px-6 py-3 text-base': size === 'md',
      'px-8 py-4 text-lg': size === 'lg',
    }
  );

  const variantStyles = {
    primary: cn(
      baseStyles,
      'bg-brand-primary text-white hover:shadow-button-primary active:scale-95',
      'hover:translate-y-[-2px]'
    ),
    secondary: cn(
      baseStyles,
      'bg-brand-secondary text-white hover:shadow-button-secondary active:scale-95',
      'hover:translate-y-[-2px]'
    ),
    outline: cn(
      baseStyles,
      'border-2 border-brand-primary bg-transparent text-brand-primary',
      'hover:bg-brand-primary/5 active:bg-brand-primary/10'
    ),
    glass: cn(
      baseStyles,
      'glass text-brand-primary',
      'hover:translate-y-[-4px] hover:shadow-card-hover'
    ),
  };

  return (
    <button
      className={cn(variantStyles[variant], className)}
      disabled={disabled}
      aria-label={ariaLabel}
      {...props}
    >
      {children}
    </button>
  );
}
