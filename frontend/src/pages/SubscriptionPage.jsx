import { useState, useEffect } from 'react'
import api from '../api/client'

const CATEGORY_NAMES = { global: '默认订阅', life: '生活通知', department: '部门通知' }

export default function SubscriptionPage() {
  const [tags, setTags] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  const load = async () => {
    try {
      const res = await api.get('/subscriptions')
      setTags(res.data.tags)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleToggle = async (tagKey, newVal) => {
    setSaving(true)
    try {
      await api.put('/subscriptions', { subscriptions: [{ tag_key: tagKey, subscribed: newVal }] })
      setTags((prev) => prev.map((t) => (t.tag_key === tagKey ? { ...t, subscribed: newVal } : t)))
      setMessage('已更新')
      setTimeout(() => setMessage(''), 1500)
    } finally {
      setSaving(false)
    }
  }

  const grouped = {}
  tags.forEach((t) => {
    grouped[t.category] = grouped[t.category] || []
    grouped[t.category].push(t)
  })

  if (loading) return <div style={{ padding: 24 }}>加载中...</div>

  return (
    <div>
      <h2>订阅管理</h2>
      <p style={{ color: '#888', marginBottom: 20 }}>
        选择你希望接收的消息类型。默认标签不可取消，部门标签可自由订阅。
      </p>
      {message && <div style={{ padding: '8px 16px', background: '#e8f5e9', borderRadius: 4, marginBottom: 12, color: '#2a7' }}>{message}</div>}

      {['global', 'life', 'department'].map((cat) => {
        const items = grouped[cat]
        if (!items || items.length === 0) return null
        return (
          <div key={cat} style={{ marginBottom: 24 }}>
            <h3 style={{ fontSize: 15, color: '#555', marginBottom: 12, borderBottom: '1px solid #eee', paddingBottom: 8 }}>
              {CATEGORY_NAMES[cat]}
            </h3>
            {items.map((tag) => (
              <div key={tag.tag_key} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid #f5f5f5' }}>
                <span style={{ fontSize: 14 }}>
                  {tag.tag_name}
                  {tag.is_default && <span style={{ color: '#999', fontSize: 12, marginLeft: 8 }}>（默认）</span>}
                </span>
                <button
                  onClick={() => handleToggle(tag.tag_key, !tag.subscribed)}
                  disabled={tag.is_default || saving}
                  style={{
                    padding: '4px 16px', fontSize: 13, borderRadius: 4, border: '1px solid #ddd',
                    background: tag.subscribed ? '#1a1a2e' : '#fff',
                    color: tag.subscribed ? '#fff' : '#888',
                    cursor: tag.is_default ? 'default' : 'pointer',
                    opacity: tag.is_default ? 0.5 : 1,
                  }}
                >
                  {tag.subscribed ? '已订阅' : '未订阅'}
                </button>
              </div>
            ))}
          </div>
        )
      })}
    </div>
  )
}
