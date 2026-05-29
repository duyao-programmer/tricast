import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'
import { useToast } from '../context/ToastContext'

export default function ChangePasswordPage() {
  const toast = useToast()
  const navigate = useNavigate()
  const [oldPw, setOldPw] = useState('')
  const [newPw, setNewPw] = useState('')
  const [confirm, setConfirm] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (newPw !== confirm) { toast.error('两次输入的新密码不一致'); return }
    setSubmitting(true)
    try {
      await api.post('/auth/change-password', { old_password: oldPw, new_password: newPw })
      toast.success('密码修改成功')
      navigate('/profile')
    } catch (err) {
      toast.error(err.response?.data?.detail || '修改失败')
    } finally { setSubmitting(false) }
  }

  return (
    <div style={{ maxWidth: 440 }}>
      <h2>修改密码</h2>
      <form onSubmit={handleSubmit} style={{ background: '#fff', borderRadius: 10, border: '1px solid #eef0f2', padding: '28px 32px', marginTop: 16 }}>
        <div style={f}>
          <label style={lbl}>旧密码</label>
          <input type="password" value={oldPw} onChange={(e) => setOldPw(e.target.value)} style={inp} required />
        </div>
        <div style={f}>
          <label style={lbl}>新密码</label>
          <input type="password" value={newPw} onChange={(e) => setNewPw(e.target.value)} style={inp} required minLength={8} placeholder="至少8位，含大小写字母和数字" />
        </div>
        <div style={f}>
          <label style={lbl}>确认新密码</label>
          <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} style={inp} required />
        </div>
        <button type="submit" disabled={submitting} style={{ width: '100%', padding: '10px', background: '#1a1a2e', color: '#fff', border: 'none', borderRadius: 5, fontSize: 15, cursor: 'pointer', marginTop: 8 }}>
          {submitting ? '修改中...' : '确认修改'}
        </button>
      </form>
    </div>
  )
}

const f = { marginBottom: 16 }
const lbl = { display: 'block', marginBottom: 6, fontSize: 13, color: '#666', fontWeight: 500 }
const inp = { width: '100%', padding: '8px 12px', border: '1px solid #ddd', borderRadius: 5, fontSize: 14, boxSizing: 'border-box' }
