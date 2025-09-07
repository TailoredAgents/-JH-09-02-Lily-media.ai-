import { useAuth } from '../contexts/AuthContext'
import { Navigate, useLocation } from 'react-router-dom'

const ProtectedRoute = ({
  children,
  requiredPermission = null,
  requiredRole = null,
}) => {
  const { isAuthenticated, isLoading, user } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  // Future: Add permission and role checking here
  // if (requiredPermission && !user?.permissions?.includes(requiredPermission)) {
  //   return <Navigate to="/403" replace />
  // }
  //
  // if (requiredRole && user?.role !== requiredRole) {
  //   return <Navigate to="/403" replace />
  // }

  return children
}

export default ProtectedRoute
