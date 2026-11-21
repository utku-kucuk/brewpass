import '@testing-library/jest-dom/vitest'

import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach } from 'vitest'

import { useAuthStore } from '../lib/auth-store'

beforeEach(() => {
  localStorage.clear()
  useAuthStore.setState({ tokens: null, user: null })
})

afterEach(() => {
  cleanup()
})
