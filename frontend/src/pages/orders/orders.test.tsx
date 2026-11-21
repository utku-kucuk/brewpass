import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { Order } from '../../api/orders'
import type { MenuItem, ShopDetail } from '../../api/shops'
import type { Subscription } from '../../api/subscriptions'
import { fail, mockApi, ok, renderApp, signInAs } from '../../test/utils'

vi.mock('../../components/shops/ShopMap', () => ({ ShopMap: () => null }))

const today = { weekday: 2, day: 'Wednesday', opens_at: '07:30:00', closes_at: '21:00:00' }
const SHOP: ShopDetail = {
  id: 'shop-1',
  name: 'Moda Roastery',
  address: 'Moda Cd. No:42',
  city: 'Istanbul',
  location: { lat: 40.98, lng: 29.02 },
  rating: '4.7',
  photo_url: null,
  distance_m: null,
  is_open_now: true,
  today,
  description: null,
  phone_number: null,
  opening_hours: [today],
}

const item = (overrides: Partial<MenuItem>): MenuItem => ({
  id: 'latte',
  name: 'Caffè Latte',
  description: 'Espresso with steamed milk.',
  category: 'HOT_COFFEE',
  list_price: '90.00',
  supports_milk: true,
  supports_extra_shot: true,
  image_url: null,
  is_available: true,
  ...overrides,
})
const MENU = {
  shop_id: 'shop-1',
  shop_name: 'Moda Roastery',
  items: [
    item({}),
    item({
      id: 'tea',
      name: 'Earl Grey Tea',
      category: 'TEA',
      supports_milk: false,
      supports_extra_shot: false,
    }),
  ],
}

const PASS: Subscription = {
  id: 'sub-1',
  status: 'ACTIVE',
  plan: {
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
  remaining_credits: 17,
  remaining_guest_credits: 2,
  current_period_start: '2026-11-21T10:00:00Z',
  current_period_end: '2026-12-21T10:00:00Z',
  pending_plan: null,
  payment_transaction_id: 'tx-1',
  cancelled_at: null,
}

const order = (overrides: Partial<Order> = {}): Order => ({
  id: 'order-1',
  status: 'PENDING',
  shop_id: 'shop-1',
  shop_name: 'Moda Roastery',
  product_id: 'latte',
  product_name: 'Caffè Latte',
  size: 'L',
  milk: 'OAT',
  sugar: 1,
  extra_shots: 1,
  note: null,
  is_guest: false,
  is_priority: false,
  is_favorite: false,
  created_at: '2026-11-21T10:00:00Z',
  completed_at: null,
  qr_payload: '{"order_id":"order-1","signature":"abc"}',
  status_history: [{ from_status: null, to_status: 'PENDING', created_at: '2026-11-21T10:00:00Z' }],
  ...overrides,
})

const builderApi = (extra: Parameters<typeof mockApi>[0] = {}) => ({
  'GET /shops/shop-1': () => ok(SHOP),
  'GET /shops/shop-1/menu': () => ok(MENU),
  'GET /subscriptions/me': () => ok(PASS),
  ...extra,
})

beforeEach(() => signInAs())

describe('ordering from the menu', () => {
  it('shows an Order button on available drinks for customers', async () => {
    mockApi(builderApi())
    renderApp('/shops/shop-1')

    const link = await screen.findByRole('link', { name: 'Order Caffè Latte' })
    expect(link).toHaveAttribute('href', '/shops/shop-1/order/latte')
  })

  it('hides ordering from shop owners', async () => {
    signInAs({ role: 'SHOP_OWNER' })
    mockApi(builderApi())
    renderApp('/shops/shop-1')

    await screen.findByText('Caffè Latte')
    expect(screen.queryByRole('link', { name: /^order /i })).toBeNull()
  })
})

describe('drink builder', () => {
  it('customizes a drink and places the order', async () => {
    const user = userEvent.setup()
    let sent: unknown
    mockApi(
      builderApi({
        'POST /orders': ({ body }) => {
          sent = body
          return ok(order())
        },
        'GET /orders/order-1': () => ok(order()),
      }),
    )
    const { router } = renderApp('/shops/shop-1/order/latte')

    expect(await screen.findByRole('heading', { name: 'Caffè Latte' })).toBeVisible()
    await user.click(screen.getByRole('radio', { name: 'Large' }))
    await user.click(screen.getByRole('radio', { name: 'Oat milk' }))
    await user.click(
      within(screen.getByRole('group', { name: 'Sugar' })).getByRole('radio', { name: '1' }),
    )
    await user.click(screen.getByRole('radio', { name: '+1' }))
    await user.type(screen.getByLabelText(/note for the barista/i), 'Extra hot')

    expect(
      screen.getByText('Caffè Latte · Large · Oat milk · 1 sugar · 1 extra shot'),
    ).toBeVisible()
    expect(screen.getByText('Uses 1 of your 17 drinks left this month.')).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Place order' }))

    await waitFor(() => expect(router.state.location.pathname).toBe('/orders/order-1'))
    expect(sent).toEqual({
      product_id: 'latte',
      size: 'L',
      milk: 'OAT',
      sugar: 1,
      extra_shots: 1,
      note: 'Extra hot',
      use_guest_credit: false,
    })
  })

  it('only offers options the drink supports', async () => {
    mockApi(builderApi())
    renderApp('/shops/shop-1/order/tea')

    await screen.findByRole('heading', { name: 'Earl Grey Tea' })
    expect(screen.queryByRole('group', { name: 'Milk' })).toBeNull()
    expect(screen.queryByRole('group', { name: 'Extra shots' })).toBeNull()
    expect(screen.getByRole('group', { name: 'Size' })).toBeVisible()
  })

  it('can pay with a guest drink', async () => {
    const user = userEvent.setup()
    let sent: { use_guest_credit?: boolean } = {}
    mockApi(
      builderApi({
        'POST /orders': ({ body }) => {
          sent = body as typeof sent
          return ok(order({ is_guest: true }))
        },
        'GET /orders/order-1': () => ok(order({ is_guest: true })),
      }),
    )
    renderApp('/shops/shop-1/order/latte')

    await user.click(await screen.findByLabelText(/use a guest drink/i))
    expect(screen.getByText('Uses 1 of your 2 guest drinks.')).toBeVisible()
    await user.click(screen.getByRole('button', { name: 'Place order' }))

    await waitFor(() => expect(sent.use_guest_credit).toBe(true))
  })

  it.each([
    [
      'no pass',
      { 'GET /subscriptions/me': () => fail(404, 'NO_ACTIVE_SUBSCRIPTION') },
      /need a pass/i,
    ],
    [
      'paused pass',
      { 'GET /subscriptions/me': () => ok({ ...PASS, status: 'PAUSED' }) },
      /is paused/i,
    ],
    [
      'closed shop',
      { 'GET /shops/shop-1': () => ok({ ...SHOP, is_open_now: false }) },
      /closed right now/i,
    ],
  ])('explains why ordering is not possible: %s', async (_, overrides, message) => {
    mockApi(builderApi(overrides))
    renderApp('/shops/shop-1/order/latte')

    expect(await screen.findByText(message)).toBeVisible()
    expect(screen.getByRole('button', { name: 'Place order' })).toBeDisabled()
  })

  it('blocks ordering without drinks left and links to an upgrade', async () => {
    mockApi(builderApi({ 'GET /subscriptions/me': () => ok({ ...PASS, remaining_credits: 0 }) }))
    renderApp('/shops/shop-1/order/latte')

    expect(await screen.findByText(/no drinks left this month/i)).toBeVisible()
    expect(screen.getByRole('link', { name: /upgrade your pass/i })).toHaveAttribute(
      'href',
      '/pass',
    )
    expect(screen.getByRole('button', { name: 'Place order' })).toBeDisabled()
  })

  it('shows errors from the API', async () => {
    const user = userEvent.setup()
    mockApi(
      builderApi({
        'POST /orders': () => fail(409, 'SHOP_CLOSED', 'This shop is closed right now.'),
      }),
    )
    renderApp('/shops/shop-1/order/latte')

    await user.click(await screen.findByRole('button', { name: 'Place order' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('This shop is closed right now.')
  })
})

describe('order page', () => {
  it('shows progress, details and the pickup QR code', async () => {
    mockApi({ 'GET /orders/order-1': () => ok(order({ status: 'PREPARING', is_priority: true })) })
    renderApp('/orders/order-1')

    expect(await screen.findByRole('heading', { name: /being made/i })).toBeVisible()
    const progress = screen.getByRole('list', { name: /order progress/i })
    expect(within(progress).getByText('Preparing').closest('li')).toHaveAttribute(
      'aria-current',
      'step',
    )
    expect(screen.getByRole('img', { name: /pickup qr code/i })).toBeVisible()
    expect(screen.getByText('Large · Oat milk · 1 sugar · 1 extra shot')).toBeVisible()
    expect(screen.getByText('Priority pickup')).toBeVisible()
    expect(screen.queryByRole('button', { name: /cancel order/i })).toBeNull()
  })

  it('cancels a pending order after confirmation', async () => {
    const user = userEvent.setup()
    mockApi({
      'GET /orders/order-1': () => ok(order()),
      'POST /orders/order-1/cancel': () => ok(order({ status: 'CANCELLED', qr_payload: null })),
      'GET /orders/history': () => ok({ items: [], total: 0, limit: 10, offset: 0 }),
      'GET /subscriptions/me': () => ok(PASS),
    })
    renderApp('/orders/order-1')

    await user.click(await screen.findByRole('button', { name: /cancel order/i }))
    const dialog = screen.getByRole('dialog')
    expect(dialog).toHaveTextContent(/credit goes back/i)
    await user.click(within(dialog).getByRole('button', { name: /cancel order/i }))

    expect(await screen.findByRole('heading', { name: /was cancelled/i })).toBeVisible()
    expect(screen.queryByRole('img', { name: /qr code/i })).toBeNull()
  })

  it('reorders a completed drink', async () => {
    const user = userEvent.setup()
    mockApi({
      'GET /orders/order-1': () =>
        ok(order({ status: 'COMPLETED', qr_payload: null, completed_at: '2026-11-21T10:10:00Z' })),
      'POST /orders/order-1/reorder': () => ok(order({ id: 'order-2' })),
      'GET /orders/order-2': () => ok(order({ id: 'order-2' })),
      'GET /orders/history': () => ok({ items: [], total: 0, limit: 10, offset: 0 }),
      'GET /subscriptions/me': () => ok(PASS),
    })
    const { router } = renderApp('/orders/order-1')

    expect(await screen.findByRole('heading', { name: /enjoy your coffee/i })).toBeVisible()
    await user.click(screen.getByRole('button', { name: /order again/i }))

    await waitFor(() => expect(router.state.location.pathname).toBe('/orders/order-2'))
  })
})

describe('order history', () => {
  it('lists orders, toggles favourites and filters them', async () => {
    const user = userEvent.setup()
    const favourites = new Set<string>()
    mockApi({
      'GET /orders/history': ({ url }) => {
        const all = [
          order({ id: 'o2', status: 'COMPLETED', product_name: 'Flat White' }),
          order({ id: 'o1' }),
        ].map((o) => ({ ...o, is_favorite: favourites.has(o.id) }))
        const items =
          url.searchParams.get('favorites') === 'true' ? all.filter((o) => o.is_favorite) : all
        return ok({ items, total: items.length, limit: 10, offset: 0 })
      },
      'PATCH /orders/o2/favorite': ({ body }) => {
        if ((body as { is_favorite: boolean }).is_favorite) favourites.add('o2')
        return ok(order({ id: 'o2', is_favorite: true }))
      },
    })
    renderApp('/orders')

    const rows = await screen.findAllByRole('listitem')
    expect(rows[0]).toHaveTextContent('Flat White')
    expect(within(rows[0]).getByRole('button', { name: /order flat white again/i })).toBeVisible()
    expect(within(rows[1]).queryByRole('button', { name: /again/i })).toBeNull() // still active

    await user.click(within(rows[0]).getByRole('button', { name: /add flat white to favourites/i }))
    await user.click(screen.getByRole('button', { name: 'Favourites' }))

    await waitFor(() => expect(screen.getAllByRole('listitem')).toHaveLength(1))
    expect(screen.getByRole('listitem')).toHaveTextContent('Flat White')
  })

  it('loads more orders', async () => {
    const user = userEvent.setup()
    mockApi({
      'GET /orders/history': ({ url }) => {
        const limit = Number(url.searchParams.get('limit'))
        const items = Array.from({ length: Math.min(limit, 12) }, (_, i) => order({ id: `o${i}` }))
        return ok({ items, total: 12, limit, offset: 0 })
      },
    })
    renderApp('/orders')

    expect(await screen.findAllByRole('listitem')).toHaveLength(10)
    await user.click(screen.getByRole('button', { name: /show more/i }))

    await waitFor(() => expect(screen.getAllByRole('listitem')).toHaveLength(12))
    expect(screen.queryByRole('button', { name: /show more/i })).toBeNull()
  })

  it('has empty states', async () => {
    mockApi({ 'GET /orders/history': () => ok({ items: [], total: 0, limit: 10, offset: 0 }) })
    renderApp('/orders')

    expect(await screen.findByRole('heading', { name: /no orders yet/i })).toBeVisible()
    expect(screen.getByRole('link', { name: /find a café/i })).toBeVisible()
  })
})
