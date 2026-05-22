/**
 * Zustand auth store for user authentication state.
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { UserResponse } from '@/types/auth';

interface AuthState {
  user: UserResponse | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  intendedDestination: string | null;
  isHydrated: boolean;
}

interface AuthActions {
  setAuth: (user: UserResponse, token: string) => void;
  clearAuth: () => void;
  updateUser: (user: Partial<UserResponse>) => void;
  setIntendedDestination: (destination: string | null) => void;
  setHydrated: () => void;
}

type AuthStore = AuthState & AuthActions;

const INITIAL_STATE: AuthState = {
  user: null,
  accessToken: null,
  isAuthenticated: false,
  intendedDestination: null,
  isHydrated: false,
};

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      ...INITIAL_STATE,

      setAuth: (user, accessToken) =>
        set({ user, accessToken, isAuthenticated: true, isHydrated: true }),

      clearAuth: () => set({ ...INITIAL_STATE, isHydrated: true }),

      updateUser: (updates) =>
        set((state) => ({
          user: state.user ? { ...state.user, ...updates } : null,
        })),

      setIntendedDestination: (destination) =>
        set({ intendedDestination: destination }),

      setHydrated: () => set({ isHydrated: true }),
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        accessToken: state.accessToken,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        intendedDestination: state.intendedDestination,
      }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          state.isHydrated = true;
        }
      },
    }
  )
);
