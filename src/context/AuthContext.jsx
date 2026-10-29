import { useCallback, useEffect, useMemo, useState } from 'react'
import { AuthContext } from './AuthContextValue'
import { authService } from '../services/authService'
import { setAccessToken } from '../services/api'
import { businessService } from '../services/businessService'
import { CURRENCY_KEY } from '../utils/formatters'

const TOKEN_KEY = 'pos_access_token'

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(() => Boolean(localStorage.getItem(TOKEN_KEY)))

  const logout = useCallback(() => {
    setAccessToken(null)
    localStorage.removeItem(TOKEN_KEY)
    setUser(null)
  }, [])

  const acceptSession = useCallback((session) => {
    localStorage.setItem(TOKEN_KEY, session.access_token)
    setAccessToken(session.access_token)
    setUser(session.user)
  }, [])

  const updateAccount = useCallback(async (details) => {
    const updated = await authService.updateMe(details)
    setUser(updated)
    // The backend increments the token version after a password change. Clear
    // the now-revoked browser token immediately and require a fresh sign-in.
    if (details.new_password) logout()
    return updated
  }, [logout])

  useEffect(() => {
    const onExpired = () => logout()
    window.addEventListener('auth:expired', onExpired)
    const token = localStorage.getItem(TOKEN_KEY)
    if (!token) {
      return () => window.removeEventListener('auth:expired', onExpired)
    }
    setAccessToken(token)
    authService.me()
      .then(setUser)
      .catch((error) => {
        // Only discard a session when the server confirms it is invalid. A
        // timeout/network error during a Render cold start must not erase it.
        if (error.response?.status === 401) logout()
      })
      .finally(() => setLoading(false))
    return () => window.removeEventListener('auth:expired', onExpired)
  }, [logout])

  useEffect(() => {
    if (!user) return
    businessService.get()
      .then((business) => localStorage.setItem(CURRENCY_KEY, business.currency || 'USD'))
      .catch(() => {})
  }, [user?.id])

  const value = useMemo(() => ({
    user,
    loading,
    login: async (credentials) => {
      const result = await authService.login(credentials)
      if (result.access_token) acceptSession(result)
      return result
    },
    finishActivation: async (challenge) => {
      const session = await authService.finishActivation(challenge)
      acceptSession(session)
      return session
    },
    register: async (details) => acceptSession(await authService.register(details)),
    updateAccount,
    logout,
  }), [user, loading, acceptSession, logout, updateAccount])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
