import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'

import type { Plan, Subscription } from '../../api/subscriptions'
import { validateCard } from '../../lib/card'
import { describePayment } from '../../lib/format'
import { fail, mockApi, ok, renderApp, signInAs } from '../../test/utils'

const PLANS: Plan[] = [
  {
    code: 'SIP',
    name: 'Sip',
    description: null,
    price: '89.99',
    currency: 'TRY',
    monthly_credits: 10,
    guest_credits: 0,
    priority_pickup: false,
    is_unlimited: false,
  },
  {
    code: 'DAILY',
    name: 'Daily',
    description: null,
    price: '149.99',
    currency: 'TRY',
    monthly_credits: 20,
    guest_credits: 2,
    priority_pickup: false,
    is_unlimited: false,
  },
  {
    code: 'BOTTOMLESS',
    name: 'Bottomless',
    description: null,
    price: '249.99',
    currency: 'TRY',
    monthly_credits: null,
    guest_credits: 5,
    priority_pickup: true,
    is_unlimited: true,
  },
]
const [SIP, DAILY, BOTTOMLESS] = PLANS

const subscription = (overrides: Partial<Subscription> = {}): Subscription => ({
  id: 'sub-1',
  status: 'ACTIVE',
  plan: DAILY,
  remaining_credits: 17,
  remaining_guest_credits: 2,
  current_period_start: '2026-11-21T10:00:00Z',
  current_period_end: '2026-12-21T10:00:00Z',
  pending_plan: null,
  payment_transaction_id: 'tx-1',
  cancelled_at: null,
  ...overrides,
})

const noPass = () => fail(404, 'NO_ACTIVE_SUBSCRIPTION', "You don't have an active pass.")

async function fillCard(user: ReturnType<typeof userEvent.setup>, number: string) {
  await user.type(screen.getByLabelText(/card number/i), number)
  await user.type(screen.getByLabelText(/expiry/i), '1230')
  await user.type(screen.getByLabelText(/cvc/i), '123')
  await user.type(screen.getByLabelText(/name on card/i), 'Zeynep Arslan')
}

beforeEach(() => signInAs())

describe('choosing and buying a pass', () => {
  it('shows the three passes when the member has none', async () => {
    mockApi({ 'GET /subscriptions/me': noPass, 'GET /subscriptions/plans': () => ok(PLANS) })
    renderApp('/pass')

    expect(await screen.findByRole('heading', { name: /choose your pass/i })).toBeVisible()
    const daily = screen.getByRole('article', { name: 'Daily' })
    expect(daily).toHaveTextContent('Most popular')
    expect(daily).toHaveTextContent('20 drinks a month')
    expect(daily).toHaveTextContent('2 drinks for friends')
    expect(screen.getByRole('article', { name: 'Bottomless' })).toHaveTextContent(
      'Unlimited drinks',
    )
    expect(within(daily).getByRole('link', { name: /choose daily/i })).toHaveAttribute(
      'href',
      '/pass/checkout?plan=DAILY',
    )
  })

  it('pays with a card and shows the confirmation', async () => {
    const user = userEvent.setup()
    let sent: unknown
    mockApi({
      'GET /subscriptions/me': noPass,
      'GET /subscriptions/plans': () => ok(PLANS),
      'POST /subscriptions': ({ body }) => {
        sent = body
        return ok(subscription({ remaining_credits: 20 }))
      },
    })
    renderApp('/pass/checkout?plan=DAILY')

    expect(await screen.findByRole('heading', { name: 'Daily pass' })).toBeVisible()
    await fillCard(user, '4242424242424242')
    expect(screen.getByLabelText(/card number/i)).toHaveValue('4242 4242 4242 4242')
    expect(screen.getByLabelText(/expiry/i)).toHaveValue('12 / 30')
    await user.click(screen.getByRole('button', { name: /pay ₺149,99/i }))

    expect(await screen.findByRole('heading', { name: /you're all set/i })).toBeVisible()
    expect(screen.getByRole('status')).toHaveTextContent('21 December 2026')
    expect(sent).toEqual({
      plan_code: 'DAILY',
      card: {
        number: '4242424242424242',
        exp_month: 12,
        exp_year: 2030,
        cvc: '123',
        holder_name: 'Zeynep Arslan',
      },
    })
  })

  it('shows a declined payment and lets the member try again', async () => {
    const user = userEvent.setup()
    mockApi({
      'GET /subscriptions/me': noPass,
      'GET /subscriptions/plans': () => ok(PLANS),
      'POST /subscriptions': () =>
        fail(402, 'PAYMENT_DECLINED', 'Payment declined. Try another card.'),
    })
    renderApp('/pass/checkout?plan=SIP')

    await screen.findByRole('heading', { name: 'Sip pass' })
    await fillCard(user, '4000000000000002')
    await user.click(screen.getByRole('button', { name: /pay/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Payment declined. Try another card.',
    )
    expect(screen.getByRole('button', { name: /pay/i })).toBeEnabled()
  })

  it('checks the card before sending it', async () => {
    const user = userEvent.setup()
    const fetchMock = mockApi({
      'GET /subscriptions/me': noPass,
      'GET /subscriptions/plans': () => ok(PLANS),
    })
    renderApp('/pass/checkout?plan=SIP')

    await screen.findByRole('heading', { name: 'Sip pass' })
    await user.type(screen.getByLabelText(/card number/i), '4242424242424241')
    await user.click(screen.getByRole('button', { name: /pay/i }))

    expect(screen.getByLabelText(/card number/i)).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByText('Check the card number.')).toBeVisible()
    expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith('/subscriptions'))).toBe(false)
  })

  it('sends members who already have a pass to their pass', async () => {
    mockApi({
      'GET /subscriptions/me': () => ok(subscription()),
      'GET /subscriptions/plans': () => ok(PLANS),
    })
    const { router } = renderApp('/pass/checkout?plan=SIP')

    await waitFor(() => expect(router.state.location.pathname).toBe('/pass'))
  })
})

describe('managing a pass', () => {
  it('shows drinks left, guest drinks and the renewal date', async () => {
    mockApi({
      'GET /subscriptions/me': () => ok(subscription()),
      'GET /subscriptions/plans': () => ok(PLANS),
    })
    renderApp('/pass')

    expect(await screen.findByText('Daily pass')).toBeVisible()
    expect(screen.getByRole('progressbar', { name: /drinks left/i })).toHaveAttribute(
      'aria-valuenow',
      '17',
    )
    expect(screen.getByText(/of 20 drinks left/)).toBeVisible()
    expect(screen.getByText(/2 guest drinks left/)).toBeVisible()
    expect(screen.getByText(/renews on 21 december 2026 for ₺149,99/i)).toBeVisible()
  })

  it('upgrades after confirming the price difference', async () => {
    const user = userEvent.setup()
    let patched: unknown
    mockApi({
      'GET /subscriptions/me': () => ok(subscription()),
      'GET /subscriptions/plans': () => ok(PLANS),
      'PATCH /subscriptions/me': ({ body }) => {
        patched = body
        return ok(subscription({ plan: BOTTOMLESS, remaining_credits: null }))
      },
      'GET /payments/me': () => ok([]),
    })
    renderApp('/pass')

    await user.click(await screen.findByRole('button', { name: /upgrade to bottomless/i }))
    const dialog = screen.getByRole('dialog', { name: /upgrade to bottomless/i })
    expect(dialog).toHaveTextContent('₺100,00')
    await user.click(within(dialog).getByRole('button', { name: /pay ₺100,00/i }))

    expect(await screen.findByText('Unlimited drinks')).toBeVisible()
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(patched).toEqual({ plan_code: 'BOTTOMLESS' })
  })

  it('schedules a downgrade and can keep the current pass', async () => {
    const user = userEvent.setup()
    const bodies: unknown[] = []
    mockApi({
      'GET /subscriptions/me': () => ok(subscription()),
      'GET /subscriptions/plans': () => ok(PLANS),
      'PATCH /subscriptions/me': ({ body }) => {
        bodies.push(body)
        const code = (body as { plan_code: string }).plan_code
        return ok(subscription({ pending_plan: code === 'SIP' ? SIP : null }))
      },
      'GET /payments/me': () => ok([]),
    })
    renderApp('/pass')

    await user.click(await screen.findByRole('button', { name: /switch to sip/i }))
    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveTextContent('You keep Daily until 21 December 2026')
    await user.click(within(dialog).getByRole('button', { name: /switch at renewal/i }))

    expect(await screen.findByText(/switches to/i)).toHaveTextContent(
      'Switches to Sip on 21 December 2026',
    )
    await user.click(screen.getByRole('button', { name: /keep daily/i }))

    await waitFor(() => expect(screen.queryByText(/switches to/i)).toBeNull())
    expect(bodies).toEqual([{ plan_code: 'SIP' }, { plan_code: 'DAILY' }])
  })

  it('cancels after confirmation and shows the passes again', async () => {
    const user = userEvent.setup()
    mockApi({
      'GET /subscriptions/me': () => ok(subscription()),
      'GET /subscriptions/plans': () => ok(PLANS),
      'DELETE /subscriptions/me': () => ok(subscription({ status: 'CANCELLED' })),
      'GET /payments/me': () => ok([]),
    })
    renderApp('/pass')

    await user.click(await screen.findByRole('button', { name: /cancel pass/i }))
    const dialog = screen.getByRole('dialog', { name: /cancel your pass/i })
    expect(within(dialog).getByRole('button', { name: /keep it/i })).toHaveFocus()
    await user.click(within(dialog).getByRole('button', { name: /cancel pass/i }))

    expect(await screen.findByRole('heading', { name: /choose your pass/i })).toBeVisible()
  })

  it('closes the dialog with Escape', async () => {
    const user = userEvent.setup()
    mockApi({
      'GET /subscriptions/me': () => ok(subscription()),
      'GET /subscriptions/plans': () => ok(PLANS),
    })
    renderApp('/pass')

    await user.click(await screen.findByRole('button', { name: /cancel pass/i }))
    await user.keyboard('{Escape}')

    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('lets a paused member retry the saved card', async () => {
    const user = userEvent.setup()
    let resumed: unknown
    mockApi({
      'GET /subscriptions/me': () => ok(subscription({ status: 'PAUSED', remaining_credits: 0 })),
      'GET /subscriptions/plans': () => ok(PLANS),
      'POST /subscriptions/me/resume': ({ body }) => {
        resumed = body
        return ok(subscription({ remaining_credits: 20 }))
      },
      'GET /payments/me': () => ok([]),
    })
    renderApp('/pass')

    expect(await screen.findByRole('heading', { name: /your pass is paused/i })).toBeVisible()
    expect(screen.queryByRole('heading', { name: /change pass/i })).toBeNull()
    await user.click(screen.getByRole('button', { name: /retry saved card/i }))

    await waitFor(() => expect(screen.queryByText(/is paused/i)).toBeNull())
    expect(resumed).toEqual({})
  })
})

describe('payment history', () => {
  it('lists paid and declined payments', async () => {
    mockApi({
      'GET /payments/me': () =>
        ok([
          {
            transaction_id: 't2',
            status: 'SUCCEEDED',
            amount: '60.00',
            currency: 'TRY',
            description: 'upgrade:SIP->DAILY',
            card_last4: '4242',
            failure_reason: null,
            created_at: '2026-11-21T10:05:00Z',
          },
          {
            transaction_id: 't1',
            status: 'FAILED',
            amount: '89.99',
            currency: 'TRY',
            description: 'subscription:SIP',
            card_last4: '0002',
            failure_reason: 'Card declined by the issuer.',
            created_at: '2026-11-21T10:00:00Z',
          },
        ]),
    })
    renderApp('/payments')

    const items = await screen.findAllByRole('listitem')
    expect(items[0]).toHaveTextContent('Upgrade Sip → Daily')
    expect(items[0]).toHaveTextContent('₺60,00')
    expect(items[0]).toHaveTextContent('Paid')
    expect(items[1]).toHaveTextContent('Sip pass')
    expect(items[1]).toHaveTextContent('Declined')
    expect(items[1]).toHaveTextContent('•••• 0002')
    expect(items[1]).toHaveTextContent('Card declined by the issuer.')
  })

  it('has an empty state', async () => {
    mockApi({ 'GET /payments/me': () => ok([]) })
    renderApp('/payments')

    expect(await screen.findByRole('heading', { name: /no payments yet/i })).toBeVisible()
  })
})

describe('card helpers', () => {
  const now = new Date('2026-11-21')
  const card = { number: '4242 4242 4242 4242', expiry: '12 / 30', cvc: '123', name: 'Zeynep' }

  it('accepts a valid card', () => {
    expect(validateCard(card, now).card).toMatchObject({ exp_month: 12, exp_year: 2030 })
  })

  it.each([
    [{ number: '4242 4242 4242 4241' }, 'number'],
    [{ expiry: '13 / 30' }, 'expiry'],
    [{ expiry: '10 / 26' }, 'expiry'],
    [{ cvc: '12' }, 'cvc'],
    [{ name: ' ' }, 'name'],
  ])('rejects %o', (change, field) => {
    expect(validateCard({ ...card, ...change }, now).errors).toHaveProperty(field)
  })

  it('accepts the current month', () => {
    expect(validateCard({ ...card, expiry: '11 / 26' }, now).card).not.toBeNull()
  })

  it.each([
    ['renewal:BOTTOMLESS', 'Bottomless pass renewal'],
    ['resume:SIP', 'Sip pass resumed'],
    ['something-else', 'something-else'],
  ])('describes %s', (raw, text) => expect(describePayment(raw)).toBe(text))
})
