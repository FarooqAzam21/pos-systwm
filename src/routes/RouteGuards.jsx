import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../context/useAuth'
import LoadingState from '../components/LoadingState'

export function ProtectedRoute() {
  const { user, loading } = useAuth()
  if (loading) return <LoadingState label="Loading your workspace…" />
  return user ? <Outlet /> : <Navigate to="/login" replace />
}

export function PublicRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <LoadingState />
  return user ? <Navigate to="/dashboard" replace /> : children
}

export function RoleGuard({ roles, redirectTo = '/dashboard', children }) {
  const { user, loading } = useAuth()
  if (loading) return <LoadingState label="Checking permissions…" />
  const destination = typeof redirectTo === 'function' ? redirectTo(user) : redirectTo
  return roles.includes(user?.role) ? (children ?? <Outlet />) : <Navigate to={destination} replace />
}
