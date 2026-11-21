import { Heart } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router'

import { isActive } from '../../api/orders'
import { StatusBadge } from '../../components/orders/OrderStatus'
import { Button } from '../../components/ui/Button'
import { EmptyState, ErrorState, LoadingState } from '../../components/ui/StateMessage'
import { useDocumentTitle } from '../../hooks/useDocumentTitle'
import { useFavorite, useOrderHistory, useReorder } from '../../hooks/useOrders'
import { errorMessage } from '../../lib/errors'
import { describeDrink, formatDateTime } from '../../lib/format'
import styles from './Orders.module.css'

const PAGE = 10

export function OrdersPage() {
  useDocumentTitle('Your orders')
  const navigate = useNavigate()
  const [favorites, setFavorites] = useState(false)
  const [limit, setLimit] = useState(PAGE)
  const history = useOrderHistory(favorites, limit)
  const favorite = useFavorite()
  const again = useReorder()

  function showFavorites(value: boolean) {
    setFavorites(value)
    setLimit(PAGE)
  }

  const items = history.data?.items ?? []

  return (
    <div className={styles.history}>
      <h1>Your orders</h1>
      <div className={styles.tabs} role="group" aria-label="Show">
        <button type="button" aria-pressed={!favorites} onClick={() => showFavorites(false)}>
          All
        </button>
        <button type="button" aria-pressed={favorites} onClick={() => showFavorites(true)}>
          Favourites
        </button>
      </div>

      {(favorite.isError || again.isError) && (
        <p className={styles.errorText} role="alert">
          {errorMessage(favorite.error ?? again.error)}
        </p>
      )}

      {history.isPending && <LoadingState label="Loading orders…" />}
      {history.isError && (
        <ErrorState error={history.error} onRetry={() => void history.refetch()} />
      )}
      {history.isSuccess && items.length === 0 && (
        <EmptyState
          title={favorites ? 'No favourites yet' : 'No orders yet'}
          description={
            favorites
              ? 'Tap the heart on an order to find it here and reorder in one tap.'
              : 'Your first cup is a few taps away.'
          }
          action={<Link to="/shops">Find a café</Link>}
        />
      )}

      {items.length > 0 && (
        <ul className={styles.orderList}>
          {items.map((order) => (
            <li key={order.id} className={styles.orderRow}>
              <Link to={`/orders/${order.id}`} className={styles.orderLink}>
                <span className={styles.orderTitle}>{order.product_name}</span>
                <span className={styles.muted}>
                  {order.shop_name} · {describeDrink(order)}
                </span>
                <span className={styles.muted}>{formatDateTime(order.created_at)}</span>
              </Link>
              <div className={styles.rowActions}>
                <StatusBadge status={order.status} />
                <button
                  type="button"
                  className={styles.heart}
                  aria-pressed={order.is_favorite}
                  aria-label={`${order.is_favorite ? 'Remove' : 'Add'} ${order.product_name} ${order.is_favorite ? 'from' : 'to'} favourites`}
                  onClick={() => favorite.mutate({ id: order.id, value: !order.is_favorite })}
                >
                  <Heart size={18} aria-hidden fill={order.is_favorite ? 'currentColor' : 'none'} />
                </button>
                {!isActive(order) && (
                  <Button
                    variant="secondary"
                    onClick={() =>
                      again.mutate(order.id, {
                        onSuccess: (next) => navigate(`/orders/${next.id}`),
                      })
                    }
                    aria-label={`Order ${order.product_name} again`}
                  >
                    Reorder
                  </Button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {history.data && history.data.total > items.length && (
        <Button
          variant="secondary"
          loading={history.isFetching}
          onClick={() => setLimit((current) => current + PAGE)}
        >
          Show more
        </Button>
      )}
    </div>
  )
}
