import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api/client'
import { useAuth } from '../context/AuthContext'
import { LoginLogo } from '../components/Logo'
import s from '../styles/login.module.css'

export default function RegisterPage() {
  const { isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (isAuthenticated) {
    navigate('/dashboard', { replace: true })
    return null
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (password !== confirm) {
      setError('两次输入的密码不一致')
      return
    }

    setSubmitting(true)
    try {
      await api.post('/auth/register', { username, password })
      navigate('/login?registered=1', { replace: true })
    } catch (err) {
      const detail = err.response?.data?.detail
      if (Array.isArray(detail)) {
        setError(detail.map((d) => d.msg).join('; '))
      } else {
        setError(detail || '注册失败，请重试')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className={s.container}>
      <form className={s.form} onSubmit={handleSubmit}>
        <LoginLogo />
        <p style={{ textAlign: 'center', color: '#999', fontSize: 14, marginTop: 4 }}>注册新账号</p>
        {error && <div className={s.error}>{error}</div>}
        <input
          className={s.input}
          type="text"
          placeholder="用户名"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoFocus
          minLength={3}
          maxLength={50}
        />
        <input
          className={s.input}
          type="password"
          placeholder="密码（至少8位，含大小写字母和数字）"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          minLength={8}
        />
        <input
          className={s.input}
          type="password"
          placeholder="确认密码"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
        />
        <button className={s.btn} type="submit" disabled={submitting}>
          {submitting ? '注册中...' : '注 册'}
        </button>
        <p className={s.hint}>
          已有账号？<Link to="/login">去登录</Link>
        </p>
      </form>
    </div>
  )
}
