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

export function RoleGuard({ roles }) {
  const { user, loading } = useAuth()
  if (loading) return <LoadingState label="Checking permissions…" />
  return roles.includes(user?.role) ? <Outlet /> : <Navigate to="/dashboard" replace />
}
