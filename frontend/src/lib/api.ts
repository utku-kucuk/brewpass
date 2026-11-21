import { useAuthStore } from './auth-store'

/** Error returned by the API envelope `{ success: false, error: { code, message, details } }`. */
export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details: unknown

  constructor(status: number, code: string, message: string, details: unknown = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }

  /** Field-level messages from a VALIDATION_ERROR, keyed by field path. */
  fieldErrors(): Record<string, string> {
    if (this.code !== 'VALIDATION_ERROR' || !Array.isArray(this.details)) return {}
    return Object.fromEntries(
      (this.details as { field: string; message: string }[]).map((d) => [d.field, d.message]),
    )
  }
}

interface Envelope<T> {
  success: boolean
  data: T | null
  error: { code: string; message: string; details: unknown } | null
}

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'
  body?: unknown
  query?: Record<string, string | number | boolean | undefined | null>
  /** Send the access token (default true). */
  auth?: boolean
  signal?: AbortSignal
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

function buildUrl(path: string, query?: RequestOptions['query']): string {
  const url = `${API_BASE}/api/v1${path}`
  if (!query) return url
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== '') params.set(key, String(value))
  }
  const qs = params.toString()
  return qs ? `${url}?${qs}` : url
}

async function parse<T>(response: Response): Promise<T> {
  if (response.status === 204) return undefined as T
  let body: Envelope<T>
  try {
    body = (await response.json()) as Envelope<T>
  } catch {
    throw new ApiError(response.status, 'BAD_RESPONSE', 'Something went wrong. Please try again.')
  }
  if (!response.ok || !body.success) {
    const error = body.error ?? { code: 'HTTP_ERROR', message: response.statusText, details: null }
    throw new ApiError(response.status, error.code, error.message, error.details)
  }
  return body.data as T
}

async function send(path: string, options: RequestOptions, token: string | null) {
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (options.body !== undefined) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = `Bearer ${token}`
  try {
    return await fetch(buildUrl(path, options.query), {
      method: options.method ?? 'GET',
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal,
    })
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') throw error
    throw new ApiError(0, 'NETWORK_ERROR', 'Could not reach BrewPass. Check your connection.')
  }
}

let refreshing: Promise<boolean> | null = null

/** Rotate the token pair once, even if several requests hit an expired token at the same time. */
function refreshTokens(): Promise<boolean> {
  refreshing ??= (async () => {
    const tokens = useAuthStore.getState().tokens
    if (!tokens) return false
    try {
      const response = await send(
        '/auth/refresh',
        { method: 'POST', body: { refresh_token: tokens.refreshToken } },
        null,
      )
      const data = await parse<{ access_token: string; refresh_token: string }>(response)
      useAuthStore
        .getState()
        .setTokens({ accessToken: data.access_token, refreshToken: data.refresh_token })
      return true
    } catch {
      useAuthStore.getState().signOut()
      return false
    }
  })().finally(() => {
    refreshing = null
  })
  return refreshing
}

/** Call the BrewPass API and return the envelope's `data`. Throws `ApiError` on failure. */
export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const useAuth = options.auth ?? true
  const token = useAuth ? (useAuthStore.getState().tokens?.accessToken ?? null) : null
  const response = await send(path, options, token)

  if (response.status === 401 && token && (await refreshTokens())) {
    const retryToken = useAuthStore.getState().tokens?.accessToken ?? null
    return parse<T>(await send(path, options, retryToken))
  }
  return parse<T>(response)
}
