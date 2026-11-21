import { CreditCard } from 'lucide-react'

import { formatCardNumber, formatExpiry, type CardErrors, type CardForm } from '../../lib/card'
import { TextField } from '../ui/TextField'
import styles from './CardFields.module.css'

interface CardFieldsProps {
  value: CardForm
  errors: CardErrors
  onChange: (value: CardForm) => void
}

/** Card inputs with browser autofill hints. Values are never persisted. */
export function CardFields({ value, errors, onChange }: CardFieldsProps) {
  const set = (field: keyof CardForm, next: string) => onChange({ ...value, [field]: next })

  return (
    <fieldset className={styles.fieldset}>
      <legend className={styles.legend}>
        <CreditCard size={18} aria-hidden /> Card details
      </legend>
      <TextField
        label="Card number"
        name="cc-number"
        autoComplete="cc-number"
        inputMode="numeric"
        placeholder="4242 4242 4242 4242"
        value={value.number}
        onChange={(event) => set('number', formatCardNumber(event.target.value))}
        error={errors.number}
      />
      <div className={styles.row}>
        <TextField
          label="Expiry"
          name="cc-exp"
          autoComplete="cc-exp"
          inputMode="numeric"
          placeholder="MM / YY"
          value={value.expiry}
          onChange={(event) => set('expiry', formatExpiry(event.target.value))}
          error={errors.expiry}
        />
        <TextField
          label="CVC"
          name="cc-csc"
          autoComplete="cc-csc"
          inputMode="numeric"
          maxLength={4}
          placeholder="123"
          value={value.cvc}
          onChange={(event) => set('cvc', event.target.value.replace(/\D/g, ''))}
          error={errors.cvc}
        />
      </div>
      <TextField
        label="Name on card"
        name="cc-name"
        autoComplete="cc-name"
        value={value.name}
        onChange={(event) => set('name', event.target.value)}
        error={errors.name}
      />
      <p className={styles.testCards}>
        BrewPass Pay test cards: <code>4242 4242 4242 4242</code> is approved,{' '}
        <code>4000 0000 0000 0002</code> is declined. Any future expiry and CVC work.
      </p>
    </fieldset>
  )
}
