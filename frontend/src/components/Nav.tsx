/**
 * Top navigation bar — shared across all pages.
 *
 * NavLink from react-router-dom applies an "active" class automatically
 * when the current URL matches its `to` prop. We use that to highlight
 * the current page without any manual state.
 */

import { NavLink } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Nav() {
  const { user, clearAuth } = useAuth()

  return (
    <nav style={{
      display: 'flex',
      alignItems: 'center',
      gap: 4,
      padding: '0 24px',
      height: 48,
      background: '#1a1a2e',
      color: '#fff',
    }}>
      <span style={{ fontWeight: 700, marginRight: 16, fontSize: 15 }}>📬 RFQ Sender</span>

      <NavLink to="/queue" style={navLinkStyle}>Queue</NavLink>
      <NavLink to="/vendors" style={navLinkStyle}>Vendors</NavLink>

      {/* push user info to the right */}
      <span style={{ flex: 1 }} />
      <span style={{ fontSize: 13, opacity: 0.75, marginRight: 12 }}>
        {user?.name} · <code style={{ fontSize: 12 }}>{user?.role}</code>
      </span>
      <button
        onClick={clearAuth}
        style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.3)', color: '#fff', fontSize: 13 }}
      >
        Log Out
      </button>
    </nav>
  )
}

function navLinkStyle({ isActive }: { isActive: boolean }) {
  return {
    color: isActive ? '#fff' : 'rgba(255,255,255,0.6)',
    textDecoration: 'none',
    padding: '4px 12px',
    borderRadius: 4,
    fontWeight: isActive ? 600 : 400,
    background: isActive ? 'rgba(255,255,255,0.15)' : 'transparent',
    fontSize: 14,
  }
}
