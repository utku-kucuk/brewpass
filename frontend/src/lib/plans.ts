import type { Plan } from '../api/subscriptions'

export function planPerks(plan: Plan): string[] {
  const perks = [
    plan.is_unlimited ? 'Unlimited drinks' : `${plan.monthly_credits} drinks a month`,
    'Valid at every partner café',
  ]
  if (plan.guest_credits > 0) perks.push(`${plan.guest_credits} drinks for friends`)
  if (plan.priority_pickup) perks.push('Priority pickup')
  return perks
}

/** Positive for an upgrade, negative for a downgrade. */
export const priceDifference = (from: Plan, to: Plan) => Number(to.price) - Number(from.price)
