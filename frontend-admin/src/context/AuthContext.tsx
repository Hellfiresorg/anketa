import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { apiPost } from '../lib/api'

const TOKEN_KEY = 'admin_token'
const MANAGER_KEY = 'admin_manager'

interface Manager {
  id: string
  email: string
  full_name: string
  is_active: boolean
}

interface AuthCtx {
  accessToken: string | null
  manager: Manager | null
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  setToken: (t: string) => void
  setManager: (m: Manager) => void
}

const AuthContext = createContext<AuthCtx | null>(null)

function loadStored<T>(key: string): T | null {
  try {
    const s = localStorage.getItem(key)
    return s ? (JSON.parse(s) as T) : null
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [accessToken, setAccessToken] = useState<string | null>(
    () => localStorage.getItem(TOKEN_KEY),
  )
  const [manager, setManagerState] = useState<Manager | null>(
    () => loadStored<Manager>(MANAGER_KEY),
  )

  // Auto-refresh: on app load, exchange refresh cookie for new access token
  useEffect(() => {
    if (!localStorage.getItem(TOKEN_KEY)) return
    fetch('/api/auth/refresh', { method: 'POST', credentials: 'include' })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.access_token) {
          localStorage.setItem(TOKEN_KEY, data.access_token)
          setAccessToken(data.access_token)
        }
      })
      .catch(() => {})
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const data = await apiPost('/api/auth/login', { email, password }, null)
    const me = await apiPost('/api/auth/me', null, data.access_token, 'GET')
    localStorage.setItem(TOKEN_KEY, data.access_token)
    localStorage.setItem(MANAGER_KEY, JSON.stringify(me))
    setAccessToken(data.access_token)
    setManagerState(me)
  }, [])

  const logout = useCallback(async () => {
    try {
      await apiPost('/api/auth/logout', null, accessToken)
    } catch {}
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(MANAGER_KEY)
    setAccessToken(null)
    setManagerState(null)
  }, [accessToken])

  const setToken = useCallback((t: string) => {
    localStorage.setItem(TOKEN_KEY, t)
    setAccessToken(t)
  }, [])

  const setManager = useCallback((m: Manager) => {
    localStorage.setItem(MANAGER_KEY, JSON.stringify(m))
    setManagerState(m)
  }, [])

  return (
    <AuthContext.Provider value={{ accessToken, manager, login, logout, setToken, setManager }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
