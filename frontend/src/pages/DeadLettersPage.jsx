import { useState, useEffect } from 'react'
import api from '../api/client'
import { usePermission } from '../hooks/usePermission'
import UnauthorizedPage from './UnauthorizedPage'

export default function DeadLettersPage() {
  const { canView } = usePermission()
  const [data, setData] = useState({ total: 0, items: [] })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/messages/dead')
      .then((res) => setData(res.data))
      .finally(() => setLoading(false))
  }, [])

  if (!canView('dead_letters')) return <UnauthorizedPage />
  if (loading) return <div>加载中...</div>

  return (
    <div>
      <h2>死信消息（共 {data.total} 条）</h2>
      {data.items.length === 0 ? (
        <p style={{ color: '#888' }}>暂无死信消息</p>
      ) : (
        data.items.map((item, i) => (
          <div key={i} style={{ marginBottom: 12, padding: 12, background: '#fff3f3', borderRadius: 6, border: '1px solid #fcc' }}>
            <p style={{ fontSize: 13, color: '#999', margin: '0 0 8px' }}>
              接收时间：{new Date(item.received_at).toLocaleString('zh-CN')} | 来源角色：{item.consumer_role}
            </p>
            <pre style={{ fontSize: 13, margin: 0, whiteSpace: 'pre-wrap' }}>
              {JSON.stringify(item.body, null, 2)}
            </pre>
          </div>
        ))
      )}
    </div>
  )
}
