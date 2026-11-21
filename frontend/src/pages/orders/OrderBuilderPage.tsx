import { useQuery } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router'

import type { DrinkSize, MilkOption } from '../../api/orders'
import { getMenu, getShop } from '../../api/shops'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { ChoiceGroup } from '../../components/ui/ChoiceGroup'
import { EmptyState, ErrorState, LoadingState } from '../../components/ui/StateMessage'
import { useDocumentTitle } from '../../hooks/useDocumentTitle'
import { usePlaceOrder } from '../../hooks/useOrders'
import { useMySubscription } from '../../hooks/usePass'
import { errorMessage } from '../../lib/errors'
import { describeDrink, MILK_LABELS, SIZE_LABELS } from '../../lib/format'
import styles from './Orders.module.css'

const SIZES: DrinkSize[] = ['S', 'M', 'L']
const MILKS: MilkOption[] = ['NONE', 'WHOLE', 'SKIMMED', 'OAT', 'ALMOND', 'LACTOSE_FREE']
const COUNTS = [0, 1, 2, 3]

export function OrderBuilderPage() {
  const { shopId = '', productId = '' } = useParams()
  const navigate = useNavigate()
  const shop = useQuery({ queryKey: ['shop', shopId, null], queryFn: () => getShop(shopId) })
  const menu = useQuery({ queryKey: ['menu', shopId], queryFn: () => getMenu(shopId) })
  const pass = useMySubscription()
  const place = usePlaceOrder()

  const [size, setSize] = useState<DrinkSize>('M')
  const [milk, setMilk] = useState<MilkOption>('NONE')
  const [sugar, setSugar] = useState(0)
  const [shots, setShots] = useState(0)
  const [note, setNote] = useState('')
  const [guest, setGuest] = useState(false)

  const product = menu.data?.items.find((item) => item.id === productId)
  useDocumentTitle(product ? `Order ${product.name}` : 'Order')

  if (shop.isPending || menu.isPending || pass.isPending) return <LoadingState />
  for (const query of [shop, menu, pass]) {
    if (query.isError)
      return <ErrorState error={query.error} onRetry={() => void query.refetch()} />
  }
  if (!shop.data || !menu.data) return null
  if (!product) {
    return (
      <EmptyState
        title="Drink not found"
        action={<Link to={`/shops/${shopId}`}>Back to the menu</Link>}
      />
    )
  }

  const subscription = pass.data
  const blocker = !subscription
    ? { text: 'You need a pass to order.', link: '/pass', label: 'Choose a pass' }
    : subscription.status === 'PAUSED'
      ? { text: 'Your pass is paused.', link: '/pass', label: 'Resume your pass' }
      : !shop.data.is_open_now
        ? {
            text: `${shop.data.name} is closed right now.`,
            link: '/shops',
            label: 'Find an open café',
          }
        : !product.is_available
          ? {
              text: `${product.name} is sold out.`,
              link: `/shops/${shopId}`,
              label: 'Pick another drink',
            }
          : null

  const creditsLeft = subscription?.remaining_credits
  const guestLeft = subscription?.remaining_guest_credits ?? 0
  const outOfCredits = !guest && creditsLeft === 0

  function submit(event: FormEvent) {
    event.preventDefault()
    place.mutate(
      {
        product_id: productId,
        size,
        milk: product?.supports_milk ? milk : 'NONE',
        sugar,
        extra_shots: product?.supports_extra_shot ? shots : 0,
        note: note.trim() || null,
        use_guest_credit: guest,
      },
      { onSuccess: (order) => navigate(`/orders/${order.id}`) },
    )
  }

  return (
    <div className={styles.builder}>
      <Link to={`/shops/${shopId}`} className={styles.back}>
        <ArrowLeft size={16} aria-hidden /> {shop.data.name}
      </Link>
      <h1>{product.name}</h1>
      {product.description && <p className={styles.muted}>{product.description}</p>}

      {blocker && (
        <Card className={styles.blocker} role="status">
          <p>{blocker.text}</p>
          <Link to={blocker.link}>{blocker.label}</Link>
        </Card>
      )}

      <form onSubmit={submit} aria-label={`Customize ${product.name}`}>
        <ChoiceGroup
          legend="Size"
          value={size}
          onChange={setSize}
          options={SIZES.map((s) => ({ value: s, label: SIZE_LABELS[s] }))}
        />
        {product.supports_milk && (
          <ChoiceGroup
            legend="Milk"
            value={milk}
            onChange={setMilk}
            options={MILKS.map((m) => ({ value: m, label: MILK_LABELS[m] }))}
          />
        )}
        <ChoiceGroup
          legend="Sugar"
          value={sugar}
          onChange={setSugar}
          options={COUNTS.map((n) => ({ value: n, label: n === 0 ? 'None' : String(n) }))}
        />
        {product.supports_extra_shot && (
          <ChoiceGroup
            legend="Extra shots"
            value={shots}
            onChange={setShots}
            options={COUNTS.map((n) => ({ value: n, label: n === 0 ? 'None' : `+${n}` }))}
          />
        )}
        <label className={styles.noteLabel} htmlFor="order-note">
          Note for the barista (optional)
        </label>
        <textarea
          id="order-note"
          className={styles.note}
          maxLength={200}
          rows={2}
          value={note}
          onChange={(event) => setNote(event.target.value)}
        />

        {guestLeft > 0 && (
          <label className={styles.guest}>
            <input
              type="checkbox"
              checked={guest}
              onChange={(event) => setGuest(event.target.checked)}
            />
            Use a guest drink — treat a friend ({guestLeft} left)
          </label>
        )}

        <Card className={styles.summary}>
          <p className={styles.summaryDrink}>
            {product.name} ·{' '}
            {describeDrink({
              size,
              milk: product.supports_milk ? milk : 'NONE',
              sugar,
              extra_shots: product.supports_extra_shot ? shots : 0,
            })}
          </p>
          {subscription && (
            <p className={styles.muted}>
              {guest
                ? `Uses 1 of your ${guestLeft} guest drinks.`
                : creditsLeft === null
                  ? `Included in your ${subscription.plan.name} pass.`
                  : `Uses 1 of your ${creditsLeft} drinks left this month.`}
            </p>
          )}
          {outOfCredits && (
            <p className={styles.errorText}>
              No drinks left this month. <Link to="/pass">Upgrade your pass</Link>
            </p>
          )}
          {place.isError && (
            <p className={styles.errorText} role="alert">
              {errorMessage(place.error)}
            </p>
          )}
          <Button
            type="submit"
            fullWidth
            loading={place.isPending}
            disabled={Boolean(blocker) || outOfCredits}
          >
            Place order
          </Button>
        </Card>
      </form>
    </div>
  )
}
