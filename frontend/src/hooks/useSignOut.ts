import { useQueryClient } from '@tanstack/react-query'
import { useCallback } from 'react'
import { useNavigate } from 'react-router'

import { logout } from '../api/auth'
import { useAuthStore } from '../lib/auth-store'

/** Revoke the refresh token (best effort), clear the session and cached data, go to sign-in. */
export function useSignOut() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  return useCallback(() => {
    const tokens = useAuthStore.getState().tokens
    if (tokens) void logout(tokens.refreshToken).catch(() => undefined)
    useAuthStore.getState().signOut()
    queryClient.clear()
    navigate('/sign-in', { replace: true })
  }, [navigate, queryClient])
}
