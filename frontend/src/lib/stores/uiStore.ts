/**
 * Zustand UI store for application state.
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

interface UIState {
  theme: 'light' | 'dark';
  sidebarOpen: boolean;
  searchModalOpen: boolean;
}

interface UIActions {
  setTheme: (theme: 'light' | 'dark') => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  toggleSearchModal: () => void;
  setSearchModalOpen: (open: boolean) => void;
}

type UIStore = UIState & UIActions;

const INITIAL_STATE: UIState = {
  theme: 'light',
  sidebarOpen: true,
  searchModalOpen: false,
};

export const useUIStore = create<UIStore>()(
  persist(
    (set) => ({
      ...INITIAL_STATE,

      setTheme: (theme) => set({ theme }),

      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

      setSidebarOpen: (open) => set({ sidebarOpen: open }),

      toggleSearchModal: () => set((state) => ({ searchModalOpen: !state.searchModalOpen })),

      setSearchModalOpen: (open) => set({ searchModalOpen: open }),
    }),
    {
      name: 'ui-storage',
      storage: createJSONStorage(() => localStorage),
    }
  )
);
