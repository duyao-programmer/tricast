import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'
import { usePermission } from '../hooks/usePermission'
import UnauthorizedPage from './UnauthorizedPage'

export default function PublishPage() {
  const { canView } = usePermission()
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [secretKey, setSecretKey] = useState('')
  const [secretVal, setSecretVal] = useState('')
  const [selectedTags, setSelectedTags] = useState([])
  const [allTags, setAllTags] = useState([])
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    api.get('/messages/tags').then((res) => setAllTags(res.data))
  }, [])

  if (!canView('publish_message')) return <UnauthorizedPage />

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const body = { title, content }
      if (secretKey || secretVal) {
        body.secret_data = { [secretKey]: secretVal }
      }
      if (selectedTags.length > 0) {
        body.tags = selectedTags
      }
      const res = await api.post('/publish', body)
      setResult(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || '发布失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div>
      <h2>发布消息</h2>
      {result ? (
        <div style={{ padding: 24, background: '#f0fff0', borderRadius: 8, textAlign: 'center' }}>
          <p style={{ fontSize: 18, color: '#2a7' }}>发布成功！</p>
          <p>消息 ID：{result.message_id}</p>
          <button onClick={() => navigate(`/messages/${result.message_id}`)}>查看消息</button>
          <button style={{ marginLeft: 12 }} onClick={() => { setResult(null); setTitle(''); setContent(''); setSecretKey(''); setSecretVal(''); setSelectedTags([]) }}>
            再发一条
          </button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} style={{ maxWidth: 600 }}>
          {error && <div style={{ color: 'red', marginBottom: 12 }}>{error}</div>}
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>标题 *</label>
            <input style={inputStyle} value={title} onChange={(e) => setTitle(e.target.value)} required maxLength={200} placeholder="输入消息标题" />
          </div>
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>内容 *</label>
            <textarea style={{ ...inputStyle, height: 120 }} value={content} onChange={(e) => setContent(e.target.value)} required maxLength={5000} placeholder="输入消息正文" />
          </div>
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>消息标签</label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {allTags.map((tag) => (
                <label key={tag.tag_key} style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 10px', border: '1px solid #ddd', borderRadius: 4, fontSize: 13, cursor: 'pointer', background: selectedTags.includes(tag.tag_key) ? '#e8f0fe' : '#fff' }}>
                  <input
                    type="checkbox"
                    checked={selectedTags.includes(tag.tag_key)}
                    onChange={(e) => {
                      if (e.target.checked) setSelectedTags([...selectedTags, tag.tag_key])
                      else setSelectedTags(selectedTags.filter((t) => t !== tag.tag_key))
                    }}
                  />
                  {tag.tag_name}
                </label>
              ))}
            </div>
          </div>
          <div style={{ marginBottom: 16 }}>
            <label style={labelStyle}>加密数据（可选）</label>
            <div style={{ display: 'flex', gap: 8 }}>
              <input style={{ ...inputStyle, flex: 1 }} value={secretKey} onChange={(e) => setSecretKey(e.target.value)} placeholder="key" />
              <input style={{ ...inputStyle, flex: 1 }} value={secretVal} onChange={(e) => setSecretVal(e.target.value)} placeholder="value" />
            </div>
          </div>
          <button type="submit" disabled={submitting} style={{
            padding: '10px 32px', background: '#333', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 15,
          }}>
            {submitting ? '发布中...' : '发布消息'}
          </button>
        </form>
      )}
    </div>
  )
}

const labelStyle = { display: 'block', marginBottom: 6, fontWeight: 600, fontSize: 14 }
const inputStyle = { width: '100%', padding: '8px 12px', border: '1px solid #ddd', borderRadius: 4, fontSize: 14, boxSizing: 'border-box' }
