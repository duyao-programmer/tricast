import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import api from '../api/client'
import { useAuth } from '../context/AuthContext'

const ROLE_LABELS = { admin: '管理员', advanced: '高级用户', regular: '普通用户' }
const ROLE_COLORS = { admin: '#1890ff', advanced: '#52c41a', regular: '#fa8c16' }

export default function UsersByRolePage() {
  const { role } = useParams()
  const { user } = useAuth()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/admin/users', { params: { role } }).then((r) => {
      setUsers(r.data)
      setLoading(false)
    })
  }, [role])

  if (loading) return <div style={{ padding: 24, textAlign: 'center', color: '#aaa' }}>加载中...</div>

  const isAdmin = user?.role === 'admin'

  return (
    <div style={{ maxWidth: 700 }}>
      <Link to="/dashboard" style={{ color: '#888', fontSize: 13, textDecoration: 'none', marginBottom: 16, display: 'inline-block' }}>
        &larr; 返回仪表盘
      </Link>
      <h2 style={{ margin: '0 0 8px' }}>
        <span style={{
          display: 'inline-block', padding: '2px 10px', borderRadius: 4, fontSize: 14, fontWeight: 500, marginRight: 8,
          background: (ROLE_COLORS[role] || '#888') + '18', color: ROLE_COLORS[role] || '#888',
        }}>
          {ROLE_LABELS[role] || role}
        </span>
        用户列表
      </h2>
      <p style={{ color: '#999', marginBottom: 20 }}>共 {users.length} 人</p>

      <div style={{ background: '#fff', borderRadius: 8, border: '1px solid #eef0f2', overflow: 'hidden' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#fafafa' }}>
              <th style={th}>ID</th>
              <th style={th}>用户名</th>
              <th style={th}>角色</th>
              <th style={th}>状态</th>
              {isAdmin && <th style={th}>操作</th>}
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td style={td}>{u.id}</td>
                <td style={td}><strong>{u.username}</strong></td>
                <td style={td}>
                  <span style={{
                    padding: '2px 8px', borderRadius: 3, fontSize: 12, fontWeight: 500,
                    background: (ROLE_COLORS[u.role] || '#888') + '15', color: ROLE_COLORS[u.role] || '#888',
                  }}>
                    {ROLE_LABELS[u.role] || u.role}
                  </span>
                </td>
                <td style={td}>
                  <span style={{ fontSize: 12, color: u.is_active ? '#52c41a' : '#d32' }}>
                    {u.is_active ? '正常' : '已禁用'}
                  </span>
                </td>
                {isAdmin && (
                  <td style={td}>
                    <Link to={`/permissions`} style={{ fontSize: 12, color: '#1890ff', textDecoration: 'none' }}>
                      权限管理
                    </Link>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

const th = { padding: '10px 16px', textAlign: 'left', fontSize: 12, fontWeight: 600, color: '#888', borderBottom: '1px solid #eee' }
const td = { padding: '10px 16px', fontSize: 14, borderBottom: '1px solid #f5f5f5' }
