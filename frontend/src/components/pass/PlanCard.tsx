import { Check } from 'lucide-react'
import type { ReactNode } from 'react'

import type { Plan } from '../../api/subscriptions'
import { formatPrice } from '../../lib/format'
import { planPerks } from '../../lib/plans'
import styles from './PlanCard.module.css'

interface PlanCardProps {
  plan: Plan
  highlight?: string
  current?: boolean
  action?: ReactNode
}

export function PlanCard({ plan, highlight, current, action }: PlanCardProps) {
  return (
    <article
      className={[styles.card, highlight && styles.highlight, current && styles.current]
        .filter(Boolean)
        .join(' ')}
      aria-labelledby={`plan-${plan.code}`}
    >
      {highlight && <span className={styles.ribbon}>{highlight}</span>}
      <h3 id={`plan-${plan.code}`} className={styles.name}>
        {plan.name}
      </h3>
      <p className={styles.price}>
        <span className={styles.amount}>{formatPrice(plan.price)}</span>
        <span className={styles.per}> / month</span>
      </p>
      <ul className={styles.perks}>
        {planPerks(plan).map((perk) => (
          <li key={perk}>
            <Check size={16} aria-hidden className={styles.check} /> {perk}
          </li>
        ))}
      </ul>
      {action && <div className={styles.action}>{action}</div>}
    </article>
  )
}
