import React, { createContext, useContext, useEffect, useState } from 'react'

type AuthCtx = {
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<boolean>
  logout: () => void
  user?: { email: string }
}

const AuthContext = createContext<AuthCtx | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false)
  const [user, setUser] = useState<{email: string} | undefined>(undefined)

  useEffect(() => {
    const saved = localStorage.getItem('demo-auth')
    if (saved) {
      const parsed = JSON.parse(saved)
      setIsAuthenticated(!!parsed?.isAuthenticated)
      setUser(parsed?.user)
    }
  }, [])

  const login = async (email: string, password: string) => {
    // Dummy credentials
    if (email === 'admin@demo.dev' && password === 'Pass@123') {
      const u = { email }
      setIsAuthenticated(true)
      setUser(u)
      localStorage.setItem('demo-auth', JSON.stringify({ isAuthenticated: true, user: u }))
      return true
    }
    return false
  }

  const logout = () => {
    setIsAuthenticated(false)
    setUser(undefined)
    localStorage.removeItem('demo-auth')
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, login, logout, user }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
