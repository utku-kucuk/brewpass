import { ApiError } from './api'

/** A message that is safe and helpful to show to the user. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message
  return 'Something went wrong. Please try again.'
}
