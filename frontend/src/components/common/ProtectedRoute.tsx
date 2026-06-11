// ProtectedRoute.tsx
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/context/authStore'

interface ProtectedRouteProps {
  allowedRoles?: string[]
}

const ProtectedRoute = ({ allowedRoles }: ProtectedRouteProps) => {
  const { isAuthenticated, user } = useAuthStore()
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    // Redirect to role-appropriate dashboard
    if (user.role === 'ADMIN') return <Navigate to="/admin" replace />
    if (user.role === 'DRIVER') return <Navigate to="/driver/dashboard" replace />
    return <Navigate to="/dashboard" replace />
  }

  return <Outlet />
}

export default ProtectedRoute
