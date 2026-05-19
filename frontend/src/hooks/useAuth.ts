'use client';

import { useRouter } from 'next/navigation';
import { useMutation, useQuery } from '@tanstack/react-query';
import { login, register, getCurrentUser } from '@/lib/api/auth';
import { useAuthStore } from '@/lib/stores/authStore';
import { authKeys } from '@/lib/queryKeys';

export function useLogin() {
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);
  const intendedDestination = useAuthStore((s) => s.intendedDestination);
  const setIntendedDestination = useAuthStore((s) => s.setIntendedDestination);

  return useMutation({
    mutationFn: ({ username, password }: { username: string; password: string }) =>
      login(username, password),
    onSuccess: async (tokenData) => {
      // Set token first so it's available for the next API call
      // Create a temporary user object with basic info
      const tempUser = {
        user_id: '',
        username: '',
        email: '',
        is_admin: false,
        created_at: new Date().toISOString(),
      };
      setAuth(tempUser, tokenData.access_token);

      // Now fetch the actual user data
      try {
        const { data: user } = await getCurrentUser();
        setAuth(user, tokenData.access_token);
      } catch (error) {
        console.error('Failed to fetch user data:', error);
      }

      // Redirect to intended destination or home
      const destination = intendedDestination || '/';
      setIntendedDestination(null);
      router.push(destination);
    },
  });
}

export function useRegister() {
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);

  return useMutation({
    mutationFn: ({
      username,
      email,
      password,
    }: {
      username: string;
      email: string;
      password: string;
    }) => register(username, email, password),
    onSuccess: async (tokenData) => {
      // Set token first so it's available for the next API call
      // Create a temporary user object with basic info
      const tempUser = {
        user_id: '',
        username: '',
        email: '',
        is_admin: false,
        created_at: new Date().toISOString(),
      };
      setAuth(tempUser, tokenData.access_token);

      // Now fetch the actual user data
      try {
        const { data: user } = await getCurrentUser();
        setAuth(user, tokenData.access_token);
      } catch (error) {
        console.error('Failed to fetch user data:', error);
      }
      router.push('/');
    },
  });
}

export function useLogout() {
  const router = useRouter();
  const clearAuth = useAuthStore((s) => s.clearAuth);

  return () => {
    clearAuth();
    router.push('/login');
  };
}

export function useCurrentUser() {
  const accessToken = useAuthStore((s) => s.accessToken);

  return useQuery({
    queryKey: authKeys.me(),
    queryFn: () => getCurrentUser().then((res) => res.data),
    enabled: !!accessToken,
  });
}

export function useIsAdmin() {
  const user = useAuthStore((state) => state.user);
  return user?.is_admin ?? false;
}

export function useIsAuthenticated() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  return isAuthenticated;
}
