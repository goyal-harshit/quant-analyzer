'use client'

import React, { createContext, useContext, useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { authApi } from '@/lib/api'

interface User {
  id: number
  email: string
  plan: string
  is_active: boolean
}

interface AuthContextType {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

// Non-sensitive marker that a session likely exists. The actual JWT lives only in
// the httpOnly cookie set by the backend — never in JS-readable storage.
const AUTH_FLAG = 'authed'

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  const fetchUser = async () => {
    try {
      const data = await authApi.me()
      setUser(data)
      localStorage.setItem(AUTH_FLAG, '1')
    } catch {
      setUser(null)
      localStorage.removeItem(AUTH_FLAG)
      localStorage.removeItem('token')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    // A legacy 'token' or the 'authed' marker both signal a possible session;
    // /me then confirms it via the httpOnly cookie.
    if (localStorage.getItem(AUTH_FLAG) || localStorage.getItem('token')) {
      fetchUser()
    } else {
      setUser(null)
      setLoading(false)
    }
  }, [])

  const login = async (email: string, password: string) => {
    const params = new URLSearchParams()
    params.append('username', email)
    params.append('password', password)

    // Login sets the httpOnly auth cookies server-side; we only record a marker.
    await authApi.login(params)
    localStorage.setItem(AUTH_FLAG, '1')
    localStorage.removeItem('token') // drop any legacy JS-stored token
    await fetchUser()
    router.push('/dashboard')
  }

  const register = async (email: string, password: string) => {
    await authApi.register({ email, password })
    await login(email, password)
  }

  const logout = async () => {
    try {
      await authApi.logout() // clears the httpOnly cookies server-side
    } catch {
      /* best-effort */
    }
    localStorage.removeItem(AUTH_FLAG)
    localStorage.removeItem('token')
    localStorage.removeItem('csrf')
    setUser(null)
    router.push('/login')
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
