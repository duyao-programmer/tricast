import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import api from '../api/client'
import { useAuth } from './AuthContext'

const PermissionContext = createContext(null)

export function PermissionProvider({ children }) {
  const { isAuthenticated } = useAuth()
  const [components, setComponents] = useState([])
  const [role, setRole] = useState('')

  const fetchPermissions = useCallback(async () => {
    try {
      const res = await api.get('/user/permissions')
      setComponents(res.data.components)
      setRole(res.data.role)
    } catch {
      // 降级：设为空数组，菜单为空但不会崩溃
      setComponents([])
      setRole('')
    }
  }, [])

  useEffect(() => {
    if (isAuthenticated) {
      fetchPermissions()
    } else {
      setComponents([])
      setRole('')
    }
  }, [isAuthenticated, fetchPermissions])

  return (
    <PermissionContext.Provider value={{ components, role, refresh: fetchPermissions }}>
      {children}
    </PermissionContext.Provider>
  )
}

export function usePermissionCtx() {
  const ctx = useContext(PermissionContext)
  if (!ctx) throw new Error('usePermissionCtx must be used within PermissionProvider')
  return ctx
}
