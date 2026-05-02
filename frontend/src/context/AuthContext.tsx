/**
 * AuthContext — makes the current user available anywhere in the app.
 *
 * React "context" solves the "prop drilling" problem: without it, you'd have
 * to pass `user` as a prop from App → Layout → Sidebar → every page → every
 * component that needs it. Context lets any component reach for it directly.
 *
 * Pattern:
 *   1. AuthProvider wraps the whole app (in App.tsx) and holds the state
 *   2. Any component calls `const { user } = useAuth()` to read it
 *   3. When setAuth() or clearAuth() is called, every component re-renders
 */

import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import type { User } from '../api/auth'

interface AuthContextValue {
  user: User | null
  token: string | null
  setAuth: (user: User, token: string) => void
  clearAuth: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)

  // On first mount, restore session from localStorage.
  // This is why you stay logged in after a page refresh — the browser
  // keeps localStorage between sessions, unlike component state.
  useEffect(() => {
    const savedToken = localStorage.getItem('rfq_token')
    const savedUser = localStorage.getItem('rfq_user')
    if (savedToken && savedUser) {
      try {
        setToken(savedToken)
        setUser(JSON.parse(savedUser))
      } catch {
        // Corrupted data — start fresh
        localStorage.removeItem('rfq_token')
        localStorage.removeItem('rfq_user')
      }
    }
  }, []) // [] means "run once when the component first mounts"

  function setAuth(user: User, token: string) {
    localStorage.setItem('rfq_token', token)
    localStorage.setItem('rfq_user', JSON.stringify(user))
    setUser(user)
    setToken(token)
  }

  function clearAuth() {
    localStorage.removeItem('rfq_token')
    localStorage.removeItem('rfq_user')
    setUser(null)
    setToken(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, setAuth, clearAuth }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
