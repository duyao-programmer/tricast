import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function ProfilePage() {
  const { user } = useAuth()

  return (
    <div style={{ maxWidth: 500 }}>
      <h2>个人中心</h2>
      <div style={{ background: '#fff', borderRadius: 10, border: '1px solid #eef0f2', padding: '28px 32px', marginTop: 16 }}>
        <div style={row}>
          <span style={label}>用户名</span>
          <span style={value}>{user?.username}</span>
        </div>
        <div style={row}>
          <span style={label}>角色</span>
          <span style={value}>
            <span style={badge(user?.role)}>{user?.role}</span>
          </span>
        </div>
        <div style={{ marginTop: 20, paddingTop: 20, borderTop: '1px solid #f0f0f0', display: 'flex', gap: 12 }}>
          <Link to="/change-password" style={{ padding: '8px 20px', background: '#1a1a2e', color: '#fff', textDecoration: 'none', borderRadius: 5, fontSize: 14 }}>
            修改密码
          </Link>
        </div>
      </div>
    </div>
  )
}

const row = { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #f5f5f5' }
const label = { fontSize: 14, color: '#888' }
const value = { fontSize: 15, fontWeight: 600, color: '#333' }
const badge = (r) => ({
  padding: '2px 10px', borderRadius: 4, fontSize: 13, fontWeight: 500,
  background: r === 'admin' ? '#e8f0fe' : r === 'advanced' ? '#e8f5e9' : '#fff3e0',
  color: r === 'admin' ? '#1890ff' : r === 'advanced' ? '#52c41a' : '#fa8c16',
})
