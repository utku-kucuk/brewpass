import { MapPin } from 'lucide-react'
import { Link } from 'react-router'

import type { ShopSummary } from '../../api/shops'
import { formatDistance, formatHours } from '../../lib/format'
import styles from './ShopCard.module.css'
import { OpenBadge, Rating } from './ShopBits'

interface ShopCardProps {
  shop: ShopSummary
  selected?: boolean
  onHover?: (id: string | null) => void
}

export function ShopCard({ shop, selected, onHover }: ShopCardProps) {
  const distance = formatDistance(shop.distance_m)
  return (
    <li
      className={[styles.card, selected && styles.selected].filter(Boolean).join(' ')}
      onMouseEnter={() => onHover?.(shop.id)}
      onMouseLeave={() => onHover?.(null)}
    >
      <Link to={`/shops/${shop.id}`} className={styles.link}>
        <div className={styles.header}>
          <h3 className={styles.name}>{shop.name}</h3>
          <Rating value={shop.rating} />
        </div>
        <p className={styles.address}>
          <MapPin size={14} aria-hidden /> {shop.address}
        </p>
        <div className={styles.meta}>
          <OpenBadge open={shop.is_open_now} />
          <span>Today {formatHours(shop.today.opens_at, shop.today.closes_at)}</span>
          {distance && <span className={styles.distance}>{distance}</span>}
        </div>
      </Link>
    </li>
  )
}
