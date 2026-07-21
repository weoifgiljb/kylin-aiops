import { createContext, useContext } from 'react'

import type { CurrentUser } from '../../api/types'

export interface AuthState {
  user: CurrentUser | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

export const AuthStateContext = createContext<AuthState | null>(null)

export function useAuth(): AuthState {
  const context = useContext(AuthStateContext)
  if (!context) throw new Error('useAuth 必须在 AuthProvider 内使用')
  return context
}
