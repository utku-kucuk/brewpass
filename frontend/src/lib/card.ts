import type { CardInput } from '../api/subscriptions'

export function luhnValid(digits: string): boolean {
  let sum = 0
  for (let i = 0; i < digits.length; i++) {
    let digit = Number(digits[digits.length - 1 - i])
    if (i % 2 === 1) {
      digit *= 2
      if (digit > 9) digit -= 9
    }
    sum += digit
  }
  return sum % 10 === 0
}

/** "4242424242424242" -> "4242 4242 4242 4242" while typing. */
export function formatCardNumber(value: string): string {
  return value
    .replace(/\D/g, '')
    .slice(0, 19)
    .replace(/(\d{4})(?=\d)/g, '$1 ')
}

/** "1228" -> "12 / 28" while typing. */
export function formatExpiry(value: string): string {
  const digits = value.replace(/\D/g, '').slice(0, 4)
  return digits.length > 2 ? `${digits.slice(0, 2)} / ${digits.slice(2)}` : digits
}

export interface CardForm {
  number: string
  expiry: string
  cvc: string
  name: string
}

export const EMPTY_CARD: CardForm = { number: '', expiry: '', cvc: '', name: '' }

export type CardErrors = Partial<Record<keyof CardForm, string>>

/** Client-side checks mirroring the payment service; returns errors or a card ready to send. */
export function validateCard(
  form: CardForm,
  now = new Date(),
): { errors: CardErrors; card: CardInput | null } {
  const errors: CardErrors = {}
  const number = form.number.replace(/\D/g, '')
  if (number.length < 13 || number.length > 19 || !luhnValid(number)) {
    errors.number = 'Check the card number.'
  }

  const [, mm, yy] = /^(\d{2})\s*\/?\s*(\d{2})$/.exec(form.expiry.trim()) ?? []
  const month = Number(mm)
  const year = 2000 + Number(yy)
  if (!mm || month < 1 || month > 12) {
    errors.expiry = 'Use MM / YY.'
  } else if (
    year < now.getFullYear() ||
    (year === now.getFullYear() && month < now.getMonth() + 1)
  ) {
    errors.expiry = 'This card has expired.'
  }

  if (!/^\d{3,4}$/.test(form.cvc)) errors.cvc = '3 or 4 digits.'
  if (form.name.trim().length < 2) errors.name = 'Name as it appears on the card.'

  if (Object.keys(errors).length > 0) return { errors, card: null }
  return {
    errors,
    card: {
      number,
      exp_month: month,
      exp_year: year,
      cvc: form.cvc,
      holder_name: form.name.trim(),
    },
  }
}
