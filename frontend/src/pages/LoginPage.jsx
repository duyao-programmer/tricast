import { Link } from 'react-router-dom'
import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { LoginLogo } from '../components/Logo'
import s from '../styles/login.module.css'

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  // 已登录则直接跳转
  if (isAuthenticated) {
    const redirect = params.get('redirect') || '/dashboard'
    navigate(redirect, { replace: true })
    return null
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await login(username, password)
      const redirect = params.get('redirect') || '/dashboard'
      navigate(redirect, { replace: true })
    } catch (err) {
      setError(err.response?.data?.detail || '登录失败，请检查用户名和密码')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className={s.container}>
      <form className={s.form} onSubmit={handleSubmit}>
        <LoginLogo />
        {error && <div className={s.error}>{error}</div>}
        <input
          className={s.input}
          type="text"
          placeholder="用户名"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoFocus
        />
        <input
          className={s.input}
          type="password"
          placeholder="密码"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button className={s.btn} type="submit" disabled={submitting}>
          {submitting ? '登录中...' : '登 录'}
        </button>
        <p className={s.hint}>
          没有账号？<Link to="/register">去注册</Link>
        </p>
      </form>
    </div>
  )
}
