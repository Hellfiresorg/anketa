import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { accessToken, manager } = useAuth()
  if (!accessToken) return <Navigate to="/login" replace />
  if (manager !== null && !manager.full_name) return <Navigate to="/setup-name" replace />
  return <>{children}</>
}
