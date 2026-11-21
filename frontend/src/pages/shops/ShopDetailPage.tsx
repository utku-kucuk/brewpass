import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Clock, MapPin, Phone } from 'lucide-react'
import { Link, useParams } from 'react-router'

import { getMenu, getShop, type MenuItem } from '../../api/shops'
import { OpenBadge, Rating } from '../../components/shops/ShopBits'
import { ShopMap } from '../../components/shops/ShopMap'
import { Card } from '../../components/ui/Card'
import { EmptyState, ErrorState, LoadingState } from '../../components/ui/StateMessage'
import { useDocumentTitle } from '../../hooks/useDocumentTitle'
import { useGeolocation } from '../../hooks/useGeolocation'
import { ApiError } from '../../lib/api'
import { CATEGORY_LABELS, formatDistance, formatHours, formatPrice } from '../../lib/format'
import styles from './ShopDetailPage.module.css'

function groupByCategory(items: MenuItem[]) {
  const groups = new Map<string, MenuItem[]>()
  for (const item of items) {
    groups.set(item.category, [...(groups.get(item.category) ?? []), item])
  }
  return [...groups.entries()]
}

function options(item: MenuItem): string {
  const parts = ['S / M / L']
  if (item.supports_milk) parts.push('milk options')
  if (item.supports_extra_shot) parts.push('extra shot')
  return parts.join(' · ')
}

export function ShopDetailPage() {
  const { shopId = '' } = useParams()
  const location = useGeolocation()

  const shop = useQuery({
    queryKey: ['shop', shopId, location.coords],
    queryFn: () => getShop(shopId, location.coords),
    enabled: location.status !== 'pending',
  })
  const menu = useQuery({ queryKey: ['menu', shopId], queryFn: () => getMenu(shopId) })
  useDocumentTitle(shop.data?.name ?? 'Café')

  if (location.status === 'pending' || shop.isPending) {
    return <LoadingState label="Loading café…" />
  }
  if (shop.isError) {
    const notFound = shop.error instanceof ApiError && shop.error.status === 404
    return notFound ? (
      <EmptyState
        title="Café not found"
        description="It may have closed or moved."
        action={<Link to="/shops">Back to cafés</Link>}
      />
    ) : (
      <ErrorState error={shop.error} onRetry={() => void shop.refetch()} />
    )
  }

  const data = shop.data
  const distance = formatDistance(data.distance_m)
  const todayIndex = data.today.weekday

  return (
    <article className={styles.page}>
      <Link to="/shops" className={styles.back}>
        <ArrowLeft size={16} aria-hidden /> All cafés
      </Link>

      <header className={styles.header}>
        <div>
          <h1>{data.name}</h1>
          <div className={styles.meta}>
            <OpenBadge open={data.is_open_now} />
            <Rating value={data.rating} />
            {distance && <span>{distance} away</span>}
          </div>
        </div>
      </header>

      <div className={styles.layout}>
        <div className={styles.main}>
          {data.description && <p className={styles.description}>{data.description}</p>}

          <section aria-labelledby="menu-heading">
            <h2 id="menu-heading">Menu</h2>
            <p className={styles.note}>Every drink costs one credit from your pass.</p>
            {menu.isPending && <LoadingState label="Loading menu…" />}
            {menu.isError && <ErrorState error={menu.error} onRetry={() => void menu.refetch()} />}
            {menu.isSuccess && menu.data.items.length === 0 && (
              <EmptyState title="The menu is being updated" />
            )}
            {menu.isSuccess &&
              groupByCategory(menu.data.items).map(([category, items]) => (
                <div key={category} className={styles.category}>
                  <h3>{CATEGORY_LABELS[category] ?? category}</h3>
                  <ul className={styles.menu}>
                    {items.map((item) => (
                      <li
                        key={item.id}
                        className={styles.item}
                        aria-disabled={!item.is_available || undefined}
                      >
                        <div>
                          <p className={styles.itemName}>
                            {item.name}
                            {!item.is_available && <span className={styles.soldOut}>Sold out</span>}
                          </p>
                          {item.description && (
                            <p className={styles.itemDescription}>{item.description}</p>
                          )}
                          <p className={styles.itemOptions}>{options(item)}</p>
                        </div>
                        <div className={styles.price}>
                          <span className={styles.credit}>1 credit</span>
                          <span className={styles.listPrice}>
                            {formatPrice(item.list_price)} at the counter
                          </span>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
          </section>
        </div>

        <aside className={styles.aside}>
          <Card>
            <h2 className={styles.asideTitle}>Visit</h2>
            <p className={styles.line}>
              <MapPin size={16} aria-hidden /> {data.address}, {data.city}
            </p>
            {data.phone_number && (
              <p className={styles.line}>
                <Phone size={16} aria-hidden />
                <a href={`tel:${data.phone_number}`}>{data.phone_number}</a>
              </p>
            )}
            <h3 className={styles.hoursTitle}>
              <Clock size={16} aria-hidden /> Opening hours
            </h3>
            <table className={styles.hours}>
              <tbody>
                {data.opening_hours.map((day) => (
                  <tr
                    key={day.weekday}
                    aria-current={day.weekday === todayIndex ? 'date' : undefined}
                  >
                    <th scope="row">{day.day}</th>
                    <td>{formatHours(day.opens_at, day.closes_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
          <ShopMap className={styles.map} shops={[data]} userLocation={location.coords} />
        </aside>
      </div>
    </article>
  )
}
