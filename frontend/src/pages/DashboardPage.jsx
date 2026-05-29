import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import api from '../api/client'

const TAG_COLORS = {
  all: '#1890ff', holiday: '#eb2f96', canteen: '#fa8c16', dormitory: '#722ed1',
  tech: '#13c2c2', admin: '#52c41a', hr: '#faad14', finance: '#f5222d',
}

export default function DashboardPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [stats, setStats] = useState(null)
  const isAdmin = user?.role === 'admin'

  useEffect(() => { api.get('/dashboard/stats').then((r) => setStats(r.data)) }, [])

  if (!stats) return <div style={{ padding: 24, textAlign: 'center', color: '#aaa' }}>加载中...</div>

  const today = new Date().toISOString().slice(0, 10)
  const maxTag = stats.tag_stats?.[0]?.count || 1
  const maxDaily = Math.max(1, ...(stats.recent_daily || []).map((d) => d.count))

  return (
    <div style={{ maxWidth: 900 }}>
      <h2 style={{ margin: '0 0 4px' }}>仪表盘</h2>
      <p style={{ margin: '0 0 28px', color: '#999', fontSize: 14 }}>
        {user?.username}（{user?.role}），欢迎回来。点击卡片可查看详情。
      </p>

      {/* ===== 统计卡片 ===== */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 28, flexWrap: 'wrap' }}>
        <Card label="总消息数" value={stats.total_messages} unit="条" color="#1890ff"
          onClick={() => navigate('/messages')} />
        <Card label="今日发布" value={stats.today_messages} unit="条" color="#52c41a"
          onClick={() => navigate(`/messages?start_date=${today}&end_date=${today}`)} />
        {isAdmin && Object.entries(stats.users_by_role || {}).map(([role, count]) => (
          <Card key={role} label={role} value={count} unit="人" color="#fa8c16"
            onClick={() => navigate(`/users/${role}`)} />
        ))}
      </div>

      {/* ===== 标签统计 + 7天趋势 ===== */}
      <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
        <div style={panel}>
          <h3 style={panelTitle}>标签使用分布</h3>
          {(stats.tag_stats || []).length === 0 ? (
            <p style={{ color: '#bbb', fontSize: 13, textAlign: 'center', padding: 20 }}>暂无数据</p>
          ) : (
            stats.tag_stats.map((t) => (
              <div key={t.tag_key} style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
                <span style={{ width: 72, fontSize: 13, color: '#555', textAlign: 'right' }}>{t.tag_name}</span>
                <div style={{ flex: 1, height: 22, background: '#f0f2f5', borderRadius: 11, overflow: 'hidden' }}>
                  <div style={{
                    height: '100%', borderRadius: 11, background: TAG_COLORS[t.tag_key] || '#aaa',
                    width: Math.max(10, Math.round((t.count / maxTag) * 100)) + '%',
                    transition: 'width 0.4s ease',
                  }} />
                </div>
                <span style={{ width: 28, fontSize: 12, color: '#999' }}>{t.count}</span>
              </div>
            ))
          )}
        </div>

        <div style={panel}>
          <h3 style={panelTitle}>最近 7 天</h3>
          {(stats.recent_daily || []).length === 0 ? (
            <p style={{ color: '#bbb', fontSize: 13, textAlign: 'center', padding: 20 }}>暂无数据</p>
          ) : (
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 14, height: 160, padding: '0 4px' }}>
              {stats.recent_daily.map((d) => {
                const h = Math.max(8, Math.round((d.count / maxDaily) * 140))
                return (
                  <div key={d.date} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: '#333' }}>{d.count}</span>
                    <div style={{ width: '100%', maxWidth: 44, background: '#1890ff', borderRadius: '4px 4px 0 0', height: h, minHeight: 4, transition: 'height 0.3s' }} />
                    <span style={{ fontSize: 11, color: '#aaa' }}>{d.date.slice(5)}</span>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function Card({ label, value, unit, color, onClick }) {
  return (
    <div onClick={onClick} style={{
      background: '#fff', borderRadius: 10, border: '1px solid #eef0f2',
      padding: '20px 24px', minWidth: 140, flex: '1 1 auto', cursor: 'pointer',
      transition: 'box-shadow 0.15s, transform 0.15s',
    }}
      onMouseEnter={(e) => { e.currentTarget.style.boxShadow = '0 2px 12px rgba(0,0,0,0.1)'; e.currentTarget.style.transform = 'translateY(-1px)' }}
      onMouseLeave={(e) => { e.currentTarget.style.boxShadow = 'none'; e.currentTarget.style.transform = 'none' }}
    >
      <div style={{ fontSize: 13, color: '#999', marginBottom: 8 }}>{label}</div>
      <div style={{ fontSize: 32, fontWeight: 700, color, lineHeight: 1 }}>
        {value ?? '-'}
        <span style={{ fontSize: 14, fontWeight: 400, marginLeft: 4 }}>{unit}</span>
      </div>
    </div>
  )
}

const panel = {
  flex: '1 1 330px', background: '#fff', borderRadius: 10,
  border: '1px solid #eef0f2', padding: '20px 24px',
}
const panelTitle = { margin: '0 0 18px', fontSize: 15, fontWeight: 600 }
