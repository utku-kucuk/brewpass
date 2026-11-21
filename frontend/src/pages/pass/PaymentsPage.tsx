import { Link } from 'react-router'

import { EmptyState, ErrorState, LoadingState } from '../../components/ui/StateMessage'
import { useDocumentTitle } from '../../hooks/useDocumentTitle'
import { usePayments } from '../../hooks/usePass'
import { describePayment, formatDateTime, formatPrice } from '../../lib/format'
import styles from './Pass.module.css'

export function PaymentsPage() {
  useDocumentTitle('Payment history')
  const payments = usePayments()

  return (
    <div style={{ maxWidth: '40rem', margin: '0 auto' }}>
      <h1>Payment history</h1>
      {payments.isPending && <LoadingState label="Loading payments…" />}
      {payments.isError && (
        <ErrorState error={payments.error} onRetry={() => void payments.refetch()} />
      )}
      {payments.isSuccess && payments.data.length === 0 && (
        <EmptyState
          title="No payments yet"
          description="Your BrewPass Pay receipts will show up here."
          action={<Link to="/pass">Choose a pass</Link>}
        />
      )}
      {payments.isSuccess && payments.data.length > 0 && (
        <ul className={styles.payments}>
          {payments.data.map((payment) => {
            const failed = payment.status === 'FAILED'
            return (
              <li
                key={payment.transaction_id}
                className={[styles.payment, failed && styles.failed].filter(Boolean).join(' ')}
              >
                <strong>{describePayment(payment.description)}</strong>
                <span className={styles.amount}>{formatPrice(payment.amount)}</span>
                <span className={styles.muted}>
                  {formatDateTime(payment.created_at)}
                  {payment.card_last4 && ` · card •••• ${payment.card_last4}`}
                  {failed && payment.failure_reason && ` · ${payment.failure_reason}`}
                </span>
                <span
                  className={[
                    styles.status,
                    failed ? styles.statusFailed : styles.statusSucceeded,
                  ].join(' ')}
                >
                  {failed ? 'Declined' : 'Paid'}
                </span>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
