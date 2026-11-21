import { QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { vi } from 'vitest'

import type { User } from '../api/auth'
import { useAuthStore, type SessionUser } from '../lib/auth-store'
import { createQueryClient } from '../lib/query-client'
import { routes } from '../router'

type Handler = (request: { url: URL; method: string; body: unknown; headers: Headers }) => {
  status?: number
  body?: unknown
}

/** Envelope helpers matching the API. */
export const ok = (data: unknown) => ({ status: 200, body: { success: true, data, error: null } })
export const fail = (status: number, code: string, message = code, details: unknown = null) => ({
  status,
  body: { success: false, data: null, error: { code, message, details } },
})

/**
 * Replace `fetch` with a router of `"METHOD /path"` handlers (path without `/api/v1`).
 * Returns the mock so tests can inspect calls.
 */
export function mockApi(handlers: Record<string, Handler>) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const url = new URL(String(input), 'http://localhost')
    const method = init.method ?? 'GET'
    const key = `${method} ${url.pathname.replace(/^\/api\/v1/, '')}`
    const handler = handlers[key]
    if (!handler) throw new Error(`Unhandled request: ${key}`)
    const body = init.body ? JSON.parse(String(init.body)) : undefined
    const result = handler({ url, method, body, headers: new Headers(init.headers) })
    return new Response(result.body === undefined ? null : JSON.stringify(result.body), {
      status: result.status ?? 200,
      headers: { 'Content-Type': 'application/json' },
    })
  })
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

export const sampleUser = (overrides: Partial<User> = {}): User => ({
  id: 'user-1',
  phone_number: '+905321112233',
  full_name: 'Zeynep Arslan',
  email: null,
  role: 'CUSTOMER',
  preferences: { favorite_drinks: [], allergens: [] },
  profile_completed: true,
  created_at: '2026-11-21T00:00:00Z',
  ...overrides,
})

export function signInAs(user: Partial<SessionUser> = {}) {
  useAuthStore.getState().signIn(
    { accessToken: 'access-1', refreshToken: 'refresh-1' },
    {
      id: 'user-1',
      phoneNumber: '+905321112233',
      fullName: 'Zeynep Arslan',
      role: 'CUSTOMER',
      profileCompleted: true,
      ...user,
    },
  )
}

/** Render the real app routes at a given URL. */
export function renderApp(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  const queryClient = createQueryClient()
  const utils = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return { ...utils, router }
}
