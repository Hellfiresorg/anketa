import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import LoginPage from './pages/Login'
import SetupNamePage from './pages/SetupName'
import Dashboard from './pages/Dashboard'
import InvitationDetail from './pages/InvitationDetail'
import CreateInvitation from './pages/CreateInvitation'
import Settings from './pages/Settings'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/setup-name" element={<SetupNamePage />} />
          <Route
            path="/"
            element={<ProtectedRoute><Dashboard /></ProtectedRoute>}
          />
          <Route
            path="/invitations/new"
            element={<ProtectedRoute><CreateInvitation /></ProtectedRoute>}
          />
          <Route
            path="/invitations/:id"
            element={<ProtectedRoute><InvitationDetail /></ProtectedRoute>}
          />
          <Route
            path="/settings"
            element={<ProtectedRoute><Settings /></ProtectedRoute>}
          />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
