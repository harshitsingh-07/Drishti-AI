import { createContext, useContext, useEffect, useMemo, useState } from 'react'

const STORAGE_KEY = 'ai_eye_user'

const AuthContext = createContext(null)

function readStoredUser() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => readStoredUser())

  useEffect(() => {
    if (user == null) {
      localStorage.removeItem(STORAGE_KEY)
    } else {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(user))
    }
  }, [user])

  const login = (userData) => {
    // await authService.login(credentials)
    setUser(userData)
  }

  const logout = () => {
    // await authService.logout()
    setUser(null)
  }

  const register = (userData) => {
    // await authService.register(payload)
    setUser(userData)
  }

  const value = useMemo(
    () => ({ user, login, logout, register }),
    [user],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context == null) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
