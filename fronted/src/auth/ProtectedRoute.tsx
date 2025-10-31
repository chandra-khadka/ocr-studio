import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from './auth-context'

export default function ProtectedRoute({ children }: { children: JSX.Element }) {
  const { isAuthenticated } = useAuth()
  const location = useLocation()
  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location }} replace />
  return children
}
