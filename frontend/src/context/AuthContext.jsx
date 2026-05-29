import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import api from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)     // { username, role }
  const [loading, setLoading] = useState(true)

  // 初始化：尝试获取用户权限（Cookie 自动携带）
  useEffect(() => {
    let cancelled = false
    api.get('/user/permissions')
      .then((res) => {
        if (!cancelled) setUser({ username: res.data.username, role: res.data.role })
      })
      .catch(() => {
        // 未登录或 token 失效，忽略（在 /login 页面是正常的）
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  const login = useCallback(async (username, password) => {
    const res = await api.post('/auth/login', { username, password })
    setUser({ username: res.data.username, role: res.data.role })
    return res.data
  }, [])

  const logout = useCallback(async () => {
    await api.post('/auth/logout')
    setUser(null)
  }, [])

  const isAuthenticated = !!user

  return (
    <AuthContext.Provider value={{ user, loading, isAuthenticated, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
