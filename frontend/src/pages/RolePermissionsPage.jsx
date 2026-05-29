import { useState, useEffect } from 'react'
import api from '../api/client'
import { usePermission } from '../hooks/usePermission'
import { usePermissionCtx } from '../context/PermissionContext'
import UnauthorizedPage from './UnauthorizedPage'

const ROLE_LABELS = { admin: '管理员', advanced: '高级用户', regular: '普通用户' }

export default function RolePermissionsPage() {
  const { canView } = usePermission()
  const { refresh } = usePermissionCtx()
  const [grouped, setGrouped] = useState({})
  const [dirty, setDirty] = useState([])
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    api.get('/admin/permissions').then((res) => setGrouped(res.data.permissions))
  }, [])

  if (!canView('role_permission_management')) return <UnauthorizedPage />

  const handleToggle = (role, componentKey, currentVal) => {
    const newVal = !currentVal
    setGrouped((prev) => {
      const next = { ...prev }
      next[role] = next[role].map((p) =>
        p.role === role && p.component_key === componentKey ? { ...p, allowed: newVal } : p
      )
      return next
    })
    setDirty((prev) => {
      const filtered = prev.filter((d) => !(d.role === role && d.component_key === componentKey))
      return [...filtered, { role, component_key: componentKey, allowed: newVal }]
    })
  }

  const handleSave = async () => {
    if (dirty.length === 0) return
    setSaving(true)
    setMessage('')
    try {
      const items = dirty.map((d) => {
        const existing = grouped[d.role]?.find((p) => p.component_key === d.component_key)
        return { ...d, description: existing?.description || '' }
      })
      await api.put('/admin/permissions', { permissions: items })
      setDirty([])
      setMessage('保存成功')
      await refresh()
    } catch (err) {
      setMessage('保存失败: ' + (err.response?.data?.detail || '未知错误'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <h2>角色权限管理</h2>
      <p style={{ color: '#888', marginBottom: 16 }}>
        配置每个角色默认可见的组件。修改后该角色的所有用户立即生效。
      </p>

      {message && (
        <div style={{ padding: '8px 16px', marginBottom: 16, borderRadius: 4, background: message.includes('成功') ? '#e8f5e9' : '#ffebee', color: message.includes('成功') ? '#2a7' : '#d32' }}>
          {message}
        </div>
      )}

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ background: '#f5f5f5' }}>
            <th style={tdStyle}>组件</th>
            {Object.keys(ROLE_LABELS).map((r) => (
              <th key={r} style={{ ...tdStyle, textAlign: 'center' }}>{ROLE_LABELS[r]}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Object.values(grouped)[0]?.map((p) => (
            <tr key={p.component_key}>
              <td style={tdStyle}>
                <strong>{p.component_key}</strong>
                {p.description && <span style={{ color: '#999', fontSize: 12, marginLeft: 8 }}>{p.description}</span>}
              </td>
              {Object.keys(ROLE_LABELS).map((role) => {
                const perm = grouped[role]?.find((x) => x.component_key === p.component_key)
                const allowed = perm?.allowed ?? false
                const isDirty = dirty.some((d) => d.role === role && d.component_key === p.component_key)
                return (
                  <td key={role} style={{ ...tdStyle, textAlign: 'center' }}>
                    <input type="checkbox" checked={allowed} onChange={() => handleToggle(role, p.component_key, allowed)} />
                    {isDirty && <span style={{ color: '#fa0', fontSize: 11 }}> *</span>}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>

      <div style={{ marginTop: 20 }}>
        <button onClick={handleSave} disabled={dirty.length === 0 || saving} style={{ padding: '10px 32px', background: dirty.length ? '#333' : '#ccc', color: '#fff', border: 'none', borderRadius: 4, cursor: dirty.length ? 'pointer' : 'default', fontSize: 15 }}>
          {saving ? '保存中...' : `保存修改（${dirty.length} 项）`}
        </button>
      </div>
    </div>
  )
}

const tdStyle = { padding: '8px 14px', borderBottom: '1px solid #eee', textAlign: 'left', fontSize: 14 }
