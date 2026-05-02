/**
 * App.tsx — the root of the React component tree.
 *
 * Three providers wrap everything:
 *
 *   QueryClientProvider — TanStack Query's cache layer. Think of it as a
 *     smart in-memory store for server data. Any component can ask "give me
 *     the queue" and TQ handles fetching, caching, loading states, and
 *     automatic background refresh. One instance, shared by the whole app.
 *
 *   AuthProvider — our custom context (AuthContext.tsx) that holds the
 *     current user and token. Any component can call useAuth() to read them.
 *
 *   BrowserRouter — React Router. Reads the URL and renders the matching
 *     Route component. Without this, React wouldn't know what to show for
 *     /login vs /queue.
 *
 * PrivateRoute: a thin wrapper that redirects to /login if not authenticated.
 * It's just a component that either renders its children or a <Navigate>.
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from './context/AuthContext'
import LoginPage from './pages/LoginPage'
import QueuePage from './pages/QueuePage'
import VendorsPage from './pages/VendorsPage'
import SpecsPage from './pages/SpecsPage'
import RfqMasterPage from './pages/RfqMasterPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Don't retry failed requests by default — a 401 or 404 won't fix itself.
      retry: false,
      // Keep cached data for 5 minutes before re-fetching in the background.
      staleTime: 5 * 60 * 1000,
    },
  },
})

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  return user ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/queue" element={<PrivateRoute><QueuePage /></PrivateRoute>} />
            <Route path="/vendors" element={<PrivateRoute><VendorsPage /></PrivateRoute>} />
            <Route path="/specs" element={<PrivateRoute><SpecsPage /></PrivateRoute>} />
            <Route path="/rfq-master" element={<PrivateRoute><RfqMasterPage /></PrivateRoute>} />
            <Route path="/" element={<Navigate to="/queue" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}
