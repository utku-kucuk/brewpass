import { api } from '../lib/api'
import type { Role, SessionUser } from '../lib/auth-store'

export interface UserPreferences {
  favorite_drinks: string[]
  allergens: string[]
}

export interface User {
  id: string
  phone_number: string
  full_name: string | null
  email: string | null
  role: Role
  preferences: UserPreferences
  profile_completed: boolean
  created_at: string
}

export interface RegisterResult {
  phone_number: string
  is_new_user: boolean
  otp_expires_in: number
}

export interface AuthResult {
  access_token: string
  refresh_token: string
  token_type: 'bearer'
  expires_in: number
  user: User
}

export interface ProfileUpdate {
  full_name?: string
  email?: string | null
  preferences?: UserPreferences
}

export const toSessionUser = (user: User): SessionUser => ({
  id: user.id,
  phoneNumber: user.phone_number,
  fullName: user.full_name,
  role: user.role,
  profileCompleted: user.profile_completed,
})

export const requestCode = (phoneNumber: string) =>
  api<RegisterResult>('/auth/register', {
    method: 'POST',
    body: { phone_number: phoneNumber },
    auth: false,
  })

export const verifyCode = (phoneNumber: string, code: string) =>
  api<AuthResult>('/auth/verify-otp', {
    method: 'POST',
    body: { phone_number: phoneNumber, code },
    auth: false,
  })

export const logout = (refreshToken: string) =>
  api<void>('/auth/logout', {
    method: 'POST',
    body: { refresh_token: refreshToken },
    auth: false,
  })

export const getMe = () => api<User>('/users/me')

export const updateMe = (update: ProfileUpdate) =>
  api<User>('/users/me', { method: 'PATCH', body: update })
