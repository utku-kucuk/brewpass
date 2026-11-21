import { Navigate, Outlet, useLocation } from 'react-router'

import { isSignedIn, useAuthStore } from '../../lib/auth-store'

/** Only signed-in members; others go to sign-in and come back afterwards. */
export function RequireAuth() {
  const signedIn = useAuthStore(isSignedIn)
  const location = useLocation()
  if (!signedIn) {
    const next = encodeURIComponent(location.pathname + location.search)
    return <Navigate to={`/sign-in?next=${next}`} replace />
  }
  return <Outlet />
}

/** Members must finish their profile (name) after the first sign-in. */
export function RequireProfile() {
  const completed = useAuthStore((state) => state.user?.profileCompleted ?? false)
  const location = useLocation()
  if (!completed) {
    const next = encodeURIComponent(location.pathname + location.search)
    return <Navigate to={`/welcome?next=${next}`} replace />
  }
  return <Outlet />
}
