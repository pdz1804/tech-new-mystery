import React, { ReactNode } from 'react';
import { motion } from 'framer-motion';

export type ButtonVariant = 'primary' | 'secondary' | 'tertiary';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface SquircleButtonProps {
  children: ReactNode;
  variant?: ButtonVariant;
  size?: ButtonSize;
  disabled?: boolean;
  onClick?: () => void;
  type?: 'button' | 'submit' | 'reset';
  className?: string;
  title?: string;
  ariaLabel?: string;
  ariaPressed?: boolean;
}

/**
 * Squircle Button - Apple-style button with physics spring animations
 *
 * Features:
 * - Continuous curvature (squircle) geometry
 * - Physics-based spring animations
 * - Three variants: primary (blue), secondary (glass), tertiary (text)
 * - Three sizes: sm, md, lg
 * - Full accessibility support
 */
export default function SquircleButton({
  children,
  variant = 'primary',
  size = 'md',
  disabled = false,
  onClick,
  type = 'button',
  className = '',
  title,
  ariaLabel,
  ariaPressed,
}: SquircleButtonProps) {
  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2.5 text-base',
    lg: 'px-6 py-3 text-lg',
  };

  const variantClasses = {
    primary: 'btn-primary',
    secondary: 'btn-secondary',
    tertiary: 'btn-tertiary',
  };

  const baseClass = `btn-base ${variantClasses[variant]} ${sizeClasses[size]}`;

  return (
    <motion.button
      className={`${baseClass} ${className}`.trim()}
      type={type}
      disabled={disabled}
      onClick={onClick}
      title={title}
      aria-label={ariaLabel}
      aria-pressed={ariaPressed}
      whileHover={disabled ? {} : { scale: 1.05 }}
      whileTap={disabled ? {} : { scale: 0.95 }}
      transition={{
        type: 'spring',
        stiffness: 300,
        damping: 0.8,
      }}
    >
      {children}
    </motion.button>
  );
}
