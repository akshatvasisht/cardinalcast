import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { api } from '@/api/client'
import type { User } from '@/api/types'

/** Dummy token used when dev bypass is on and there is no real token. Pages can check for this to skip backend calls. */
export const DEV_BYPASS_TOKEN = 'dev-bypass'

const DEV_BYPASS =
  import.meta.env.DEV && import.meta.env.VITE_DEV_BYPASS_AUTH === 'true'

const MOCK_USER: User = {
  id: 1,
  username: 'dev_user',
  credits_balance: 2_340,
}

type AuthContextValue = {
  token: string | null
  user: User | null
  loading: boolean
  login: (t: string) => void
  logout: () => void
  setUser: (u: User | null) => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

function getInitialAuth() {
  const stored = localStorage.getItem('token')
  const useBypass = DEV_BYPASS && !stored
  return {
    token: useBypass ? DEV_BYPASS_TOKEN : stored,
    user: useBypass ? MOCK_USER : null,
    loading: useBypass ? false : true,
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const initial = getInitialAuth()
  const [token, setToken] = useState<string | null>(() => initial.token)
  const [user, setUser] = useState<User | null>(() => initial.user)
  const [loading, setLoading] = useState(() => initial.loading)

  useEffect(() => {
    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }
    if (token === DEV_BYPASS_TOKEN) {
      setLoading(false)
      return
    }
    api
      .me(token)
      .then(setUser)
      .catch(() => {
        setToken(null)
        localStorage.removeItem('token')
      })
      .finally(() => setLoading(false))
  }, [token])

  const login = useCallback((t: string) => {
    setToken(t)
    localStorage.setItem('token', t)
  }, [])

  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
    localStorage.removeItem('token')
  }, [])

  return (
    <AuthContext.Provider value={{ token, user, loading, login, logout, setUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
