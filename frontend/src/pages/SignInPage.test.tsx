import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { useAuthStore } from '../lib/auth-store'
import { fail, mockApi, ok, renderApp, sampleUser, signInAs } from '../test/utils'

const registered = ok({ phone_number: '+905321112233', is_new_user: true, otp_expires_in: 300 })

describe('sign-in flow', () => {
  it('sends signed-out visitors to sign-in and back after completing the profile', async () => {
    const user = userEvent.setup()
    const newUser = sampleUser({ full_name: null, profile_completed: false })
    mockApi({
      'POST /auth/register': () => registered,
      'POST /auth/verify-otp': ({ body }) =>
        (body as { code: string }).code === '1234'
          ? ok({
              access_token: 'a',
              refresh_token: 'r',
              token_type: 'bearer',
              expires_in: 900,
              user: newUser,
            })
          : fail(401, 'INVALID_OTP', 'Code is incorrect.', { remaining_attempts: 4 }),
      'GET /users/me': () => ok(newUser),
      'PATCH /users/me': ({ body }) =>
        ok(sampleUser({ full_name: (body as { full_name: string }).full_name })),
    })
    const { router } = renderApp('/profile')

    // Redirected to sign-in, remembering where we were going.
    expect(await screen.findByRole('heading', { name: /sign in or create/i })).toBeVisible()
    expect(router.state.location.search).toBe('?next=%2Fprofile')

    await user.type(screen.getByLabelText(/mobile number/i), '0532 111 22 33')
    await user.click(screen.getByRole('button', { name: /send code/i }))

    const codeInput = await screen.findByLabelText(/one-time code/i)
    expect(screen.getByText('+90 532 111 22 33')).toBeVisible()
    await user.type(codeInput, '9999')
    await user.click(screen.getByRole('button', { name: /verify/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Code is incorrect. 4 attempts left.',
    )

    await user.clear(codeInput)
    await user.type(codeInput, '1234')
    await user.click(screen.getByRole('button', { name: /verify/i }))

    // First sign-in: complete the profile, then continue to the original page.
    expect(await screen.findByRole('heading', { name: /welcome to brewpass/i })).toBeVisible()
    await user.type(await screen.findByLabelText(/full name/i), 'Zeynep Arslan')
    await user.click(screen.getByRole('button', { name: /continue/i }))

    expect(await screen.findByRole('heading', { name: /your profile/i })).toBeVisible()
    expect(router.state.location.pathname).toBe('/profile')
    expect(useAuthStore.getState().user?.profileCompleted).toBe(true)
  })

  it('validates the phone number before calling the API', async () => {
    const user = userEvent.setup()
    const fetchMock = mockApi({})
    renderApp('/sign-in')

    await user.type(await screen.findByLabelText(/mobile number/i), '12345')
    await user.click(screen.getByRole('button', { name: /send code/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/turkish mobile number/i)
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('shows server errors such as rate limiting', async () => {
    const user = userEvent.setup()
    mockApi({
      'POST /auth/register': () =>
        fail(429, 'RATE_LIMITED', 'Too many requests. Please slow down.'),
    })
    renderApp('/sign-in')

    await user.type(await screen.findByLabelText(/mobile number/i), '05321112233')
    await user.click(screen.getByRole('button', { name: /send code/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Too many requests')
  })
})

describe('route guards and shell', () => {
  it('sends members with an incomplete profile to the welcome page', async () => {
    signInAs({ profileCompleted: false, fullName: null })
    mockApi({ 'GET /users/me': () => ok(sampleUser({ full_name: null })) })

    const { router } = renderApp('/')

    expect(await screen.findByRole('heading', { name: /welcome to brewpass/i })).toBeVisible()
    expect(router.state.location.pathname).toBe('/welcome')
  })

  it('greets signed-in members and signs them out', async () => {
    const user = userEvent.setup()
    signInAs()
    const fetchMock = mockApi({ 'POST /auth/logout': () => ({ status: 204 }) })
    const { router } = renderApp('/')

    expect(await screen.findByRole('heading', { name: /good to see you, zeynep/i })).toBeVisible()
    await user.click(screen.getAllByRole('button', { name: /sign out/i })[0])

    await waitFor(() => expect(router.state.location.pathname).toBe('/sign-in'))
    expect(useAuthStore.getState().tokens).toBeNull()
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/auth/logout', expect.anything())
  })

  it('shows a friendly 404', async () => {
    renderApp('/does-not-exist')

    expect(await screen.findByRole('heading', { name: /this cup is empty/i })).toBeVisible()
  })
})
