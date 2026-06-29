'use client'

import Link from 'next/link'
import { User, Mail, Shield, LogOut, Cpu, Star, Target, Bell, LineChart, GitCompareArrows, Grid3x3 } from 'lucide-react'
import { T } from '@/lib/stockData'
import { useAuth } from '@/components/auth/AuthProvider'

const card = (x: any = {}) => ({ background: T.card, border: `1px solid ${T.b}`, borderRadius: 10, ...x })

export default function ProfilePage() {
  const { user, logout } = useAuth()

  if (!user) {
    return (
      <div style={{ padding: '26px 30px', maxWidth: 560, fontFamily: T.sans }}>
        <div style={card({ padding: 40, textAlign: 'center' })}>
          <User style={{ width: 36, height: 36, color: T.muted, margin: '0 auto 14px' }} />
          <div style={{ fontSize: 16, fontWeight: 700, color: T.text }}>You're not signed in</div>
          <div style={{ fontSize: 13, color: T.sub, margin: '8px 0 18px' }}>
            Sign in to manage your portfolios, watchlists and alerts.
          </div>
          <Link href="/login" style={{
            display: 'inline-block', padding: '9px 20px', background: T.blue, color: '#fff',
            borderRadius: 8, fontSize: 13, fontWeight: 600, textDecoration: 'none',
          }}>Sign In</Link>
        </div>
      </div>
    )
  }

  const username = user.email.split('@')[0]
  const initials = username.slice(0, 2).toUpperCase()

  return (
    <div style={{ padding: '26px 30px', maxWidth: 760, fontFamily: T.sans }}>
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 22, fontWeight: 700, color: T.text }}>Profile</div>
        <div style={{ fontSize: 13, color: T.sub, marginTop: 3 }}>Your account and preferences</div>
      </div>

      {/* Identity card */}
      <div style={card({ padding: '22px 24px', display: 'flex', alignItems: 'center', gap: 18, marginBottom: 16 })}>
        <div style={{
          width: 64, height: 64, borderRadius: '50%', background: T.blue + '22',
          border: `2px solid ${T.blue}`, display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 22, fontWeight: 700, color: T.blue, fontFamily: T.mono,
        }}>{initials}</div>
        <div>
          <div style={{ fontSize: 19, fontWeight: 700, color: T.text, textTransform: 'capitalize' }}>{username}</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: T.sub, marginTop: 4 }}>
            <Mail style={{ width: 13, height: 13 }} /> {user.email}
          </div>
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 5, marginTop: 8,
            fontSize: 11, fontWeight: 700, color: T.green, background: T.green + '1a',
            padding: '3px 10px', borderRadius: 20, textTransform: 'capitalize',
          }}>
            <Shield style={{ width: 11, height: 11 }} /> {user.plan} plan
          </span>
        </div>
      </div>

      {/* Account details */}
      <div style={card({ padding: '16px 22px', marginBottom: 16 })}>
        <div style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 12 }}>Account</div>
        {[
          ['User ID', `#${user.id}`],
          ['Email', user.email],
          ['Plan', user.plan],
          ['Status', user.is_active ? 'Active' : 'Inactive'],
        ].map(([k, v]) => (
          <div key={k as string} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid color-mix(in srgb, var(--border) 40%, transparent)', fontSize: 13 }}>
            <span style={{ color: T.sub }}>{k}</span>
            <span style={{ color: T.text, fontFamily: T.mono, textTransform: 'capitalize' }}>{v as string}</span>
          </div>
        ))}
      </div>

      {/* Your toolkit */}
      <div style={{ fontSize: 13, fontWeight: 600, color: T.text, margin: '4px 2px 10px' }}>Your toolkit</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 12, marginBottom: 16 }}>
        {[
          ['Portfolio', '/portfolio', Target, T.blue],
          ['Simulator', '/simulator', LineChart, T.green],
          ['Compare', '/compare', GitCompareArrows, T.blue],
          ['Sectors', '/sectors', Grid3x3, T.amber],
          ['Watchlists', '/watchlists', Star, T.amber],
          ['Notifications', '/notifications', Bell, T.purple],
        ].map(([label, href, Icon, c]: any) => (
          <Link key={label} href={href} style={{ textDecoration: 'none' }}>
            <div style={card({ padding: '14px 16px', display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' })}>
              <Icon style={{ width: 17, height: 17, color: c }} />
              <span style={{ fontSize: 13, color: T.text, fontWeight: 500 }}>{label}</span>
            </div>
          </Link>
        ))}
      </div>

      {/* System status */}
      <div style={card({ padding: '14px 22px', display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 })}>
        <Cpu style={{ width: 15, height: 15, color: T.green }} />
        <span style={{ fontSize: 12.5, color: T.sub }}>AI engine: <span style={{ color: T.green, fontWeight: 600 }}>Ollama (local) · active</span> — no API charges</span>
      </div>

      <button
        onClick={logout}
        style={{
          display: 'flex', alignItems: 'center', gap: 8, padding: '10px 18px',
          background: T.red + '1a', color: T.red, border: `1px solid ${T.red}40`,
          borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer',
        }}
      >
        <LogOut style={{ width: 15, height: 15 }} /> Sign Out
      </button>
    </div>
  )
}
