import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { List, Map as MapIcon, Search } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router'

import { searchShops, type ShopSearch } from '../../api/shops'
import { ShopCard } from '../../components/shops/ShopCard'
import { ShopMap } from '../../components/shops/ShopMap'
import { EmptyState, ErrorState, LoadingState } from '../../components/ui/StateMessage'
import { useDocumentTitle } from '../../hooks/useDocumentTitle'
import { useGeolocation } from '../../hooks/useGeolocation'
import styles from './ShopsPage.module.css'

const RADII_KM = [1, 3, 5, 10]
const RATINGS = ['4.0', '4.5']

export function ShopsPage() {
  useDocumentTitle('Find a café')
  const location = useGeolocation()
  const [params, setParams] = useSearchParams()
  const [hovered, setHovered] = useState<string | null>(null)

  const q = params.get('q') ?? ''
  const openNow = params.get('open') === '1'
  const minRating = params.get('rating')
  const radiusKm = Number(params.get('radius') ?? 3)
  const view = params.get('view') === 'map' ? 'map' : 'list'

  const [search, setSearch] = useState(q)
  useEffect(() => setSearch(q), [q])

  function update(changes: Record<string, string | null>) {
    setParams(
      (current) => {
        const next = new URLSearchParams(current)
        for (const [key, value] of Object.entries(changes)) {
          if (value === null || value === '') next.delete(key)
          else next.set(key, value)
        }
        return next
      },
      { replace: true },
    )
  }

  // Debounce typing into the search box.
  useEffect(() => {
    const handle = setTimeout(() => {
      if (search.trim() !== q) update({ q: search.trim() || null })
    }, 300)
    return () => clearTimeout(handle)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search])

  const query: ShopSearch = {
    ...(location.coords && { ...location.coords, radius: radiusKm * 1000 }),
    q: q || undefined,
    open_now: openNow || undefined,
    min_rating: minRating ? Number(minRating) : undefined,
    limit: 50,
  }

  const shops = useQuery({
    queryKey: ['shops', query],
    queryFn: ({ signal }) => searchShops(query, signal),
    enabled: location.status !== 'pending',
    placeholderData: keepPreviousData,
  })

  const items = shops.data?.items ?? []
  const hasFilters = Boolean(q || openNow || minRating)

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1>Find a café</h1>
        <p className={styles.locationNote} role="status">
          {location.status === 'pending' && 'Finding cafés near you…'}
          {location.status === 'granted' && `Partner cafés within ${radiusKm} km of you.`}
          {(location.status === 'denied' || location.status === 'unavailable') &&
            'Location is off, so we show the top-rated cafés. Allow location to see what is near you.'}
        </p>
      </header>

      <form
        className={styles.filters}
        role="search"
        aria-label="Filter cafés"
        onSubmit={(event) => event.preventDefault()}
      >
        <label className={styles.searchBox}>
          <Search size={18} aria-hidden />
          <span className="visually-hidden">Search by name or address</span>
          <input
            type="search"
            placeholder="Search by name or address"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>

        <label className={styles.toggle}>
          <input
            type="checkbox"
            checked={openNow}
            onChange={(event) => update({ open: event.target.checked ? '1' : null })}
          />
          Open now
        </label>

        <label className={styles.select}>
          <span>Rating</span>
          <select
            value={minRating ?? ''}
            onChange={(event) => update({ rating: event.target.value || null })}
          >
            <option value="">Any</option>
            {RATINGS.map((rating) => (
              <option key={rating} value={rating}>
                {rating}+
              </option>
            ))}
          </select>
        </label>

        {location.coords && (
          <label className={styles.select}>
            <span>Within</span>
            <select value={radiusKm} onChange={(event) => update({ radius: event.target.value })}>
              {RADII_KM.map((km) => (
                <option key={km} value={km}>
                  {km} km
                </option>
              ))}
            </select>
          </label>
        )}
      </form>

      <div className={styles.viewSwitch} role="group" aria-label="View">
        <button type="button" aria-pressed={view === 'list'} onClick={() => update({ view: null })}>
          <List size={18} aria-hidden /> List
        </button>
        <button type="button" aria-pressed={view === 'map'} onClick={() => update({ view: 'map' })}>
          <MapIcon size={18} aria-hidden /> Map
        </button>
      </div>

      <div className={styles.layout} data-view={view}>
        <section className={styles.results} aria-labelledby="results-heading">
          <h2 id="results-heading" className={styles.count}>
            {shops.data
              ? `${shops.data.total} ${shops.data.total === 1 ? 'café' : 'cafés'}`
              : 'Cafés'}
          </h2>
          {(location.status === 'pending' || shops.isPending) && (
            <LoadingState label="Looking for cafés…" />
          )}
          {shops.isError && <ErrorState error={shops.error} onRetry={() => void shops.refetch()} />}
          {shops.isSuccess && items.length === 0 && (
            <EmptyState
              title="No cafés match"
              description={
                hasFilters
                  ? 'Try clearing a filter or searching for something else.'
                  : 'There are no partner cafés in this area yet. Try a larger distance.'
              }
            />
          )}
          {items.length > 0 && (
            <ul className={styles.list} aria-busy={shops.isFetching}>
              {items.map((shop) => (
                <ShopCard
                  key={shop.id}
                  shop={shop}
                  selected={hovered === shop.id}
                  onHover={setHovered}
                />
              ))}
            </ul>
          )}
        </section>

        <ShopMap
          className={styles.map}
          shops={items}
          userLocation={location.coords}
          selectedId={hovered}
        />
      </div>
    </div>
  )
}
