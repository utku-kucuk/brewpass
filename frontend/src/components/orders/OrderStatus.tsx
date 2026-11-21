import { Check } from 'lucide-react'

import type { OrderStatus } from '../../api/orders'
import { STATUS_LABELS } from '../../lib/format'
import styles from './OrderStatus.module.css'

export function StatusBadge({ status }: { status: OrderStatus }) {
  return (
    <span className={styles.badge} data-status={status}>
      {STATUS_LABELS[status] ?? status}
    </span>
  )
}

const STEPS: OrderStatus[] = ['PENDING', 'ACCEPTED', 'PREPARING', 'READY', 'COMPLETED']

/** Progress through the pickup steps; the current step is announced as "current step". */
export function StatusTracker({ status }: { status: OrderStatus }) {
  if (status === 'CANCELLED') return null
  const current = STEPS.indexOf(status)
  return (
    <ol className={styles.tracker} aria-label="Order progress">
      {STEPS.map((step, index) => {
        const state = index < current ? 'done' : index === current ? 'current' : 'todo'
        return (
          <li
            key={step}
            className={styles.step}
            data-state={state}
            aria-current={state === 'current' ? 'step' : undefined}
          >
            <span className={styles.dot}>
              {state === 'done' ? <Check size={14} aria-hidden /> : index + 1}
            </span>
            <span className={styles.label}>{STATUS_LABELS[step]}</span>
          </li>
        )
      })}
    </ol>
  )
}
