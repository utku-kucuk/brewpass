import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  cancelOrder,
  getOrder,
  getOrderHistory,
  isActive,
  placeOrder,
  reorder,
  setFavorite,
  type Order,
} from '../api/orders'

/** Polls while the order is moving through the café's queue. */
export const useOrder = (id: string) =>
  useQuery({
    queryKey: ['order', id],
    queryFn: () => getOrder(id),
    refetchInterval: (query) => (query.state.data && isActive(query.state.data) ? 5000 : false),
  })

export const useOrderHistory = (favorites: boolean, limit: number) =>
  useQuery({
    queryKey: ['orders', { favorites, limit }],
    queryFn: () => getOrderHistory({ favorites, limit }),
  })

/** Ordering uses a credit, so the pass and order caches are refreshed afterwards. */
function useOrderMutation<TArgs>(fn: (args: TArgs) => Promise<Order>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: (order) => queryClient.setQueryData(['order', order.id], order),
    onSettled: () => {
      void queryClient.invalidateQueries({ queryKey: ['orders'] })
      void queryClient.invalidateQueries({ queryKey: ['subscription'] })
    },
  })
}

export const usePlaceOrder = () => useOrderMutation(placeOrder)
export const useReorder = () => useOrderMutation((id: string) => reorder(id))
export const useCancelOrder = () => useOrderMutation((id: string) => cancelOrder(id))
export const useFavorite = () =>
  useOrderMutation(({ id, value }: { id: string; value: boolean }) => setFavorite(id, value))
