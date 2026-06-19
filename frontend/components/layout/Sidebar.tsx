'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Home, Filter, Target, RefreshCw, Globe, MessageSquare, Zap, Cpu, LogOut, User } from 'lucide-react'
import { useAuth } from '../auth/AuthProvider'
import { T } from '@/lib/stockData'

const NAV = [
  { id: 'dashboard', icon: Home, label: 'Dashboard', href: '/' },
  { id: 'screener', icon: Filter, label: 'Screener', href: '/screener' },
  { id: 'portfolio', icon: Target, label: 'Portfolio', href: '/portfolio' },
  { id: 'backtest', icon: RefreshCw, label: 'Backtester', href: '/backtest' },
  { id: 'macro', icon: Globe, label: 'Macro', href: '/macro' },
  { id: 'ai', icon: MessageSquare, label: 'QuantAI', href: '/ai' },
]

export default function Sidebar() {
  const pathname = usePathname()
  const { user, logout } = useAuth()

  const isAuthPage = pathname === '/login' || pathname === '/register'
  if (isAuthPage) return null

  const active = (href: string) => {
    if (href === '/') return pathname === '/'
    return pathname.startsWith(href)
  }

  return (
    <div style={{
      position: 'fixed', left: 0, top: 0, bottom: 0, width: 215,
      background: T.card, borderRight: `1px solid ${T.b}`,
      display: 'flex', flexDirection: 'column', zIndex: 100,
      fontFamily: T.sans,
    }}>
      <div style={{ padding: '18px 18px 14px', borderBottom: `1px solid ${T.b}` }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 34, height: 34, background: T.blue, borderRadius: 8,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Zap size={16} color="#fff" />
          </div>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: T.text }}>QuantAI</div>
            <div style={{ fontSize: 10, color: T.muted }}>NSE · BSE Analytics</div>
          </div>
        </div>
      </div>

      <nav style={{ flex: 1, padding: '10px 8px' }}>
        {NAV.map(({ id, icon: Icon, label, href }) => {
          const isActive = active(href)
          return (
            <Link
              key={id}
              href={href}
              style={{
                width: '100%', display: 'flex', alignItems: 'center', gap: 11,
                padding: '9px 12px', borderRadius: 7, marginBottom: 2,
                cursor: 'pointer', textDecoration: 'none',
                background: isActive ? `${T.blue}18` : 'transparent',
                border: `1px solid ${isActive ? T.blue + '44' : 'transparent'}`,
                color: isActive ? T.blue : T.sub, fontSize: 13,
                fontWeight: isActive ? 600 : 400,
              }}
            >
              <Icon size={15} />
              {label}
            </Link>
          )
        })}
      </nav>

      <div style={{ padding: '12px 16px', borderTop: `1px solid ${T.b}` }}>
        {user ? (
          <button
            onClick={logout}
            style={{
              width: '100%', display: 'flex', alignItems: 'center', gap: 10,
              padding: '8px 12px', borderRadius: 7, cursor: 'pointer',
              background: 'transparent', border: 'none', color: T.red,
              fontSize: 13, fontWeight: 500,
            }}
          >
            <LogOut size={15} />
            Logout
          </button>
        ) : (
          <Link
            href="/login"
            style={{
              width: '100%', display: 'flex', alignItems: 'center', gap: 10,
              padding: '8px 12px', borderRadius: 7, cursor: 'pointer',
              textDecoration: 'none', background: `${T.blue}22`,
              border: `1px solid ${T.blue}44`, color: T.blue,
              fontSize: 13, fontWeight: 600,
            }}
          >
            <User size={15} />
            Sign In
          </Link>
        )}
        <div style={{ marginTop: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 5 }}>
            <Cpu size={11} color={T.green} />
            <span style={{ fontSize: 10, color: T.green, fontWeight: 600, fontFamily: T.mono }}>
              OLLAMA · FREE LLM
            </span>
          </div>
          <div style={{ fontSize: 10, color: T.muted, lineHeight: 1.6 }}>
            100% open-source stack · No API costs · Educational use only
          </div>
        </div>
      </div>
    </div>
  )
}
