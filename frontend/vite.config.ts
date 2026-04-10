import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

const proxyTarget = process.env.VITE_PROXY_TARGET ?? 'http://127.0.0.1:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/health': proxyTarget,
      '/accounts': proxyTarget,
      '/invoices': proxyTarget,
      '/journal-entries': proxyTarget,
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './tests/setup.ts',
    include: ['tests/**/*.test.tsx'],
  },
})
