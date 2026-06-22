import { create } from "zustand";

interface AppState {
  // Sidebar
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;

  // Active page
  activePage: string;
  setActivePage: (page: string) => void;

  // Command palette
  commandPaletteOpen: boolean;
  setCommandPaletteOpen: (open: boolean) => void;

  // First-run "Getting started" guide (also re-openable from Help & Docs)
  welcomeOpen: boolean;
  setWelcomeOpen: (open: boolean) => void;

  // Chat
  chatOpen: boolean;
  setChatOpen: (open: boolean) => void;
  pendingChatPrompt: string;
  setPendingChatPrompt: (prompt: string) => void;

  // Notifications
  notificationCount: number;
  setNotificationCount: (count: number) => void;

  // GR&R wizard prefill (set by the Gage Registry "Run study" action)
  grrPrefill: { processName?: string; partTolerance?: number } | null;
  setGrrPrefill: (prefill: { processName?: string; partTolerance?: number } | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  sidebarCollapsed: false,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),

  activePage: "dashboard",
  setActivePage: (page) => set({ activePage: page }),

  commandPaletteOpen: false,
  setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),

  welcomeOpen: false,
  setWelcomeOpen: (open) => set({ welcomeOpen: open }),

  chatOpen: false,
  setChatOpen: (open) => set({ chatOpen: open }),
  pendingChatPrompt: "",
  setPendingChatPrompt: (prompt) => set({ pendingChatPrompt: prompt }),

  // Synced from the backend (active alert count); starts at zero until loaded.
  notificationCount: 0,
  setNotificationCount: (count) => set({ notificationCount: count }),

  grrPrefill: null,
  setGrrPrefill: (prefill) => set({ grrPrefill: prefill }),
}));
