/**
 * Badge component - For status indicators and tags.
 * Supports multiple variants for different use cases (featured, trending, status, etc).
 */

import { ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { TrendingUp, Star } from 'lucide-react';

interface BadgeProps {
  children: ReactNode;
  variant?: 'primary' | 'featured' | 'trending' | 'success' | 'warning' | 'error' | 'info';
  size?: 'sm' | 'md';
  icon?: boolean;
  className?: string;
}

/**
 * Badge renders a styled badge/tag element.
 *
 * @example
 * ```tsx
 * <Badge variant="featured" icon>Featured</Badge>
 * ```
 *
 * @example
 * ```tsx
 * <Badge variant="trending" icon size="md">Trending</Badge>
 * ```
 */
export function Badge({
  children,
  variant = 'primary',
  size = 'md',
  icon = false,
  className,
}: BadgeProps) {
  const baseStyles = 'inline-flex items-center gap-1.5 font-semibold rounded-full border transition-smooth';

  const sizeStyles = {
    sm: 'px-2.5 py-1 text-xs',
    md: 'px-3 py-1.5 text-xs',
  };

  const variantStyles = {
    primary: 'bg-blue-100 text-blue-600 border-blue-200',
    featured: 'bg-blue-100 text-blue-600 border-blue-200',
    trending: 'bg-amber-100 text-amber-600 border-amber-200',
    success: 'bg-green-100 text-green-600 border-green-200',
    warning: 'bg-amber-100 text-amber-600 border-amber-200',
    error: 'bg-red-100 text-red-600 border-red-200',
    info: 'bg-blue-100 text-blue-600 border-blue-200',
  };

  const iconMap = {
    featured: <Star size={14} className="fill-current" />,
    trending: <TrendingUp size={14} />,
  };

  return (
    <span className={cn(baseStyles, sizeStyles[size], variantStyles[variant], className)}>
      {icon && variant in iconMap && iconMap[variant as keyof typeof iconMap]}
      {children}
    </span>
  );
}
