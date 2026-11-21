import { Heart, RotateCcw } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'

import { isActive } from '../../api/orders'
import { StatusBadge, StatusTracker } from '../../components/orders/OrderStatus'
import { PickupCode } from '../../components/orders/PickupCode'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog'
import { EmptyState, ErrorState, LoadingState } from '../../components/ui/StateMessage'
import { useDocumentTitle } from '../../hooks/useDocumentTitle'
import { useCancelOrder, useFavorite, useOrder, useReorder } from '../../hooks/useOrders'
import { ApiError } from '../../lib/api'
import { errorMessage } from '../../lib/errors'
import { describeDrink, formatDateTime } from '../../lib/format'
import styles from './Orders.module.css'

const HEADLINES: Record<string, string> = {
  PENDING: 'Order sent — waiting for the café',
  ACCEPTED: 'The café has your order',
  PREPARING: 'Your drink is being made',
  READY: 'Ready! Show your code at the counter',
  COMPLETED: 'Enjoy your coffee',
  CANCELLED: 'This order was cancelled',
}

export function OrderPage() {
  const { orderId = '' } = useParams()
  const navigate = useNavigate()
  const order = useOrder(orderId)
  const cancel = useCancelOrder()
  const favorite = useFavorite()
  const again = useReorder()
  const [confirming, setConfirming] = useState(false)
  useDocumentTitle(order.data ? `${order.data.product_name} order` : 'Order')

  if (order.isPending) return <LoadingState label="Loading your order…" />
  if (order.isError) {
    return order.error instanceof ApiError && order.error.status === 404 ? (
      <EmptyState title="Order not found" action={<Link to="/orders">Your orders</Link>} />
    ) : (
      <ErrorState error={order.error} onRetry={() => void order.refetch()} />
    )
  }

  const data = order.data
  const active = isActive(data)

  return (
    <div className={styles.orderPage}>
      <header>
        <p className={styles.eyebrow}>
          {data.shop_name} · {formatDateTime(data.created_at)}
        </p>
        <h1 aria-live="polite">{HEADLINES[data.status]}</h1>
        <StatusBadge status={data.status} />
        {data.is_priority && active && <span className={styles.priority}>Priority pickup</span>}
      </header>

      <StatusTracker status={data.status} />

      <div className={styles.orderLayout}>
        {data.qr_payload && (
          <Card className={styles.codeCard}>
            <PickupCode payload={data.qr_payload} orderId={data.id} />
          </Card>
        )}

        <Card>
          <h2 className={styles.drinkName}>{data.product_name}</h2>
          <p>{describeDrink(data)}</p>
          {data.note && <p className={styles.muted}>Note: {data.note}</p>}
          {data.is_guest && <p className={styles.muted}>Paid with a guest drink.</p>}
          {data.completed_at && (
            <p className={styles.muted}>Picked up {formatDateTime(data.completed_at)}</p>
          )}

          {(cancel.isError || favorite.isError || again.isError) && (
            <p className={styles.errorText} role="alert">
              {errorMessage(cancel.error ?? favorite.error ?? again.error)}
            </p>
          )}

          <div className={styles.orderActions}>
            <Button
              variant="secondary"
              aria-pressed={data.is_favorite}
              icon={
                <Heart size={16} aria-hidden fill={data.is_favorite ? 'currentColor' : 'none'} />
              }
              onClick={() => favorite.mutate({ id: data.id, value: !data.is_favorite })}
              loading={favorite.isPending}
            >
              {data.is_favorite ? 'Favourite' : 'Add to favourites'}
            </Button>
            {!active && (
              <Button
                icon={<RotateCcw size={16} aria-hidden />}
                loading={again.isPending}
                onClick={() =>
                  again.mutate(data.id, { onSuccess: (next) => navigate(`/orders/${next.id}`) })
                }
              >
                Order again
              </Button>
            )}
            {data.status === 'PENDING' && (
              <Button variant="danger" onClick={() => setConfirming(true)}>
                Cancel order
              </Button>
            )}
          </div>
        </Card>
      </div>

      <ConfirmDialog
        open={confirming}
        title="Cancel this order?"
        confirmLabel="Cancel order"
        destructive
        loading={cancel.isPending}
        error={cancel.isError ? errorMessage(cancel.error) : undefined}
        onConfirm={() => cancel.mutate(data.id, { onSuccess: () => setConfirming(false) })}
        onCancel={() => {
          setConfirming(false)
          cancel.reset()
        }}
      >
        <p>The café hasn't started yet, so your drink credit goes back to your pass.</p>
      </ConfirmDialog>
    </div>
  )
}
