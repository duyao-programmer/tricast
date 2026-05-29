import { Link } from 'react-router-dom'

export default function UnauthorizedPage({ message = '您没有访问此页面的权限' }) {
  return (
    <div style={{ textAlign: 'center', padding: 60 }}>
      <h2>权限不足</h2>
      <p style={{ color: '#666' }}>{message}</p>
      <Link to="/dashboard">返回首页</Link>
    </div>
  )
}
