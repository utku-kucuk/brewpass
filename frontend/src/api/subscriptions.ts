import { api, ApiError } from '../lib/api'

export type PlanCode = 'SIP' | 'DAILY' | 'BOTTOMLESS'
export type SubscriptionStatus = 'ACTIVE' | 'PAUSED' | 'CANCELLED'

export interface Plan {
  code: PlanCode
  name: string
  description: string | null
  price: string
  currency: string
  monthly_credits: number | null
  guest_credits: number
  priority_pickup: boolean
  is_unlimited: boolean
}

export interface Subscription {
  id: string
  status: SubscriptionStatus
  plan: Plan
  remaining_credits: number | null
  remaining_guest_credits: number
  current_period_start: string
  current_period_end: string
  pending_plan: Plan | null
  payment_transaction_id: string | null
  cancelled_at: string | null
}

/** Card details are sent straight to the API and never stored in the app. */
export interface CardInput {
  number: string
  exp_month: number
  exp_year: number
  cvc: string
  holder_name: string
}

export interface Payment {
  transaction_id: string
  status: 'SUCCEEDED' | 'FAILED'
  amount: string
  currency: string
  description: string
  card_last4: string | null
  failure_reason: string | null
  created_at: string
}

export const getPlans = () => api<Plan[]>('/subscriptions/plans', { auth: false })

/** The member's live pass, or null when they don't have one. */
export async function getMySubscription(): Promise<Subscription | null> {
  try {
    return await api<Subscription>('/subscriptions/me')
  } catch (error) {
    if (error instanceof ApiError && error.code === 'NO_ACTIVE_SUBSCRIPTION') return null
    throw error
  }
}

export const subscribe = (planCode: PlanCode, card: CardInput) =>
  api<Subscription>('/subscriptions', { method: 'POST', body: { plan_code: planCode, card } })

export const changePlan = (planCode: PlanCode) =>
  api<Subscription>('/subscriptions/me', { method: 'PATCH', body: { plan_code: planCode } })

export const resumeSubscription = (card?: CardInput) =>
  api<Subscription>('/subscriptions/me/resume', { method: 'POST', body: card ? { card } : {} })

export const cancelSubscription = () => api<Subscription>('/subscriptions/me', { method: 'DELETE' })

export const getPayments = () => api<Payment[]>('/payments/me')
