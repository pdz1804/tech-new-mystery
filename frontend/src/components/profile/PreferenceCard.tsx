'use client';

import { ReactNode } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

interface PreferenceCardProps {
  label: string;
  description?: string;
  icon?: ReactNode;
  children?: ReactNode;
  className?: string;
}

export function PreferenceCard({
  label,
  description,
  icon,
  children,
  className,
}: PreferenceCardProps) {
  return (
    <motion.div
      whileHover={{ borderColor: '#2563EB', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' }}
      className={cn(
        'flex items-start gap-4 rounded-lg border border-slate-200 bg-white p-4 transition-all cursor-pointer',
        className
      )}
    >
      {children ? (
        <>
          <div className="mt-1">{children}</div>
          <div className="flex-1">
            <label className="flex items-center gap-2 font-medium text-slate-900 cursor-pointer">
              {icon}
              {label}
            </label>
            {description && <p className="mt-1 text-sm text-slate-600">{description}</p>}
          </div>
        </>
      ) : (
        <>
          {icon && <div className="mt-1">{icon}</div>}
          <div className="flex-1">
            <label className="flex items-center gap-2 font-medium text-slate-900">
              {label}
            </label>
            {description && <p className="mt-1 text-sm text-slate-600">{description}</p>}
          </div>
        </>
      )}
    </motion.div>
  );
}
