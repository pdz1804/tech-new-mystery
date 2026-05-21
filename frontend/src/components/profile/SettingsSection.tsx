'use client';

import { ReactNode } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

interface SettingsSectionProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
  icon?: ReactNode;
}

export function SettingsSection({
  title,
  subtitle,
  children,
  className,
  icon,
}: SettingsSectionProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className={cn(
        'glass-panel p-5 md:p-7',
        className
      )}
    >
      <div className="mb-6">
        <div className="flex items-center gap-3">
          {icon && <div className="text-blue-600">{icon}</div>}
          <h2 className="font-sans text-2xl font-bold text-black">{title}</h2>
        </div>
        {subtitle && <p className="mt-2 text-sm text-black/60">{subtitle}</p>}
      </div>
      <div>{children}</div>
    </motion.div>
  );
}
