/* eslint-disable react-refresh/only-export-components -- context + hook no mesmo módulo */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { apiFetch, getStoredToken, setStoredToken } from '../api/client'
const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const logout = useCallback(async () => {
    const token = getStoredToken()
    if (token) {
      try {
        await apiFetch('/api/auth/logout/', { method: 'POST', token })
      } catch {
        /* ignora */
      }
    }
    setStoredToken(null)
    setUser(null)
  }, [])

  const refreshMe = useCallback(async () => {
    const token = getStoredToken()
    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }
    try {
      const me = await apiFetch('/api/auth/me/')
      setUser(me)
    } catch {
      setStoredToken(null)
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refreshMe()
  }, [refreshMe])

  const login = useCallback(async (email, password) => {
    const data = await apiFetch('/api/auth/login/', {
      method: 'POST',
      skipAuth: true,
      body: JSON.stringify({ email, password }),
    })
    setStoredToken(data.token)
    setUser(data.user)
    return data.user
  }, [])

  const register = useCallback(async (payload) => {
    const data = await apiFetch('/api/auth/register/', {
      method: 'POST',
      skipAuth: true,
      body: JSON.stringify(payload),
    })
    setStoredToken(data.token)
    setUser(data.user)
    return data.user
  }, [])

  const registerStudio = useCallback(async (payload) => {
    const data = await apiFetch('/api/studios/register/', {
      method: 'POST',
      skipAuth: true,
      body: JSON.stringify(payload),
    })
    setStoredToken(data.token)
    setUser(data.user)
    return data
  }, [])

  const value = useMemo(
    () => ({
      user,
      loading,
      login,
      logout,
      register,
      registerStudio,
      refreshMe,
      isAuthenticated: Boolean(user),
    }),
    [user, loading, login, logout, register, registerStudio, refreshMe],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth deve ser usado dentro de AuthProvider')
  return ctx
}
