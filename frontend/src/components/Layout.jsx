import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import { useAuth } from '../context/AuthContext'
import s from '../styles/layout.module.css'

export default function Layout() {
  const { user, logout } = useAuth()

  return (
    <div className={s.layout}>
      <Sidebar />
      <div className={s.main}>
        <header className={s.header}>
          <span className={s.userInfo}>
            {user?.username}（{user?.role}）
          </span>
          <button className={s.logoutBtn} onClick={logout}>登出</button>
        </header>
        <main className={s.content}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
