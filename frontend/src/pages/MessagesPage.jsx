import { useState, useEffect, useRef, useCallback } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import api from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'

const TAG_COLORS = {
  all: '#1890ff', holiday: '#eb2f96', canteen: '#fa8c16', dormitory: '#722ed1',
  tech: '#13c2c2', admin: '#52c41a', hr: '#faad14', finance: '#f5222d',
}

export default function MessagesPage() {
  const { user } = useAuth()
  const toast = useToast()
  const [urlParams] = useSearchParams()
  const [items, setItems] = useState([])
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const [loading, setLoading] = useState(false)
  const [tags, setTags] = useState([])
  const [filter, setFilter] = useState('all')

  // 筛选（支持从 URL 参数初始化，用于仪表盘跳转）
  const [keyword, setKeyword] = useState('')
  const [startDate, setStartDate] = useState(urlParams.get('start_date') || '')
  const [endDate, setEndDate] = useState(urlParams.get('end_date') || '')
  const [selTags, setSelTags] = useState([])
  const publisherRole = urlParams.get('publisher_role') || ''
  const [showFilters, setShowFilters] = useState(!!(startDate || endDate || publisherRole))

  const isAdmin = user?.role === 'admin'
  const observer = useRef(null)

  useEffect(() => { api.get('/messages/tags').then((r) => setTags(r.data)) }, [])

  const load = useCallback(async (p = 1, append = false) => {
    setLoading(true)
    const params = { page: p, page_size: 20 }
    if (filter === 'subscribed') params.subscribed = true
    if (startDate) params.start_date = startDate
    if (endDate) params.end_date = endDate
    if (selTags.length > 0) params.filter_tags = selTags.join(',')
    if (keyword.trim()) params.keyword = keyword.trim()
    if (publisherRole) params.publisher_role = publisherRole
    try {
      const r = await api.get('/messages', { params })
      const newItems = r.data.items
      if (append) {
        setItems((prev) => [...prev, ...newItems])
      } else {
        setItems(newItems)
      }
      setHasMore(newItems.length >= 20)
      setPage(p)
    } finally { setLoading(false) }
  }, [filter, startDate, endDate, selTags, keyword])

  useEffect(() => { setPage(1); setItems([]); load(1) }, [filter, keyword])

  // 无限滚动
  const lastRef = useCallback((node) => {
    if (loading) return
    if (observer.current) observer.current.disconnect()
    observer.current = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && hasMore) {
        load(page + 1, true)
      }
    })
    if (node) observer.current.observe(node)
  }, [loading, hasMore, page, load])

  const handleSearch = () => { setPage(1); setItems([]); load(1) }
  const handleClear = () => { setKeyword(''); setStartDate(''); setEndDate(''); setSelTags([]); setFilter('all'); setPage(1); setItems([]); setTimeout(() => load(1), 0) }
  const toggleTag = (k) => setSelTags((prev) => prev.includes(k) ? prev.filter((t) => t !== k) : [...prev, k])

  const handleExport = async (fmt) => {
    try {
      const r = await api.get('/messages/export', { params: { fmt }, responseType: 'blob' })
      const url = window.URL.createObjectURL(new Blob([r.data]))
      const a = document.createElement('a'); a.href = url; a.download = `messages.${fmt}`; a.click()
      toast.success('导出成功')
    } catch { toast.error('导出失败') }
  }

  const tagName = (k) => { const t = tags.find((x) => x.tag_key === k); return t ? t.tag_name : k }

  return (
    <div style={{ maxWidth: 800 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, flexWrap: 'wrap', gap: 10 }}>
        <h2 style={{ margin: 0 }}>消息中心</h2>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {isAdmin && (
            <>
              <button onClick={() => handleExport('json')} style={outlineBtn}>导出 JSON</button>
              <button onClick={() => handleExport('csv')} style={outlineBtn}>导出 CSV</button>
            </>
          )}
          <button onClick={() => setShowFilters(!showFilters)} style={outlineBtn}>
            {showFilters ? '收起筛选' : '展开筛选'}
          </button>
          {!isAdmin && (
            <select value={filter} onChange={(e) => setFilter(e.target.value)}
              style={{ padding: '5px 12px', borderRadius: 5, border: '1px solid #ddd', fontSize: 13, background: '#fff' }}>
              <option value="all">全部消息</option>
              <option value="subscribed">仅已订阅</option>
            </select>
          )}
        </div>
      </div>

      {/* 搜索框 */}
      <div style={{ display: 'flex', gap: 8, marginBottom: showFilters ? 10 : 16 }}>
        <input type="text" placeholder="搜索标题或内容..."
          value={keyword} onChange={(e) => setKeyword(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          style={{ flex: 1, padding: '7px 12px', border: '1px solid #ddd', borderRadius: 5, fontSize: 14 }} />
        <button onClick={handleSearch} style={primaryBtn}>搜索</button>
      </div>

      {/* 筛选面板 */}
      {showFilters && (
        <div style={{ background: '#fafafa', borderRadius: 8, padding: '14px 18px', marginBottom: 16, border: '1px solid #eee', display: 'flex', flexWrap: 'wrap', gap: 16, alignItems: 'flex-end' }}>
          <div><label style={lbl}>开始日期</label><input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} style={inp} /></div>
          <div><label style={lbl}>结束日期</label><input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} style={inp} /></div>
          <div style={{ flex: 1, minWidth: 200 }}>
            <label style={lbl}>标签筛选</label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {tags.map((t) => (
                <label key={t.tag_key} style={{ display: 'flex', alignItems: 'center', gap: 3, padding: '3px 8px', borderRadius: 4, fontSize: 12, cursor: 'pointer', background: selTags.includes(t.tag_key) ? (TAG_COLORS[t.tag_key]||'#888')+'20' : '#fff', border: '1px solid '+(selTags.includes(t.tag_key)?TAG_COLORS[t.tag_key]||'#888':'#ddd') }}>
                  <input type="checkbox" checked={selTags.includes(t.tag_key)} onChange={() => toggleTag(t.tag_key)} style={{ margin: 0 }} />{t.tag_name}
                </label>
              ))}
            </div>
          </div>
          <button onClick={handleClear} style={outlineBtn}>清除</button>
        </div>
      )}

      {/* 消息列表 */}
      {items.length === 0 && !loading ? (
        <div style={{ textAlign: 'center', padding: 60, color: '#999' }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>&#128236;</div>
          <p>{keyword ? '未搜索到相关消息' : '暂无消息'}</p>
        </div>
      ) : (
        <div>
          {items.map((msg, i) => (
            <Link to={`/messages/${msg.id}`} key={msg.id} ref={i === items.length - 1 ? lastRef : null}
              style={{ textDecoration: 'none', color: 'inherit', display: 'block' }}>
              <div style={{ background: '#fff', borderRadius: 8, padding: '16px 20px', marginBottom: 10, border: '1px solid #eef0f2' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <h3 style={{ margin: '0 0 6px', fontSize: 15, fontWeight: 600, color: '#1a1a2e' }}>{msg.title}</h3>
                  {msg.tags?.length > 0 && (
                    <div style={{ display: 'flex', gap: 4, flexShrink: 0, marginLeft: 12 }}>
                      {msg.tags.map((t) => (
                        <span key={t} style={{ padding: '1px 6px', borderRadius: 3, fontSize: 10, fontWeight: 500, background: (TAG_COLORS[t]||'#888')+'18', color: TAG_COLORS[t]||'#888' }}>{tagName(t)}</span>
                      ))}
                    </div>
                  )}
                </div>
                {msg.content && (
                  <p style={{ margin: '0 0 8px', color: '#666', fontSize: 13, lineHeight: 1.5 }}>
                    {msg.content.length > 80 ? msg.content.slice(0, 80) + '...' : msg.content}
                  </p>
                )}
                <div style={{ display: 'flex', gap: 16, color: '#aaa', fontSize: 12 }}>
                  {msg.publisher && <span>{msg.publisher}</span>}
                  {msg.published_at && <span>{new Date(msg.published_at).toLocaleString('zh-CN')}</span>}
                </div>
              </div>
            </Link>
          ))}
          {loading && <div style={{ textAlign: 'center', padding: 16, color: '#aaa' }}>加载中...</div>}
        </div>
      )}
    </div>
  )
}

const lbl = { display: 'block', fontSize: 12, color: '#888', marginBottom: 4 }
const inp = { padding: '5px 8px', border: '1px solid #ddd', borderRadius: 4, fontSize: 13 }
const primaryBtn = { padding: '6px 18px', background: '#1a1a2e', color: '#fff', border: 'none', borderRadius: 5, cursor: 'pointer', fontSize: 13 }
const outlineBtn = { padding: '5px 14px', background: '#fff', color: '#555', border: '1px solid #ddd', borderRadius: 4, cursor: 'pointer', fontSize: 13 }
