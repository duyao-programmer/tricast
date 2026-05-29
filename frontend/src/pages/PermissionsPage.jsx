import { usePermission } from '../hooks/usePermission'
import UnauthorizedPage from './UnauthorizedPage'

const ts = { padding: '8px 14px', borderBottom: '1px solid #eee', textAlign: 'left', fontSize: 14 }

export default function PermissionsPage() {
  const { canView } = usePermission()
  if (!canView('user_permission_management')) return <UnauthorizedPage />
  return (
    <div>
      <h2>用户权限管理</h2>
      <p style={{ color: '#888', marginBottom: 16 }}>
        输入用户名搜索，为用户单独授权或禁止某个组件，覆盖角色默认规则。
      </p>
      <UserPermissionPanel />
    </div>
  )
}

import { useState, useEffect, useRef } from 'react'
import api from '../api/client'

function UserPermissionPanel() {
  const [users, setUsers] = useState([])
  const [query, setQuery] = useState('')
  const [showDropdown, setShowDropdown] = useState(false)
  const [selectedUser, setSelectedUser] = useState(null)
  const [perms, setPerms] = useState([])
  const [dirty, setDirty] = useState({})
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const inputRef = useRef(null)
  const dropdownRef = useRef(null)

  useEffect(() => {
    api.get('/admin/users').then((res) => setUsers(res.data))
    const handler = (e) => { if (dropdownRef.current && !dropdownRef.current.contains(e.target)) setShowDropdown(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const filtered = query
    ? users.filter((u) => u.username.toLowerCase().includes(query.toLowerCase()))
    : users

  const loadUserPerms = async (userId) => {
    const res = await api.get(`/admin/users/${userId}/permissions`)
    setSelectedUser(res.data)
    setPerms(res.data.components)
    setDirty({})
    setMessage('')
    setShowDropdown(false)
  }

  const handleOverride = (componentKey, newType) => {
    setDirty((prev) => ({ ...prev, [componentKey]: newType }))
  }

  const handleSave = async () => {
    const overrides = Object.entries(dirty).map(([k, v]) => ({ component_key: k, override_type: v }))
    if (overrides.length === 0) return
    setSaving(true)
    try {
      await api.put(`/admin/users/${selectedUser.user_id}/permissions`, { overrides })
      setDirty({})
      setMessage('保存成功')
      loadUserPerms(selectedUser.user_id)
    } catch (err) {
      setMessage('保存失败: ' + (err.response?.data?.detail || '未知错误'))
    } finally { setSaving(false) }
  }

  const badge = (item) => {
    const v = dirty[item.component_key] !== undefined ? dirty[item.component_key] : item.override
    if (v === 'grant') return { text: '额外授权', color: '#2e7d32', bg: '#e8f5e9' }
    if (v === 'deny') return { text: '额外禁止', color: '#c62828', bg: '#ffebee' }
    return null
  }

  return (
    <div>
      {/* 搜索框 */}
      <div style={{ position: 'relative', marginBottom: 16 }} ref={dropdownRef}>
        <input
          ref={inputRef}
          type="text"
          placeholder="输入用户名搜索..."
          value={query}
          onChange={(e) => { setQuery(e.target.value); setShowDropdown(true) }}
          onFocus={() => setShowDropdown(true)}
          style={{ padding: '8px 14px', border: '1px solid #ccc', borderRadius: 4, fontSize: 14, width: 280, boxSizing: 'border-box' }}
        />
        {showDropdown && filtered.length > 0 && (
          <div style={{
            position: 'absolute', top: '100%', left: 0, width: 280, maxHeight: 200, overflowY: 'auto',
            background: '#fff', border: '1px solid #ddd', borderRadius: 4, boxShadow: '0 4px 12px rgba(0,0,0,0.1)', zIndex: 10,
          }}>
            {filtered.map((u) => (
              <div
                key={u.id}
                onClick={() => { setQuery(u.username); loadUserPerms(u.id) }}
                style={{
                  padding: '8px 14px', cursor: 'pointer', fontSize: 14,
                  background: selectedUser?.user_id === u.id ? '#e8f0fe' : '#fff',
                  borderBottom: '1px solid #f0f0f0',
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = '#f5f5f5'}
                onMouseLeave={(e) => e.currentTarget.style.background = selectedUser?.user_id === u.id ? '#e8f0fe' : '#fff'}
              >
                <strong>{u.username}</strong>
                <span style={{ color: '#888', marginLeft: 8, fontSize: 12 }}>{u.role}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {message && (
        <div style={{ padding: '8px 16px', marginBottom: 12, borderRadius: 4, background: message.includes('成功') ? '#e8f5e9' : '#ffebee', color: message.includes('成功') ? '#2a7' : '#d32' }}>
          {message}
        </div>
      )}

      {selectedUser && (
        <div>
          <p style={{ color: '#555', marginBottom: 12, fontSize: 14 }}>
            已选择: <strong>{selectedUser.username}</strong>（角色: {selectedUser.role}）
            <span style={{ color: '#aaa', marginLeft: 12 }}>角色默认允许的组件打勾，最终结果 = (角色默认 OR grant) AND NOT deny</span>
          </p>
          <table style={{ width: '100%', borderCollapse: 'collapse', tableLayout: 'fixed' }}>
            <thead>
              <tr style={{ background: '#f5f5f5' }}>
                <th style={{ ...ts, width: '25%' }}>组件</th>
                <th style={{ ...ts, width: '15%', textAlign: 'center' }}>角色默认</th>
                <th style={{ ...ts, width: '15%', textAlign: 'center' }}>覆盖状态</th>
                <th style={{ ...ts, width: '15%', textAlign: 'center' }}>最终结果</th>
                <th style={{ ...ts, width: '30%', textAlign: 'center' }}>操作</th>
              </tr>
            </thead>
            <tbody>
              {perms.map((item) => {
                const b = badge(item)
                return (
                  <tr key={item.component_key} style={{ background: item.effective ? '#fff' : '#fff8f8' }}>
                    <td style={ts}>
                      <strong>{item.component_key}</strong>
                      {item.description && <span style={{ color: '#999', fontSize: 11, marginLeft: 6 }}>{item.description}</span>}
                    </td>
                    <td style={{ ...ts, textAlign: 'center' }}>
                      <span style={{ fontSize: 12, color: item.role_default ? '#2a7' : '#d32' }}>
                        {item.role_default ? '允许' : '禁止'}
                      </span>
                    </td>
                    <td style={{ ...ts, textAlign: 'center' }}>
                      {b ? <span style={{ padding: '2px 8px', borderRadius: 3, fontSize: 11, color: b.color, background: b.bg }}>{b.text}</span>
                        : <span style={{ color: '#bbb', fontSize: 12 }}>跟随角色</span>}
                    </td>
                    <td style={{ ...ts, textAlign: 'center', fontWeight: 600, color: item.effective ? '#2a7' : '#d32' }}>
                      {item.effective ? '允许' : '禁止'}
                    </td>
                    <td style={{ ...ts, textAlign: 'center' }}>
                      <select
                        value={dirty[item.component_key] !== undefined ? dirty[item.component_key] : (item.override || '')}
                        onChange={(e) => handleOverride(item.component_key, e.target.value === '' ? null : e.target.value)}
                        style={{ padding: '4px 8px', fontSize: 12, borderRadius: 3, border: '1px solid #ddd' }}
                      >
                        <option value="">默认（跟随角色）</option>
                        <option value="grant">授权（grant）</option>
                        <option value="deny">禁止（deny）</option>
                      </select>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          <div style={{ marginTop: 16 }}>
            <button
              onClick={handleSave}
              disabled={Object.keys(dirty).length === 0 || saving}
              style={{ padding: '10px 32px', background: Object.keys(dirty).length ? '#1a1a2e' : '#ccc', color: '#fff', border: 'none', borderRadius: 4, cursor: Object.keys(dirty).length ? 'pointer' : 'default', fontSize: 15 }}
            >
              {saving ? '保存中...' : `保存（${Object.keys(dirty).length} 项）`}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
