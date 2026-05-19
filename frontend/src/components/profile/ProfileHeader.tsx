'use client';

import { motion } from 'framer-motion';
import { LogOut } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ProfileHeaderProps {
  username: string;
  email: string;
  onLogout: () => void;
}

export function ProfileHeader({ username, email, onLogout }: ProfileHeaderProps) {
  const initials = username?.[0]?.toUpperCase() || 'U';

  return (
    <motion.section
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="border-b border-slate-200 bg-gradient-to-r from-slate-50 to-slate-100"
    >
      <div className="mx-auto max-w-6xl px-4 py-8 md:py-12">
        <div className="flex flex-col items-start justify-between gap-6 md:flex-row md:items-center">
          {/* User Info */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1, duration: 0.5 }}
            className="flex items-center gap-4"
          >
            {/* Avatar */}
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-blue-600 text-2xl font-bold text-white shadow-md">
              {initials}
            </div>

            {/* Details */}
            <div>
              <h1 className="text-2xl font-bold text-slate-900 md:text-3xl">{username}</h1>
              <p className="text-sm text-slate-600 md:text-base">{email}</p>
            </div>
          </motion.div>

          {/* Logout Button */}
          <motion.button
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1, duration: 0.5 }}
            whileHover={{ scale: 1.02, boxShadow: '0 4px 12px rgba(239, 68, 68, 0.3)' }}
            whileTap={{ scale: 0.98 }}
            onClick={onLogout}
            className={cn(
              'flex items-center gap-2 rounded-lg border-2 border-red-500 px-6 py-2 font-semibold text-red-500',
              'transition-all duration-200 hover:bg-red-50'
            )}
          >
            <LogOut className="h-5 w-5" />
            <span className="hidden sm:inline">Logout</span>
          </motion.button>
        </div>
      </div>
    </motion.section>
  );
}
