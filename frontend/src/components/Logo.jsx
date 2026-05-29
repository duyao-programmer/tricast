// TriCast Logo — 三角广播图标
export default function Logo({ size = 32, color = '#4fc3f7', dark = false }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* 三角形主体 */}
      <path d="M32 6L58 54H6L32 6Z" fill={color} opacity="0.2" stroke={color} strokeWidth="2.5" strokeLinejoin="round" />
      {/* 内部小三角 */}
      <path d="M32 18L46 44H18L32 18Z" fill={color} opacity="0.5" stroke={color} strokeWidth="1.5" strokeLinejoin="round" />
      {/* 信号波纹 左 */}
      <path d="M12 16 Q8 10 6 6" stroke={color} strokeWidth="2" strokeLinecap="round" fill="none" />
      <path d="M8 20 Q3 12 0 6" stroke={color} strokeWidth="1.5" strokeLinecap="round" fill="none" opacity="0.6" />
      {/* 信号波纹 右 */}
      <path d="M52 16 Q56 10 58 6" stroke={color} strokeWidth="2" strokeLinecap="round" fill="none" />
      <path d="M56 20 Q61 12 64 6" stroke={color} strokeWidth="1.5" strokeLinecap="round" fill="none" opacity="0.6" />
    </svg>
  )
}

// 侧栏品牌 Logo + 文字
export function BrandLogo() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '18px 16px' }}>
      <Logo size={28} color="#4fc3f7" />
      <span style={{ fontSize: 18, fontWeight: 700, color: '#eee', letterSpacing: 1 }}>
        TriCast
      </span>
    </div>
  )
}

// 登录/注册页 Logo + 文字
export function LoginLogo() {
  return (
    <div style={{ textAlign: 'center', marginBottom: 20 }}>
      <Logo size={56} color="#1a1a2e" />
      <h1 style={{ margin: '10px 0 0', fontSize: 28, fontWeight: 700, color: '#1a1a2e', letterSpacing: 2 }}>
        TriCast
      </h1>
    </div>
  )
}
