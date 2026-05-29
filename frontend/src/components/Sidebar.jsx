import { NavLink } from 'react-router-dom'
import { usePermission } from '../hooks/usePermission'
import { BrandLogo } from './Logo'
import s from '../styles/layout.module.css'

const menuItems = [
  { key: 'dashboard',                   label: '仪表盘',     path: '/dashboard' },
  { key: 'message_list',                label: '消息列表',   path: '/messages' },
  { key: 'subscription_management',     label: '订阅管理',   path: '/subscriptions' },
  { key: 'message_stats',               label: '耗时统计',   path: '/stats' },
  { key: 'dead_letters',                label: '死信查看',   path: '/dead-letters' },
  { key: 'publish_message',             label: '发布消息',   path: '/publish' },
  { key: 'role_permission_management',  label: '角色权限',   path: '/admin/roles' },
  { key: 'user_permission_management',  label: '用户权限',   path: '/permissions' },
]

export default function Sidebar() {
  const { canView } = usePermission()

  return (
    <nav className={s.sidebar}>
      <BrandLogo />
      <ul className={s.nav}>
        {menuItems
          .filter((item) => canView(item.key))
          .map((item) => (
            <li key={item.key}>
              <NavLink
                to={item.path}
                className={({ isActive }) => isActive ? s.active : ''}
              >
                {item.label}
              </NavLink>
            </li>
          ))}
      </ul>
      <div style={{ marginTop: 'auto', borderTop: '1px solid #333', paddingTop: 8 }}>
        <NavLink to="/profile" className={({ isActive }) => isActive ? s.active : ''} style={{ display: 'block', padding: '10px 20px', color: '#aaa', textDecoration: 'none', fontSize: 14 }}>
          个人中心
        </NavLink>
      </div>
    </nav>
  )
}
