import { Star } from 'lucide-react'

import styles from './ShopBits.module.css'

export function OpenBadge({ open }: { open: boolean }) {
  return (
    <span className={[styles.badge, open ? styles.open : styles.closed].join(' ')}>
      {open ? 'Open now' : 'Closed'}
    </span>
  )
}

export function Rating({ value }: { value: string }) {
  return (
    <span className={styles.rating} aria-label={`Rated ${value} out of 5`}>
      <Star size={14} aria-hidden className={styles.star} />
      {value}
    </span>
  )
}
