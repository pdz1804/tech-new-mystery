'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { useAuthStore } from '@/lib/stores/authStore';
import { AppLoadingState } from '@/components/ui/AppLoadingState';

interface ProtectedAdminRouteProps {
  children: React.ReactNode;
}

/**
 * Component that protects routes to only admin users.
 * Redirects to home page if user is not authenticated or not an admin.
 */
export function ProtectedAdminRoute({ children }: ProtectedAdminRouteProps) {
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  useEffect(() => {
    if (!isAuthenticated || !user?.is_admin) {
      router.push('/');
    }
  }, [isAuthenticated, user, router]);

  if (!isAuthenticated || !user?.is_admin) {
    return <AppLoadingState variant="default" />;
  }

  return <>{children}</>;
}
