import { api } from '../lib/api'

export interface DayHours {
  weekday: number
  day: string
  opens_at: string | null
  closes_at: string | null
}

export interface ShopSummary {
  id: string
  name: string
  address: string
  city: string
  location: { lat: number; lng: number }
  rating: string
  photo_url: string | null
  distance_m: number | null
  is_open_now: boolean
  today: DayHours
}

export interface ShopDetail extends ShopSummary {
  description: string | null
  phone_number: string | null
  opening_hours: DayHours[]
}

export interface ShopPage {
  items: ShopSummary[]
  total: number
  limit: number
  offset: number
}

export type ProductCategory = 'HOT_COFFEE' | 'COLD_COFFEE' | 'TEA' | 'OTHER'

export interface MenuItem {
  id: string
  name: string
  description: string | null
  category: ProductCategory
  list_price: string
  supports_milk: boolean
  supports_extra_shot: boolean
  image_url: string | null
  is_available: boolean
}

export interface Menu {
  shop_id: string
  shop_name: string
  items: MenuItem[]
}

export interface ShopSearch {
  lat?: number
  lng?: number
  radius?: number
  q?: string
  min_rating?: number
  open_now?: boolean
  sort?: 'distance' | 'rating' | 'name'
  limit?: number
  offset?: number
}

export const searchShops = (params: ShopSearch, signal?: AbortSignal) =>
  api<ShopPage>('/shops', { query: { ...params }, auth: false, signal })

export const getShop = (id: string, location?: { lat: number; lng: number } | null) =>
  api<ShopDetail>(`/shops/${id}`, { query: location ?? undefined, auth: false })

export const getMenu = (id: string) => api<Menu>(`/shops/${id}/menu`, { auth: false })
