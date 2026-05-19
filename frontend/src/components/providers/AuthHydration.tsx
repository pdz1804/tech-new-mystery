'use client';

import { useEffect } from 'react';
import { useAuthStore } from '@/lib/stores/authStore';
import { getCurrentUser } from '@/lib/api/auth';

export function AuthHydration() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const setAuth = useAuthStore((s) => s.setAuth);
  const clearAuth = useAuthStore((s) => s.clearAuth);

  useEffect(() => {
    if (accessToken) {
      getCurrentUser()
        .then(({ data: user }) => {
          setAuth(user, accessToken);
        })
        .catch(() => {
          clearAuth();
        });
    }
  }, [accessToken, setAuth, clearAuth]);

  return null;
}
