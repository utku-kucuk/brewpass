import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  cancelSubscription,
  changePlan,
  getMySubscription,
  getPayments,
  getPlans,
  resumeSubscription,
  subscribe,
  type CardInput,
  type PlanCode,
  type Subscription,
} from '../api/subscriptions'

export const usePlans = () =>
  useQuery({ queryKey: ['plans'], queryFn: getPlans, staleTime: 10 * 60_000 })

export const useMySubscription = () =>
  useQuery({ queryKey: ['subscription'], queryFn: getMySubscription })

export const usePayments = () => useQuery({ queryKey: ['payments'], queryFn: getPayments })

/** Every pass change can create a payment, so both caches are refreshed. */
function usePassMutation<TArgs>(fn: (args: TArgs) => Promise<Subscription>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: (subscription) => {
      queryClient.setQueryData(
        ['subscription'],
        subscription.status === 'CANCELLED' ? null : subscription,
      )
    },
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ['payments'] })
    },
  })
}

export const useSubscribe = () =>
  usePassMutation(({ plan, card }: { plan: PlanCode; card: CardInput }) => subscribe(plan, card))

export const useChangePlan = () => usePassMutation((plan: PlanCode) => changePlan(plan))

export const useResume = () => usePassMutation((card?: CardInput) => resumeSubscription(card))

export const useCancelPass = () => usePassMutation(() => cancelSubscription())
