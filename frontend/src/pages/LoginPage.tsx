/**
 * Login page.
 *
 * Concepts illustrated here:
 *
 *   useState — local component state. Each call manages one piece of data
 *     (the email string, the password string, etc.). When you call setEmail(),
 *     React re-renders the component with the new value.
 *
 *   Controlled inputs — the input's value is bound to React state
 *     (value={email}), and onChange updates that state. React "owns" the
 *     input value rather than the DOM. This is the standard React pattern.
 *
 *   async/await — the login API call is asynchronous (it makes an HTTP
 *     request). We await it inside a try/catch so we can handle errors.
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login } from '../api/auth'
import { useAuth } from '../context/AuthContext'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const { setAuth } = useAuth()
  const navigate = useNavigate() // programmatic navigation (like redirect)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault() // prevent the browser from reloading the page on submit
    setError('')
    setLoading(true)
    try {
      const result = await login(email, password)
      setAuth(result.user, result.access_token)
      navigate('/queue')
    } catch {
      setError('Invalid email or password.')
    } finally {
      // finally runs whether the try succeeded or the catch ran
      setLoading(false)
    }
  }

  return (
    <div style={{
      maxWidth: 360,
      margin: '80px auto',
      padding: '32px',
      background: '#fff',
      borderRadius: 8,
      boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
    }}>
      <h1 style={{ marginTop: 0, fontSize: 22 }}>📬 RFQ Sender</h1>

      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: 16 }}>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            required
          />
        </div>

        <div style={{ marginBottom: 16 }}>
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </div>

        {error && (
          <p style={{ color: '#d93025', marginBottom: 12 }}>{error}</p>
        )}

        <button
          type="submit"
          className="primary"
          disabled={loading}
          style={{ width: '100%' }}
        >
          {loading ? 'Signing in…' : 'Sign In'}
        </button>
      </form>
    </div>
  )
}
