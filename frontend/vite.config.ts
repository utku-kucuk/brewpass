import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    css: { modules: { classNameStrategy: 'non-scoped' } },
    restoreMocks: true,
  },
  server: {
    port: 5173,
    proxy: {
      // Forward API calls to the API gateway (docker compose) during development.
      '/api': 'http://localhost:8080',
    },
  },
})
