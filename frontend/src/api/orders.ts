import { api } from '../lib/api'

export type OrderStatus = 'PENDING' | 'ACCEPTED' | 'PREPARING' | 'READY' | 'COMPLETED' | 'CANCELLED'
export type DrinkSize = 'S' | 'M' | 'L'
export type MilkOption = 'NONE' | 'WHOLE' | 'SKIMMED' | 'OAT' | 'ALMOND' | 'LACTOSE_FREE'

export interface StatusEvent {
  from_status: OrderStatus | null
  to_status: OrderStatus
  created_at: string
}

export interface Order {
  id: string
  status: OrderStatus
  shop_id: string
  shop_name: string
  product_id: string
  product_name: string
  size: DrinkSize
  milk: MilkOption
  sugar: number
  extra_shots: number
  note: string | null
  is_guest: boolean
  is_priority: boolean
  is_favorite: boolean
  created_at: string
  completed_at: string | null
  qr_payload: string | null
  status_history: StatusEvent[]
}

export interface OrderPage {
  items: Order[]
  total: number
  limit: number
  offset: number
}

export interface NewOrder {
  product_id: string
  size: DrinkSize
  milk: MilkOption
  sugar: number
  extra_shots: number
  note?: string | null
  use_guest_credit: boolean
}

export const placeOrder = (order: NewOrder) =>
  api<Order>('/orders', { method: 'POST', body: order })

export const getOrder = (id: string) => api<Order>(`/orders/${id}`)

export const getOrderHistory = (params: { favorites?: boolean; limit?: number; offset?: number }) =>
  api<OrderPage>('/orders/history', { query: params })

export const cancelOrder = (id: string) => api<Order>(`/orders/${id}/cancel`, { method: 'POST' })

export const reorder = (id: string) => api<Order>(`/orders/${id}/reorder`, { method: 'POST' })

export const setFavorite = (id: string, isFavorite: boolean) =>
  api<Order>(`/orders/${id}/favorite`, { method: 'PATCH', body: { is_favorite: isFavorite } })

export const ACTIVE_STATUSES: OrderStatus[] = ['PENDING', 'ACCEPTED', 'PREPARING', 'READY']
export const isActive = (order: Pick<Order, 'status'>) => ACTIVE_STATUSES.includes(order.status)
