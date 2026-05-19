/**
 * GlassCard component - A glassmorphic card with customizable blur and opacity.
 * Used for creating modern, semi-transparent layered UI elements.
 */

import { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  blurAmount?: 'xs' | 'sm' | 'base' | 'md' | 'lg' | 'xl';
  opacity?: 'light' | 'medium' | 'heavy';
  variant?: 'light' | 'dark';
  hoverable?: boolean;
  onClick?: () => void;
}

/**
 * GlassCard renders a glassmorphic card with backdrop blur effect.
 *
 * @example
 * ```tsx
 * <GlassCard blurAmount="base" opacity="light">
 *   Card content here
 * </GlassCard>
 * ```
 *
 * @example
 * ```tsx
 * <GlassCard variant="dark" hoverable onClick={() => handleClick()}>
 *   Interactive card
 * </GlassCard>
 * ```
 */
export function GlassCard({
  children,
  className,
  blurAmount = 'base',
  opacity = 'light',
  variant = 'light',
  hoverable = true,
  onClick,
}: GlassCardProps) {
  const opacityMap = {
    light: 0.7,
    medium: 0.5,
    heavy: 0.3,
  };

  const variantStyles = {
    light: cn(
      'backdrop-blur-[10px] border border-white/30',
      'shadow-glass'
    ),
    dark: cn(
      'backdrop-blur-[8px] border border-indigo-500/10',
      'bg-slate-900/5'
    ),
  };

  const blurMap = {
    xs: 'backdrop-blur-xs',
    sm: 'backdrop-blur-sm',
    base: 'backdrop-blur-[10px]',
    md: 'backdrop-blur-[12px]',
    lg: 'backdrop-blur-[16px]',
    xl: 'backdrop-blur-[20px]',
  };

  const bgOpacityStyle = variant === 'light'
    ? `rgba(255, 255, 255, ${opacityMap[opacity]})`
    : `rgba(31, 41, 55, ${opacityMap[opacity] * 0.1})`;

  return (
    <div
      className={cn(
        'rounded-lg transition-smooth',
        blurMap[blurAmount],
        variantStyles[variant],
        hoverable && 'cursor-pointer hover:shadow-card-hover hover:translate-y-[-4px]',
        className
      )}
      style={{
        backgroundColor: bgOpacityStyle,
      }}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => e.key === 'Enter' && onClick() : undefined}
    >
      {children}
    </div>
  );
}
