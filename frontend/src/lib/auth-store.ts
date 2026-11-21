import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

export type Role = 'CUSTOMER' | 'SHOP_OWNER' | 'ADMIN'

export interface SessionUser {
  id: string
  phoneNumber: string
  fullName: string | null
  role: Role
  profileCompleted: boolean
}

export interface Tokens {
  accessToken: string
  refreshToken: string
}

interface AuthState {
  tokens: Tokens | null
  user: SessionUser | null
  signIn: (tokens: Tokens, user: SessionUser) => void
  setTokens: (tokens: Tokens) => void
  setUser: (user: SessionUser) => void
  signOut: () => void
}

/**
 * Session state. Tokens are kept in localStorage so a reload keeps the member signed in; access
 * tokens are short-lived (15 min) and refresh tokens rotate on every use.
 */
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      tokens: null,
      user: null,
      signIn: (tokens, user) => set({ tokens, user }),
      setTokens: (tokens) => set({ tokens }),
      setUser: (user) => set({ user }),
      signOut: () => set({ tokens: null, user: null }),
    }),
    {
      name: 'brewpass-session',
      storage: createJSONStorage(() => localStorage),
      partialize: ({ tokens, user }) => ({ tokens, user }),
    },
  ),
)

export const isSignedIn = (state: AuthState) => state.tokens !== null
