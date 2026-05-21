import React, { ReactNode, CSSProperties } from 'react';

export interface GlassContainerProps {
  children: ReactNode;
  variant?: 'default' | 'elevated' | 'nested';
  blur?: number;
  className?: string;
  style?: CSSProperties;
  onClick?: (e: React.MouseEvent<HTMLDivElement>) => void;
  role?: string;
  tabIndex?: number;
}

/**
 * Glass Container - Liquid Glass UI component following Apple's modern design
 *
 * Features:
 * - Frosted glass effect with backdrop blur
 * - Multiple variants (default, elevated, nested)
 * - Customizable blur strength
 * - Spatial depth with appropriate shadows
 * - Accessibility built-in
 */
export default function GlassContainer({
  children,
  variant = 'default',
  blur = 25,
  className = '',
  style = {},
  onClick,
  role,
  tabIndex,
}: GlassContainerProps) {
  const variantClasses = {
    default: 'glass-container',
    elevated: 'glass-container elevated',
    nested: 'glass-container nested',
  };

  const baseClass = variantClasses[variant];

  return (
    <div
      className={`${baseClass} ${className}`.trim()}
      style={{
        backdropFilter: `blur(${blur}px)`,
        WebkitBackdropFilter: `blur(${blur}px)`,
        ...style,
      }}
      onClick={onClick}
      role={role}
      tabIndex={tabIndex}
    >
      {children}
    </div>
  );
}
