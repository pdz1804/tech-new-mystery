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
      className="app-hero-panel"
    >
      <div className="px-5 py-6 sm:px-7">
        <div className="flex flex-col items-start justify-between gap-6 md:flex-row md:items-center">
          {/* User Info */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1, duration: 0.5 }}
            className="flex items-center gap-4"
          >
            {/* Avatar */}
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-blue-600 text-2xl font-bold text-white shadow-[0_14px_30px_rgba(0,122,255,0.24)]">
              {initials}
            </div>

            {/* Details */}
            <div>
              <span className="text-label mb-1 block text-blue-600">Account</span>
              <h1 className="font-sans text-3xl font-bold text-black md:text-4xl">{username}</h1>
              <p className="text-sm text-black/60 md:text-base">{email}</p>
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
              'btn-liquid secondary flex items-center gap-2 text-red-600'
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
