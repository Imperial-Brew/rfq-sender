/**
 * Axios HTTP client — the single place all API calls go through.
 *
 * Why axios instead of the browser's built-in fetch()?
 * Axios adds "interceptors" — middleware that runs on every request or
 * response. We use them here to solve two problems automatically:
 *
 *   1. Auth: attach the JWT to every outgoing request so individual
 *      API functions don't have to remember to do it themselves.
 *
 *   2. Session expiry: if any response comes back as 401 (token expired),
 *      clear the stored token and bounce the user to /login.
 */

import axios from 'axios'

const client = axios.create({
  // All requests use /api as the base. Vite's proxy (vite.config.ts)
  // forwards /api/* → http://localhost:8000/* during development.
  baseURL: '/api',
})

// REQUEST interceptor: runs before each outgoing request
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('rfq_token')
  if (token) {
    // This is the standard "Bearer token" format the FastAPI backend expects.
    // FastAPI's HTTPBearer() reads the part after "Bearer ".
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// RESPONSE interceptor: runs after each response comes back
client.interceptors.response.use(
  (response) => response, // success — pass through unchanged
  (error) => {
    if (error.response?.status === 401) {
      // JWT is expired or invalid. Clear local storage and redirect.
      // The user will need to log in again to get a fresh token.
      localStorage.removeItem('rfq_token')
      localStorage.removeItem('rfq_user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

export default client
