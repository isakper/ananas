import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/health': 'http://127.0.0.1:8000',
      '/accounts': 'http://127.0.0.1:8000',
      '/invoices': 'http://127.0.0.1:8000',
      '/journal-entries': 'http://127.0.0.1:8000',
    },
  },
})
