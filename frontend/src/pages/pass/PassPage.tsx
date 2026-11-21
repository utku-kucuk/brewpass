import { Link } from 'react-router'

import { PassOverview } from '../../components/pass/PassOverview'
import { PlanCard } from '../../components/pass/PlanCard'
import { ErrorState, LoadingState } from '../../components/ui/StateMessage'
import { useDocumentTitle } from '../../hooks/useDocumentTitle'
import { useMySubscription, usePlans } from '../../hooks/usePass'
import styles from './Pass.module.css'

export function PassPage() {
  const subscription = useMySubscription()
  const plans = usePlans()
  useDocumentTitle(subscription.data ? 'Your pass' : 'Choose a pass')

  if (subscription.isPending || plans.isPending) return <LoadingState label="Loading passes…" />
  if (subscription.isError) {
    return <ErrorState error={subscription.error} onRetry={() => void subscription.refetch()} />
  }
  if (plans.isError) return <ErrorState error={plans.error} onRetry={() => void plans.refetch()} />

  if (subscription.data) return <PassOverview subscription={subscription.data} plans={plans.data} />

  return (
    <div>
      <h1>Choose your pass</h1>
      <p className={styles.lead}>
        One monthly price, coffee at every partner café. Change or cancel any time.
      </p>
      <div className={styles.plans}>
        {plans.data.map((plan) => (
          <PlanCard
            key={plan.code}
            plan={plan}
            highlight={plan.code === 'DAILY' ? 'Most popular' : undefined}
            action={
              <Link className={styles.choose} to={`/pass/checkout?plan=${plan.code}`}>
                Choose {plan.name}
              </Link>
            }
          />
        ))}
      </div>
    </div>
  )
}
