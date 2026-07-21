import { useCallback, useEffect, useMemo, useState } from 'react'

import { api, clearAccessToken } from '../../api/client'
import type { CurrentUser } from '../../api/types'
import { AuthStateContext } from './auth-state'

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    void api.refresh()
      .then(api.me)
      .then((current) => {
        if (active) setUser(current)
      })
      .catch(() => clearAccessToken())
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  const login = useCallback(async (username: string, password: string) => {
    await api.login(username, password)
    setUser(await api.me())
  }, [])

  const logout = useCallback(async () => {
    await api.logout()
    setUser(null)
  }, [])

  const value = useMemo(() => ({ user, loading, login, logout }), [user, loading, login, logout])
  return <AuthStateContext.Provider value={value}>{children}</AuthStateContext.Provider>
}
