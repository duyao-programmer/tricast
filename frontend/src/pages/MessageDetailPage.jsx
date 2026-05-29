import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import api from '../api/client'

const TAG_COLORS = {
  all: '#1890ff', holiday: '#eb2f96', canteen: '#fa8c16', dormitory: '#722ed1',
  tech: '#13c2c2', admin: '#52c41a', hr: '#faad14', finance: '#f5222d',
}

export default function MessageDetailPage() {
  const { id } = useParams()
  const [msg, setMsg] = useState(null)
  const [tags, setTags] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.get(`/messages/${id}`),
      api.get('/messages/tags'),
    ]).then(([mr, tr]) => {
      setMsg(mr.data)
      setTags(tr.data)
    }).finally(() => setLoading(false))
  }, [id])

  if (loading) return <div style={{ padding: 24, textAlign: 'center' }}>加载中...</div>
  if (!msg) return <div style={{ padding: 24, textAlign: 'center', color: '#999' }}>消息不存在</div>

  const tagName = (key) => { const t = tags.find((x) => x.tag_key === key); return t ? t.tag_name : key }

  return (
    <div style={{ maxWidth: 780, margin: '0 auto' }}>
      <Link to="/messages" style={{ color: '#888', fontSize: 13, textDecoration: 'none', marginBottom: 20, display: 'inline-block' }}>
        &larr; 返回消息列表
      </Link>

      {/* 消息卡片 */}
      <div style={{ background: '#fff', borderRadius: 10, border: '1px solid #eef0f2', overflow: 'hidden' }}>
        {/* 头部 */}
        <div style={{ padding: '28px 32px 20px', borderBottom: '1px solid #f0f0f0' }}>
          <h1 style={{ margin: '0 0 14px', fontSize: 20, fontWeight: 700, color: '#1a1a2e', lineHeight: 1.4 }}>
            {msg.title}
          </h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: 20, color: '#999', fontSize: 13 }}>
            {msg.publisher && <span style={metaItem}>发布人：{msg.publisher}</span>}
            {msg.published_at && <span style={metaItem}>{new Date(msg.published_at).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}</span>}
          </div>
          {msg.tags && msg.tags.length > 0 && (
            <div style={{ marginTop: 12, display: 'flex', gap: 6 }}>
              {msg.tags.map((t) => (
                <span key={t} style={{
                  padding: '2px 10px', borderRadius: 3, fontSize: 11, fontWeight: 500,
                  background: (TAG_COLORS[t] || '#888') + '15', color: TAG_COLORS[t] || '#888',
                  border: '1px solid ' + ((TAG_COLORS[t] || '#888') + '30'),
                }}>{tagName(t)}</span>
              ))}
            </div>
          )}
        </div>

        {/* 正文 */}
        <div style={{ padding: '28px 32px', borderBottom: msg.secret_data || (msg.receipts?.length > 0) ? '1px solid #f0f0f0' : 'none' }}>
          <p style={{ margin: 0, fontSize: 15, lineHeight: 1.85, color: '#333', whiteSpace: 'pre-wrap' }}>
            {msg.content}
          </p>
        </div>

        {/* 加密数据 */}
        {msg.secret_data && (
          <div style={{ padding: '20px 32px', borderBottom: msg.receipts?.length > 0 ? '1px solid #f0f0f0' : 'none', background: '#fafafa' }}>
            <h4 style={{ margin: '0 0 10px', fontSize: 13, color: '#888', fontWeight: 500 }}>附件 / 加密数据</h4>
            <pre style={{
              margin: 0, padding: '14px 18px', background: '#fff', borderRadius: 6,
              border: '1px solid #eee', fontSize: 13, lineHeight: 1.6, overflow: 'auto',
              fontFamily: 'SF Mono, Consolas, monospace',
            }}>
              {JSON.stringify(msg.secret_data, null, 2)}
            </pre>
          </div>
        )}

        {/* 消费回执 */}
        {msg.receipts && msg.receipts.length > 0 && (
          <div style={{ padding: '20px 32px', background: '#fafafa' }}>
            <h4 style={{ margin: '0 0 10px', fontSize: 13, color: '#888', fontWeight: 500 }}>消费回执</h4>
            <table style={{ width: '100%', borderCollapse: 'collapse', background: '#fff', borderRadius: 6, overflow: 'hidden', border: '1px solid #eee' }}>
              <thead>
                <tr style={{ background: '#f5f5f5' }}>
                  <th style={th}>消费角色</th>
                  <th style={th}>通道</th>
                  <th style={th}>处理耗时</th>
                  <th style={th}>回执时间</th>
                </tr>
              </thead>
              <tbody>
                {msg.receipts.map((r, i) => (
                  <tr key={i}>
                    <td style={td}><span style={roleBadge(r.consumer_role)}>{r.consumer_role}</span></td>
                    <td style={td}>{r.channel}</td>
                    <td style={td}>{r.processing_time_ms != null ? r.processing_time_ms + ' ms' : '-'}</td>
                    <td style={td}>{r.received_at ? new Date(r.received_at).toLocaleString('zh-CN') : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

const metaItem = {
  display: 'flex', alignItems: 'center', gap: 4,
}

const th = { padding: '10px 14px', textAlign: 'left', fontSize: 12, fontWeight: 600, color: '#666', borderBottom: '1px solid #eee' }
const td = { padding: '10px 14px', fontSize: 13, borderBottom: '1px solid #f5f5f5', color: '#555' }

const ROLE_COLORS = { admin: '#1890ff', advanced: '#52c41a', regular: '#fa8c16' }
const roleBadge = (role) => ({
  padding: '2px 8px', borderRadius: 3, fontSize: 11, fontWeight: 500,
  background: (ROLE_COLORS[role] || '#888') + '15', color: ROLE_COLORS[role] || '#888',
})
