import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { fail, mockApi, ok, renderApp, sampleUser, signInAs } from '../test/utils'

describe('profile page', () => {
  it('loads, edits and saves the profile', async () => {
    const user = userEvent.setup()
    signInAs()
    let saved: unknown
    mockApi({
      'GET /users/me': () =>
        ok(sampleUser({ preferences: { favorite_drinks: ['Cortado'], allergens: [] } })),
      'PATCH /users/me': ({ body }) => {
        saved = body
        return ok(sampleUser())
      },
    })
    renderApp('/profile')

    const drinks = await screen.findByLabelText(/favourite drinks/i)
    expect(drinks).toHaveValue('Cortado')
    await user.type(drinks, ', Flat White')
    await user.type(screen.getByLabelText(/allergens/i), 'lactose')
    await user.click(screen.getByRole('button', { name: /save changes/i }))

    expect(await screen.findByRole('status')).toHaveTextContent('Saved.')
    expect(saved).toEqual({
      full_name: 'Zeynep Arslan',
      email: null,
      preferences: { favorite_drinks: ['Cortado', 'Flat White'], allergens: ['lactose'] },
    })
  })

  it('shows field errors from the API next to the field', async () => {
    const user = userEvent.setup()
    signInAs()
    mockApi({
      'GET /users/me': () => ok(sampleUser()),
      'PATCH /users/me': () =>
        fail(422, 'VALIDATION_ERROR', 'Some fields are invalid.', [
          { field: 'email', message: 'value is not a valid email address' },
        ]),
    })
    renderApp('/profile')

    await user.type(await screen.findByLabelText(/email/i), 'not-an-email')
    await user.click(screen.getByRole('button', { name: /save changes/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent('not a valid email')
    expect(screen.getByLabelText(/email/i)).toHaveAttribute('aria-invalid', 'true')
  })

  it('shows an error state with retry when loading fails', async () => {
    signInAs()
    mockApi({ 'GET /users/me': () => fail(503, 'SERVICE_UNAVAILABLE', 'Service unavailable.') })
    renderApp('/profile')

    expect(await screen.findByRole('alert', {}, { timeout: 3000 })).toHaveTextContent(
      'Service unavailable.',
    )
    expect(screen.getByRole('button', { name: /try again/i })).toBeVisible()
  })
})
