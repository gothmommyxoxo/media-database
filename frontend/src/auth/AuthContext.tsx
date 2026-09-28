import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'
import { apiFetch, setAccessToken } from '../api/client'
import type { User } from '../types'

interface TokenResponse {
  access_token: string
}

interface AuthContextValue {
  isAuthenticated: boolean
  isAdmin: boolean
  user: User | null
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)

  const login = useCallback(async (username: string, password: string) => {
    const response = await apiFetch<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
    setAccessToken(response.access_token)
    // Section 9.1: the frontend reads role once at login to decide whether to show admin UI.
    const me = await apiFetch<User>('/auth/me')
    setUser(me)
  }, [])

  const logout = useCallback(async () => {
    try {
      await apiFetch('/auth/logout', { method: 'POST' })
    } finally {
      setAccessToken(null)
      setUser(null)
    }
  }, [])

  const value: AuthContextValue = {
    isAuthenticated: user !== null,
    isAdmin: user?.role === 'ADMIN',
    user,
    login,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
