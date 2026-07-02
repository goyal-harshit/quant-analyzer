'use client'

import { useMemo } from 'react'
import Link from 'next/link'
import { Bell, Rocket, TrendingUp, TrendingDown, Calendar, RefreshCw, Activity } from 'lucide-react'
import { T } from '@/lib/stockData'
import { useIPOs, useTopGainersLosers, useMarketSummary } from '@/lib/hooks'

const card = (x: any = {}) => ({ background: T.card, border: `1px solid ${T.b}`, borderRadius: 10, ...x })

type Notif = {
  id: string
  icon: any
  color: string
  tag: string
  title: string
  body: string
  href?: string
}

export default function NotificationsPage() {
  const { data: ipos, isLoading: ipoLoading } = useIPOs()
  const { data: movers, isLoading: moversLoading } = useTopGainersLosers()
  const { data: indices } = useMarketSummary()

  const notifs = useMemo<Notif[]>(() => {
    const out: Notif[] = []

    // Open IPOs (actionable)
    for (const ipo of (ipos?.ipos || []).filter((i: any) => i.status === 'OPEN')) {
      out.push({
        id: `ipo-open-${ipo.id}`, icon: Rocket, color: T.green, tag: 'IPO OPEN',
        title: `${ipo.company_name} IPO is open`,
        body: `Price band ₹${ipo.price_band_low}–${ipo.price_band_high}${ipo.close_date ? ` · closes ${new Date(ipo.close_date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })}` : ''}`,
        href: '/ipo',
      })
    }
    // Upcoming IPOs (reminder)
    for (const ipo of (ipos?.ipos || []).filter((i: any) => i.status === 'UPCOMING').slice(0, 3)) {
      out.push({
        id: `ipo-up-${ipo.id}`, icon: Calendar, color: T.blue, tag: 'UPCOMING IPO',
        title: `${ipo.company_name} opens soon`,
        body: `Opens ${ipo.open_date ? new Date(ipo.open_date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }) : 'soon'} · ${ipo.ipo_type}`,
        href: '/ipo',
      })
    }
    // Top movers
    for (const g of (movers?.gainers || []).slice(0, 3)) {
      out.push({
        id: `gain-${g.ticker}`, icon: TrendingUp, color: T.green, tag: 'TOP GAINER',
        title: `${g.name || g.ticker} +${Number(g.change_pct).toFixed(2)}%`,
        body: `Trading at ₹${Number(g.price).toLocaleString('en-IN')} · ${g.sector || ''}`,
        href: `/stocks/${g.ticker}`,
      })
    }
    for (const l of (movers?.losers || []).slice(0, 3)) {
      out.push({
        id: `lose-${l.ticker}`, icon: TrendingDown, color: T.red, tag: 'TOP LOSER',
        title: `${l.name || l.ticker} ${Number(l.change_pct).toFixed(2)}%`,
        body: `Trading at ₹${Number(l.price).toLocaleString('en-IN')} · ${l.sector || ''}`,
        href: `/stocks/${l.ticker}`,
      })
    }
    // Volatility / VIX note
    const vix = (indices || []).find((i: any) => i.name === 'INDIA VIX')
    if (vix) {
      out.push({
        id: 'vix', icon: Activity, color: vix.change_pct >= 0 ? T.amber : T.green, tag: 'VOLATILITY',
        title: `India VIX at ${Number(vix.last).toFixed(2)}`,
        body: `${vix.change_pct >= 0 ? 'Up' : 'Down'} ${Math.abs(Number(vix.change_pct)).toFixed(2)}% — ${vix.change_pct >= 0 ? 'rising' : 'easing'} market fear`,
        href: '/macro',
      })
    }
    return out
  }, [ipos, movers, indices])

  // Only show the full-page spinner while we have NOTHING to show yet. Otherwise
  // render notifications as each source resolves — never hang the whole page on
  // the slowest/aborted query (e.g. the live IPO fetch or a cancelled movers call).
  const loading = (ipoLoading || moversLoading) && notifs.length === 0

  return (
    <div style={{ padding: '26px 30px', maxWidth: 820, fontFamily: T.sans }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
        <Bell style={{ width: 20, height: 20, color: T.blue }} />
        <div style={{ fontSize: 22, fontWeight: 700, color: T.text }}>Notifications</div>
        {notifs.length > 0 && (
          <span style={{ fontSize: 11, fontWeight: 700, color: T.blue, background: T.blue + '1a', padding: '2px 9px', borderRadius: 20 }}>
            {notifs.length}
          </span>
        )}
      </div>
      <div style={{ fontSize: 13, color: T.sub, marginBottom: 20 }}>
        Live market alerts, IPO reminders & big movers
      </div>

      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '80px 0', gap: 10 }}>
          <RefreshCw className="w-7 h-7 text-brand animate-spin" />
          <span style={{ fontSize: 13, color: T.sub }}>Loading notifications…</span>
        </div>
      ) : notifs.length === 0 ? (
        <div style={card({ padding: 50, textAlign: 'center', color: T.sub })}>
          <Bell style={{ width: 32, height: 32, color: T.muted, margin: '0 auto 12px' }} />
          <div style={{ fontSize: 14 }}>You&rsquo;re all caught up — no notifications right now.</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {notifs.map((n) => {
            const Inner = (
              <div style={card({ padding: '13px 16px', display: 'flex', alignItems: 'flex-start', gap: 13, cursor: n.href ? 'pointer' : 'default' })}>
                <div style={{ width: 36, height: 36, borderRadius: 9, background: n.color + '1a', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  <n.icon style={{ width: 17, height: 17, color: n.color }} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3 }}>
                    <span style={{ fontSize: 9.5, fontWeight: 700, color: n.color, letterSpacing: '0.05em' }}>{n.tag}</span>
                  </div>
                  <div style={{ fontSize: 13.5, fontWeight: 600, color: T.text }}>{n.title}</div>
                  <div style={{ fontSize: 12, color: T.sub, marginTop: 2 }}>{n.body}</div>
                </div>
              </div>
            )
            return n.href
              ? <Link key={n.id} href={n.href} style={{ textDecoration: 'none' }}>{Inner}</Link>
              : <div key={n.id}>{Inner}</div>
          })}
        </div>
      )}
    </div>
  )
}
