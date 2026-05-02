import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

/**
 * The proxy block is the key development-time trick.
 *
 * Problem: React runs on localhost:5173, FastAPI on localhost:8000.
 * Browser sees these as different "origins" and blocks the requests (CORS).
 *
 * Solution: tell Vite "any request starting with /api, forward it to :8000
 * and strip the /api prefix." From React's perspective, it's talking to its
 * own server — no CORS issue at all during development.
 *
 * In production you'd configure your actual web server (nginx, etc.) to do
 * the same thing, or deploy the React build as static files served by FastAPI.
 */
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
