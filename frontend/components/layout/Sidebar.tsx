// /frontend/components/layout/Sidebar.tsx
'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Home, Filter, Target, RefreshCw, Globe, MessageSquare, Zap, Cpu, LogOut, User, Menu, Star, PiggyBank, Rocket } from 'lucide-react'
import { useAuth } from '../auth/AuthProvider'
import { useEffect, useState } from 'react'
import ModelSelector from '../ai/ModelSelector'

const NAV = [
  { id: 'dashboard', icon: Home, label: 'Dashboard', href: '/dashboard' },
  { id: 'screener', icon: Filter, label: 'Screener', href: '/screener' },
  { id: 'mutual-funds', icon: PiggyBank, label: 'Mutual Funds', href: '/mutual-funds' },
  { id: 'ipo', icon: Rocket, label: 'IPO Tracker', href: '/ipo' },
  { id: 'portfolio', icon: Target, label: 'Portfolio', href: '/portfolio' },
  { id: 'watchlists', icon: Star, label: 'Watchlists', href: '/watchlists' },
  { id: 'backtest', icon: RefreshCw, label: 'Backtester', href: '/backtest' },
  { id: 'macro', icon: Globe, label: 'Macro', href: '/macro' },
  { id: 'ai', icon: MessageSquare, label: 'QuantAI', href: '/ai' },
]

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
}

export default function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const pathname = usePathname()
  const { user, logout } = useAuth()
  const [ollamaStatus, setOllamaStatus] = useState<'checking' | 'active' | 'unavailable'>('checking')

  useEffect(() => {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 2000)
    fetch('http://localhost:11434/api/tags', { signal: controller.signal })
      .then(() => setOllamaStatus('active'))
      .catch(() => setOllamaStatus('unavailable'))
      .finally(() => clearTimeout(timer))
  }, [])

  if (pathname === '/' || pathname === '/login' || pathname === '/register') return null

  const active = (href: string) => {
    return pathname.startsWith(href)
  }

  return (
    <div
      className="fixed left-0 top-0 bottom-0 bg-card border-r border-border flex flex-col z-40 transition-all duration-300"
      style={{ width: collapsed ? '64px' : '224px' }}
    >
      {/* Header */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-border">
        {!collapsed && (
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-brand rounded-lg flex items-center justify-center font-display font-bold text-white">
              Q
            </div>
            <div>
              <div className="font-display font-bold text-sm text-textPrimary leading-none">QuantAI</div>
              <div className="text-[10px] text-textMuted mt-1">NSE & BSE Analyzer</div>
            </div>
          </div>
        )}
        {collapsed && (
          <div className="w-8 h-8 bg-brand rounded-lg flex items-center justify-center font-display font-bold text-white mx-auto">
            Q
          </div>
        )}
        <button
          onClick={onToggle}
          className="p-1 hover:bg-elevated rounded text-textSub hover:text-textPrimary transition-colors hidden md:block"
        >
          <Menu className="w-4 h-4" />
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-4 px-2 space-y-1">
        {NAV.map(({ id, icon: Icon, label, href }) => {
          const isActive = active(href)
          return (
            <Link
              key={id}
              href={href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all duration-200 ${
                isActive
                  ? 'bg-brand/10 border border-brand/20 text-brand font-semibold'
                  : 'text-textSub hover:text-textPrimary hover:bg-elevated border border-transparent'
              }`}
              title={collapsed ? label : undefined}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {!collapsed && <span>{label}</span>}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-border space-y-4">
        {user ? (
          <button
            onClick={logout}
            className="w-full flex items-center gap-3 px-3 py-2 text-danger hover:bg-danger/10 rounded-lg text-sm transition-colors border border-transparent"
            title={collapsed ? "Logout" : undefined}
          >
            <LogOut className="w-4 h-4 flex-shrink-0" />
            {!collapsed && <span>Logout</span>}
          </button>
        ) : (
          <Link
            href="/login"
            className="w-full flex items-center gap-3 px-3 py-2 text-brand bg-brand/10 border border-brand/20 rounded-lg text-sm font-semibold transition-all hover:bg-brand/20"
            title={collapsed ? "Sign In" : undefined}
          >
            <User className="w-4 h-4 flex-shrink-0" />
            {!collapsed && <span>Sign In</span>}
          </Link>
        )}

        {!collapsed && ollamaStatus !== 'checking' && (
          <div className="space-y-2">
            <div className="flex items-center gap-1.5">
              <Cpu className={`w-3 h-3 ${ollamaStatus === 'active' ? 'text-success' : 'text-textMuted'}`} />
              <span className={`text-[10px] font-semibold tracking-wider font-mono uppercase ${ollamaStatus === 'active' ? 'text-success' : 'text-textMuted'}`}>
                Ollama • {ollamaStatus === 'active' ? 'Active' : 'Unavailable'}
              </span>
            </div>
            <ModelSelector compact />
          </div>
        )}
      </div>
    </div>
  )
}
