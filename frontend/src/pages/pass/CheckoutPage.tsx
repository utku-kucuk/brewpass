import { CheckCircle2 } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link, Navigate, useSearchParams } from 'react-router'

import type { PlanCode, Subscription } from '../../api/subscriptions'
import { CardFields } from '../../components/pass/CardFields'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { ErrorState, LoadingState } from '../../components/ui/StateMessage'
import { useDocumentTitle } from '../../hooks/useDocumentTitle'
import { useMySubscription, usePlans, useSubscribe } from '../../hooks/usePass'
import { EMPTY_CARD, validateCard, type CardErrors } from '../../lib/card'
import { errorMessage } from '../../lib/errors'
import { formatDate, formatPrice } from '../../lib/format'
import { planPerks } from '../../lib/plans'
import styles from './Pass.module.css'

function Success({ subscription }: { subscription: Subscription }) {
  return (
    <div className={styles.success} role="status">
      <CheckCircle2 size={48} className={styles.successIcon} aria-hidden />
      <h1>You're all set</h1>
      <p>
        Your {subscription.plan.name} pass is active until{' '}
        {formatDate(subscription.current_period_end)} and renews automatically.
      </p>
      {subscription.payment_transaction_id && (
        <p className={styles.muted}>
          Transaction <span className={styles.mono}>{subscription.payment_transaction_id}</span>
        </p>
      )}
      <div className={styles.actions}>
        <Link to="/shops">Find a café</Link>
        <Link to="/pass">View your pass</Link>
      </div>
    </div>
  )
}

export function CheckoutPage() {
  useDocumentTitle('Checkout')
  const [params] = useSearchParams()
  const code = params.get('plan') as PlanCode | null
  const plans = usePlans()
  const current = useMySubscription()
  const buy = useSubscribe()
  const [card, setCard] = useState(EMPTY_CARD)
  const [errors, setErrors] = useState<CardErrors>({})

  if (buy.isSuccess) return <Success subscription={buy.data} />
  if (plans.isPending || current.isPending) return <LoadingState />
  if (plans.isError) return <ErrorState error={plans.error} onRetry={() => void plans.refetch()} />
  // Members who already have a pass manage it on /pass.
  if (current.data) return <Navigate to="/pass" replace />

  const plan = plans.data.find((p) => p.code === code)
  if (!plan) return <Navigate to="/pass" replace />

  function submit(event: FormEvent) {
    event.preventDefault()
    const result = validateCard(card)
    setErrors(result.errors)
    if (result.card && plan) buy.mutate({ plan: plan.code, card: result.card })
  }

  return (
    <div className={styles.checkout}>
      <Card>
        <h1>{plan.name} pass</h1>
        <ul className={styles.muted}>
          {planPerks(plan).map((perk) => (
            <li key={perk}>{perk}</li>
          ))}
        </ul>
        <div className={[styles.summaryRow, styles.total].join(' ')}>
          <span>Due today</span>
          <span>{formatPrice(plan.price)}</span>
        </div>
        <p className={styles.muted}>Then {formatPrice(plan.price)} every month. Cancel any time.</p>
        <Link to="/pass">Choose a different pass</Link>
      </Card>

      <Card>
        <form onSubmit={submit} noValidate aria-label="Payment">
          <CardFields value={card} errors={errors} onChange={setCard} />
          {buy.isError && (
            <p className={styles.formError} role="alert">
              {errorMessage(buy.error)}
            </p>
          )}
          <Button type="submit" fullWidth loading={buy.isPending}>
            Pay {formatPrice(plan.price)}
          </Button>
          <p className={styles.muted}>
            Payments are processed by BrewPass Pay (demo). Card numbers are never stored.
          </p>
        </form>
      </Card>
    </div>
  )
}
