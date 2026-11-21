import { describe, expect, it } from 'vitest'

import { fail, mockApi, ok, signInAs } from '../test/utils'
import { api, ApiError } from './api'
import { useAuthStore } from './auth-store'

describe('api', () => {
  it('returns the envelope data and sends query parameters', async () => {
    const fetchMock = mockApi({ 'GET /shops': ({ url }) => ok({ q: url.searchParams.get('q') }) })

    const data = await api<{ q: string }>('/shops', { query: { q: 'moda', empty: '' } })

    expect(data).toEqual({ q: 'moda' })
    expect(String(fetchMock.mock.calls[0][0])).toBe('/api/v1/shops?q=moda')
  })

  it('throws ApiError with code, status and field errors', async () => {
    mockApi({
      'PATCH /users/me': () =>
        fail(422, 'VALIDATION_ERROR', 'Some fields are invalid.', [
          { field: 'email', message: 'Not an email' },
        ]),
    })

    const error = (await api('/users/me', { method: 'PATCH', body: {} }).catch(
      (e) => e,
    )) as ApiError

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 422, code: 'VALIDATION_ERROR' })
    expect(error.fieldErrors()).toEqual({ email: 'Not an email' })
  })

  it('turns network failures into a friendly error', async () => {
    mockApi({})
    globalThis.fetch = () => Promise.reject(new TypeError('Failed to fetch'))

    await expect(api('/shops')).rejects.toMatchObject({ code: 'NETWORK_ERROR' })
  })

  it('sends the access token', async () => {
    signInAs()
    mockApi({
      'GET /users/me': ({ headers }) => ok({ auth: headers.get('Authorization') }),
    })

    await expect(api('/users/me')).resolves.toEqual({ auth: 'Bearer access-1' })
  })

  it('refreshes once on 401 and retries concurrent requests with the new token', async () => {
    signInAs()
    let refreshCalls = 0
    const fetchMock = mockApi({
      'GET /users/me': ({ headers }) =>
        headers.get('Authorization') === 'Bearer access-2'
          ? ok({ name: 'Zeynep' })
          : fail(401, 'INVALID_TOKEN', 'Access token has expired.'),
      'POST /auth/refresh': ({ body }) => {
        refreshCalls += 1
        expect(body).toEqual({ refresh_token: 'refresh-1' })
        return ok({ access_token: 'access-2', refresh_token: 'refresh-2' })
      },
    })

    const results = await Promise.all([api('/users/me'), api('/users/me')])

    expect(results).toEqual([{ name: 'Zeynep' }, { name: 'Zeynep' }])
    expect(refreshCalls).toBe(1)
    expect(useAuthStore.getState().tokens).toEqual({
      accessToken: 'access-2',
      refreshToken: 'refresh-2',
    })
    expect(fetchMock).toHaveBeenCalledTimes(5)
  })

  it('signs out when the refresh token is rejected', async () => {
    signInAs()
    mockApi({
      'GET /users/me': () => fail(401, 'INVALID_TOKEN'),
      'POST /auth/refresh': () => fail(401, 'INVALID_REFRESH_TOKEN'),
    })

    await expect(api('/users/me')).rejects.toMatchObject({ status: 401 })
    expect(useAuthStore.getState().tokens).toBeNull()
  })
})
