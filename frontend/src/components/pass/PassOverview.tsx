import { AlertTriangle, CalendarClock, Gift, Receipt } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'

import type { Plan, PlanCode, Subscription } from '../../api/subscriptions'
import { useCancelPass, useChangePlan, useResume } from '../../hooks/usePass'
import { EMPTY_CARD, validateCard, type CardErrors } from '../../lib/card'
import { errorMessage } from '../../lib/errors'
import { formatDate, formatPrice } from '../../lib/format'
import { priceDifference } from '../../lib/plans'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import { ConfirmDialog } from '../ui/ConfirmDialog'
import { CardFields } from './CardFields'
import styles from './PassOverview.module.css'
import { PlanCard } from './PlanCard'

function Credits({ subscription }: { subscription: Subscription }) {
  const { plan, remaining_credits: remaining } = subscription
  if (remaining === null || plan.monthly_credits === null) {
    return <p className={styles.bigNumber}>Unlimited drinks</p>
  }
  return (
    <>
      <p className={styles.bigNumber}>
        {remaining} <span className={styles.of}>of {plan.monthly_credits} drinks left</span>
      </p>
      <div
        className={styles.meter}
        role="progressbar"
        aria-label="Drinks left this month"
        aria-valuemin={0}
        aria-valuemax={plan.monthly_credits}
        aria-valuenow={remaining}
      >
        <span style={{ width: `${Math.min(100, (remaining / plan.monthly_credits) * 100)}%` }} />
      </div>
    </>
  )
}

function ResumePanel() {
  const resume = useResume()
  const [useNewCard, setUseNewCard] = useState(false)
  const [card, setCard] = useState(EMPTY_CARD)
  const [errors, setErrors] = useState<CardErrors>({})

  function retryWithNewCard() {
    const result = validateCard(card)
    setErrors(result.errors)
    if (result.card) resume.mutate(result.card)
  }

  return (
    <Card className={styles.warning}>
      <h2 className={styles.warningTitle}>
        <AlertTriangle size={20} aria-hidden /> Your pass is paused
      </h2>
      <p>The monthly renewal was declined. Pay for a new month to keep ordering.</p>
      {resume.isError && (
        <p role="alert" className={styles.error}>
          {errorMessage(resume.error)}
        </p>
      )}
      {useNewCard ? (
        <>
          <CardFields value={card} errors={errors} onChange={setCard} />
          <Button onClick={retryWithNewCard} loading={resume.isPending}>
            Pay with this card
          </Button>
        </>
      ) : (
        <div className={styles.row}>
          <Button onClick={() => resume.mutate(undefined)} loading={resume.isPending}>
            Retry saved card
          </Button>
          <Button variant="secondary" onClick={() => setUseNewCard(true)}>
            Use another card
          </Button>
        </div>
      )}
    </Card>
  )
}

interface PassOverviewProps {
  subscription: Subscription
  plans: Plan[]
}

type Pending = { kind: 'change'; plan: Plan } | { kind: 'cancel' } | null

export function PassOverview({ subscription, plans }: PassOverviewProps) {
  const change = useChangePlan()
  const cancel = useCancelPass()
  const [pending, setPending] = useState<Pending>(null)
  const current = subscription.plan
  const paused = subscription.status === 'PAUSED'
  const renewal = formatDate(subscription.current_period_end)

  function close() {
    setPending(null)
    change.reset()
    cancel.reset()
  }

  function confirm() {
    if (pending?.kind === 'change') change.mutate(pending.plan.code, { onSuccess: close })
    if (pending?.kind === 'cancel') cancel.mutate(undefined, { onSuccess: close })
  }

  function keep(code: PlanCode) {
    change.mutate(code)
  }

  const target = pending?.kind === 'change' ? pending.plan : null
  const difference = target ? priceDifference(current, target) : 0

  return (
    <div className={styles.page}>
      <h1>Your pass</h1>
      {paused && <ResumePanel />}

      <Card className={styles.hero}>
        <p className={styles.planName}>{current.name} pass</p>
        <Credits subscription={subscription} />
        <ul className={styles.facts}>
          {subscription.remaining_guest_credits > 0 && (
            <li>
              <Gift size={16} aria-hidden /> {subscription.remaining_guest_credits} guest{' '}
              {subscription.remaining_guest_credits === 1 ? 'drink' : 'drinks'} left
            </li>
          )}
          <li>
            <CalendarClock size={16} aria-hidden />
            {paused
              ? `Paused since ${renewal}`
              : `Renews on ${renewal} for ${formatPrice(current.price)}`}
          </li>
        </ul>
        {subscription.pending_plan && (
          <div className={styles.pendingNote} role="status">
            <p>
              Switches to <strong>{subscription.pending_plan.name}</strong> on {renewal}.
            </p>
            <Button variant="ghost" onClick={() => keep(current.code)} loading={change.isPending}>
              Keep {current.name}
            </Button>
          </div>
        )}
      </Card>

      {!paused && (
        <section aria-labelledby="change-heading">
          <h2 id="change-heading">Change pass</h2>
          <div className={styles.plans}>
            {plans
              .filter((plan) => plan.code !== current.code)
              .map((plan) => {
                const upgrade = priceDifference(current, plan) > 0
                const scheduled = subscription.pending_plan?.code === plan.code
                return (
                  <PlanCard
                    key={plan.code}
                    plan={plan}
                    action={
                      <Button
                        variant={upgrade ? 'primary' : 'secondary'}
                        fullWidth
                        disabled={scheduled}
                        onClick={() => setPending({ kind: 'change', plan })}
                      >
                        {scheduled
                          ? `Starts ${renewal}`
                          : upgrade
                            ? `Upgrade to ${plan.name}`
                            : `Switch to ${plan.name}`}
                      </Button>
                    }
                  />
                )
              })}
          </div>
        </section>
      )}

      <div className={styles.footer}>
        <Link to="/payments" className={styles.footerLink}>
          <Receipt size={16} aria-hidden /> Payment history
        </Link>
        <Button variant="danger" onClick={() => setPending({ kind: 'cancel' })}>
          Cancel pass
        </Button>
      </div>

      <ConfirmDialog
        open={target !== null}
        title={difference > 0 ? `Upgrade to ${target?.name}?` : `Switch to ${target?.name}?`}
        confirmLabel={difference > 0 ? `Pay ${formatPrice(difference)}` : 'Switch at renewal'}
        loading={change.isPending}
        error={change.isError ? errorMessage(change.error) : undefined}
        onConfirm={confirm}
        onCancel={close}
      >
        {target && difference > 0 ? (
          <p>
            We'll charge {formatPrice(difference)} to your saved card now and add the extra drinks
            to this month. From {renewal} it's {formatPrice(target.price)} a month.
          </p>
        ) : (
          target && (
            <p>
              You keep {current.name} until {renewal}. After that you'll be on {target.name} for{' '}
              {formatPrice(target.price)} a month.
            </p>
          )
        )}
      </ConfirmDialog>

      <ConfirmDialog
        open={pending?.kind === 'cancel'}
        title="Cancel your pass?"
        confirmLabel="Cancel pass"
        destructive
        loading={cancel.isPending}
        error={cancel.isError ? errorMessage(cancel.error) : undefined}
        onConfirm={confirm}
        onCancel={close}
      >
        <p>
          Your pass ends right away. Drinks left this month are lost and there's no refund. You can
          buy a new pass any time.
        </p>
      </ConfirmDialog>
    </div>
  )
}
