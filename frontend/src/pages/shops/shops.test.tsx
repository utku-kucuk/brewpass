import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { ShopDetail, ShopSummary } from '../../api/shops'
import { fail, mockApi, ok, renderApp, signInAs } from '../../test/utils'

// Leaflet needs a real browser layout; the list and filters are what we test here.
vi.mock('../../components/shops/ShopMap', () => ({
  ShopMap: ({ shops }: { shops: ShopSummary[] }) => (
    <div data-testid="map">{shops.map((s) => s.name).join(', ')}</div>
  ),
}))

const today = { weekday: 2, day: 'Wednesday', opens_at: '07:30:00', closes_at: '21:00:00' }

const shop = (overrides: Partial<ShopSummary> = {}): ShopSummary => ({
  id: 'shop-1',
  name: 'Karaköy Brew Lab',
  address: 'Kemankeş Karamustafa Paşa Mah. No:18',
  city: 'Istanbul',
  location: { lat: 41.02445, lng: 28.9772 },
  rating: '4.6',
  photo_url: null,
  distance_m: 640,
  is_open_now: true,
  today,
  ...overrides,
})

function mockLocation(result: 'granted' | 'denied') {
  vi.stubGlobal('navigator', {
    ...navigator,
    geolocation: {
      getCurrentPosition: (success: PositionCallback, error: PositionErrorCallback) =>
        result === 'granted'
          ? success({ coords: { latitude: 41.0222, longitude: 28.9765 } } as GeolocationPosition)
          : error({ code: 1, PERMISSION_DENIED: 1 } as GeolocationPositionError),
    },
  })
}

beforeEach(() => signInAs())

describe('shops page', () => {
  it('lists nearby cafés with distance and hours', async () => {
    mockLocation('granted')
    const fetchMock = mockApi({
      'GET /shops': () =>
        ok({
          items: [
            shop(),
            shop({ id: 'shop-2', name: 'Moda Roastery', distance_m: 4850, is_open_now: false }),
          ],
          total: 2,
          limit: 50,
          offset: 0,
        }),
    })
    renderApp('/shops')

    const list = await screen.findByRole('list')
    const cards = within(list).getAllByRole('listitem')
    expect(cards).toHaveLength(2)
    expect(cards[0]).toHaveTextContent('Karaköy Brew Lab')
    expect(cards[0]).toHaveTextContent('640 m')
    expect(cards[0]).toHaveTextContent('Open now')
    expect(cards[0]).toHaveTextContent('Today 07:30–21:00')
    expect(cards[1]).toHaveTextContent('4.9 km')
    expect(cards[1]).toHaveTextContent('Closed')
    expect(screen.getByRole('heading', { name: '2 cafés' })).toBeVisible()
    expect(screen.getByText(/within 3 km of you/i)).toBeVisible()

    const url = new URL(String(fetchMock.mock.calls[0][0]), 'http://localhost')
    expect(Object.fromEntries(url.searchParams)).toMatchObject({
      lat: '41.0222',
      lng: '28.9765',
      radius: '3000',
    })
  })

  it('works without location and explains why', async () => {
    mockLocation('denied')
    const fetchMock = mockApi({
      'GET /shops': () =>
        ok({ items: [shop({ distance_m: null })], total: 1, limit: 50, offset: 0 }),
    })
    renderApp('/shops')

    expect(await screen.findByText(/location is off/i)).toBeVisible()
    expect(await screen.findByRole('heading', { name: '1 café' })).toBeVisible()
    expect(String(fetchMock.mock.calls[0][0])).not.toContain('lat=')
    expect(screen.queryByLabelText(/within/i)).toBeNull()
  })

  it('applies search and filters and keeps them in the URL', async () => {
    const user = userEvent.setup()
    mockLocation('granted')
    const seen: URLSearchParams[] = []
    mockApi({
      'GET /shops': ({ url }) => {
        seen.push(url.searchParams)
        return ok({ items: [shop()], total: 1, limit: 50, offset: 0 })
      },
    })
    const { router } = renderApp('/shops')
    await screen.findByRole('heading', { name: '1 café' })

    await user.click(screen.getByLabelText(/open now/i))
    await user.selectOptions(screen.getByLabelText(/rating/i), '4.5')
    await user.selectOptions(screen.getByLabelText(/within/i), '10')
    await user.type(screen.getByRole('searchbox'), 'brew')

    await waitFor(() => expect(seen[seen.length - 1]?.get('q')).toBe('brew'))
    const last = seen[seen.length - 1]
    expect(last.get('open_now')).toBe('true')
    expect(last.get('min_rating')).toBe('4.5')
    expect(last.get('radius')).toBe('10000')
    expect(router.state.location.search).toContain('open=1')
    expect(router.state.location.search).toContain('rating=4.5')
  })

  it('shows an empty state when nothing matches', async () => {
    mockLocation('denied')
    mockApi({ 'GET /shops': () => ok({ items: [], total: 0, limit: 50, offset: 0 }) })
    renderApp('/shops?q=zzz')

    expect(await screen.findByRole('heading', { name: /no cafés match/i })).toBeVisible()
    expect(screen.getByText(/clearing a filter/i)).toBeVisible()
  })

  it('switches between list and map on small screens', async () => {
    const user = userEvent.setup()
    mockLocation('denied')
    mockApi({ 'GET /shops': () => ok({ items: [shop()], total: 1, limit: 50, offset: 0 }) })
    const { router } = renderApp('/shops')
    await screen.findByRole('heading', { name: '1 café' })

    await user.click(screen.getByRole('button', { name: /map/i }))

    expect(screen.getByRole('button', { name: /map/i })).toHaveAttribute('aria-pressed', 'true')
    expect(router.state.location.search).toBe('?view=map')
    expect(screen.getByTestId('map')).toHaveTextContent('Karaköy Brew Lab')
  })
})

describe('shop detail page', () => {
  const detail: ShopDetail = {
    ...shop(),
    description: 'Specialty coffee bar with cold brew on tap.',
    phone_number: null,
    opening_hours: [
      { weekday: 0, day: 'Monday', opens_at: '07:30:00', closes_at: '21:00:00' },
      { ...today },
      { weekday: 6, day: 'Sunday', opens_at: null, closes_at: null },
    ],
  }

  it('shows hours, distance and the menu grouped by category', async () => {
    mockLocation('granted')
    mockApi({
      'GET /shops/shop-1': () => ok(detail),
      'GET /shops/shop-1/menu': () =>
        ok({
          shop_id: 'shop-1',
          shop_name: 'Karaköy Brew Lab',
          items: [
            {
              id: 'p1',
              name: 'Cold Brew',
              description: 'Steeped for 18 hours.',
              category: 'COLD_COFFEE',
              list_price: '95.00',
              supports_milk: true,
              supports_extra_shot: true,
              image_url: null,
              is_available: false,
            },
            {
              id: 'p2',
              name: 'Flat White',
              description: null,
              category: 'HOT_COFFEE',
              list_price: '95.00',
              supports_milk: true,
              supports_extra_shot: true,
              image_url: null,
              is_available: true,
            },
          ],
        }),
    })
    renderApp('/shops/shop-1')

    expect(await screen.findByRole('heading', { name: 'Karaköy Brew Lab', level: 1 })).toBeVisible()
    expect(screen.getByText('640 m away')).toBeVisible()
    expect(screen.getByRole('row', { name: /wednesday/i })).toHaveAttribute('aria-current', 'date')
    expect(screen.getByRole('row', { name: /sunday/i })).toHaveTextContent('Closed')

    expect(await screen.findByRole('heading', { name: 'Cold coffee' })).toBeVisible()
    expect(screen.getByRole('heading', { name: 'Hot coffee' })).toBeVisible()
    const coldBrew = screen.getByText('Cold Brew').closest('li')!
    expect(coldBrew).toHaveTextContent('Sold out')
    expect(coldBrew).toHaveAttribute('aria-disabled', 'true')
    expect(coldBrew).toHaveTextContent('1 credit')
  })

  it('shows a not-found state for unknown cafés', async () => {
    mockLocation('denied')
    mockApi({
      'GET /shops/missing': () => fail(404, 'SHOP_NOT_FOUND', 'Shop not found.'),
      'GET /shops/missing/menu': () => fail(404, 'SHOP_NOT_FOUND', 'Shop not found.'),
    })
    renderApp('/shops/missing')

    expect(await screen.findByRole('heading', { name: /café not found/i })).toBeVisible()
  })
})
