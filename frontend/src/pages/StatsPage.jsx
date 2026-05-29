import { useState, useEffect } from 'react'
import api from '../api/client'
import { usePermission } from '../hooks/usePermission'
import UnauthorizedPage from './UnauthorizedPage'

export default function StatsPage() {
  const { canView } = usePermission()
  const [stats, setStats] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/messages/stats')
      .then((res) => setStats(res.data))
      .finally(() => setLoading(false))
  }, [])

  if (!canView('message_stats')) return <UnauthorizedPage />
  if (loading) return <div>加载中...</div>

  return (
    <div>
      <h2>消息耗时统计（最近 10 条）</h2>
      {stats.length === 0 ? (
        <p style={{ color: '#888' }}>暂无数据</p>
      ) : (
        stats.map((item) => (
          <div key={item.message_id} style={{ marginBottom: 24, padding: 16, background: '#fafafa', borderRadius: 6 }}>
            <h3 style={{ margin: '0 0 12px' }}>#{item.message_id} {item.title}</h3>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#f0f0f0' }}>
                  <th style={tdStyle}>通道</th>
                  <th style={tdStyle}>次数</th>
                  <th style={tdStyle}>最小 (ms)</th>
                  <th style={tdStyle}>最大 (ms)</th>
                  <th style={tdStyle}>平均 (ms)</th>
                </tr>
              </thead>
              <tbody>
                {item.channels.map((ch) => (
                  <tr key={ch.channel}>
                    <td style={tdStyle}>{ch.channel}</td>
                    <td style={tdStyle}>{ch.count}</td>
                    <td style={tdStyle}>{ch.min_ms ?? '-'}</td>
                    <td style={tdStyle}>{ch.max_ms ?? '-'}</td>
                    <td style={tdStyle}>{ch.avg_ms ?? '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))
      )}
    </div>
  )
}

const tdStyle = { padding: '6px 12px', borderBottom: '1px solid #eee', textAlign: 'left' }
