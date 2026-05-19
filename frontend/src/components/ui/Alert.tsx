import { cn } from '@/lib/utils';

interface AlertProps {
  variant?: 'error' | 'success' | 'info';
  children: string;
}

export function Alert({ variant = 'error', children }: AlertProps) {
  if (!children) return null;

  const variants = {
    error: 'bg-red-50 border-red-200 text-red-800',
    success: 'bg-green-50 border-green-200 text-green-800',
    info: 'bg-blue-50 border-blue-200 text-blue-800',
  };

  return (
    <div
      role="alert"
      aria-live={variant === 'error' ? 'assertive' : 'polite'}
      aria-atomic="true"
      className={cn('rounded-lg border px-4 py-3 text-sm', variants[variant])}
    >
      {children}
    </div>
  );
}
