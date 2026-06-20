'use client'

import { useState } from 'react'
import { Rocket, RefreshCw, TrendingUp, TrendingDown, Calendar, Building2 } from 'lucide-react'
import { T, fI } from '@/lib/stockData'
import { useIPOs } from '@/lib/hooks'
import type { IPOItem } from '@/lib/api'

const card = (x: any = {}) => ({ background: T.card, border: `1px solid ${T.b}`, borderRadius: 10, ...x })

const TABS = [
  { id: 'OPEN', label: 'Open Now' },
  { id: 'UPCOMING', label: 'Upcoming' },
  { id: 'LISTED', label: 'Recently Listed' },
  { id: 'SME', label: 'SME' },
]

function statusPill(status: string) {
  const map: Record<string, string> = { OPEN: T.green, UPCOMING: T.blue, LISTED: T.purple, CLOSED: T.muted }
  const c = map[status] || T.muted
  return (
    <span style={{ fontSize: 10, fontWeight: 700, color: c, background: c + '22', padding: '2px 8px', borderRadius: 20, letterSpacing: '0.04em' }}>
      {status}
    </span>
  )
}

function fmtDate(d?: string | null) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })
}

export default function IPOPage() {
  const [tab, setTab] = useState('OPEN')
  const [refreshSeed, setRefreshSeed] = useState(0)
  const { data, isLoading, isFetching } = useIPOs(refreshSeed)

  const all: IPOItem[] = data?.ipos || []
  const list = tab === 'SME'
    ? all.filter((i) => i.ipo_type === 'SME')
    : all.filter((i) => i.status === tab)

  const counts: Record<string, number> = {
    OPEN: all.filter((i) => i.status === 'OPEN').length,
    UPCOMING: all.filter((i) => i.status === 'UPCOMING').length,
    LISTED: all.filter((i) => i.status === 'LISTED').length,
    SME: all.filter((i) => i.ipo_type === 'SME').length,
  }

  return (
    <div style={{ padding: '26px 30px', maxWidth: 1200, fontFamily: T.sans }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <div style={{ fontSize: 22, fontWeight: 700, color: T.text }}>IPO & SME Tracker</div>
          <div style={{ fontSize: 13, color: T.sub, marginTop: 3 }}>
            Mainboard & SME issues · subscription, GMP & listing performance
          </div>
        </div>
        <button onClick={() => setRefreshSeed((s) => s + 1)}
          style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px', background: T.el, border: `1px solid ${T.b}`, borderRadius: 6, fontSize: 12, color: T.sub, cursor: 'pointer' }}>
          <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 18 }}>
        {TABS.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)}
            style={{
              padding: '8px 16px', borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer',
              background: tab === t.id ? T.blue : T.card,
              color: tab === t.id ? '#fff' : T.sub,
              border: `1px solid ${tab === t.id ? T.blue : T.b}`,
            }}>
            {t.label}
            <span style={{ marginLeft: 7, fontSize: 11, opacity: 0.8 }}>{counts[t.id] ?? 0}</span>
          </button>
        ))}
      </div>

      {isLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '90px 0', gap: 10 }}>
          <RefreshCw className="w-8 h-8 text-brand animate-spin" />
          <span style={{ fontSize: 13, color: T.sub }}>Loading IPO data…</span>
        </div>
      ) : list.length === 0 ? (
        <div style={card({ padding: 50, textAlign: 'center', color: T.sub })}>
          <Rocket style={{ width: 32, height: 32, color: T.muted, margin: '0 auto 12px' }} />
          <div style={{ fontSize: 14 }}>No IPOs in this category right now.</div>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: 14 }}>
          {list.map((ipo) => <IPOCard key={ipo.id} ipo={ipo} />)}
        </div>
      )}
    </div>
  )
}

function IPOCard({ ipo }: { ipo: IPOItem }) {
  const gain = ipo.listing_gain_pct
  return (
    <div style={card({ padding: '15px 17px' })}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
          <div style={{ width: 34, height: 34, borderRadius: 8, background: T.el, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Building2 style={{ width: 16, height: 16, color: T.blue }} />
          </div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: T.text, lineHeight: 1.2 }}>{ipo.company_name}</div>
            <div style={{ fontSize: 11, color: T.muted, marginTop: 2 }}>
              {ipo.symbol || '—'} · {ipo.ipo_type}{ipo.exchange ? ` · ${ipo.exchange}` : ''}
            </div>
          </div>
        </div>
        {statusPill(ipo.status)}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 9, marginTop: 14 }}>
        <Field label="Price Band" value={ipo.price_band_low ? `₹${ipo.price_band_low}–${ipo.price_band_high}` : '—'} />
        <Field label="Issue Size" value={ipo.issue_size_cr ? `₹${ipo.issue_size_cr.toLocaleString('en-IN')} Cr` : '—'} />
        <Field label="Lot Size" value={ipo.lot_size ? `${ipo.lot_size} sh` : '—'} />
        <Field label="GMP" value={ipo.gmp != null ? `₹${ipo.gmp}${ipo.gmp_pct != null ? ` (${ipo.gmp_pct}%)` : ''}` : '—'}
          color={ipo.gmp ? T.green : T.sub} />
      </div>

      {/* Subscription bar (open) */}
      {ipo.status === 'OPEN' && ipo.subscription_times != null && (
        <div style={{ marginTop: 13 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: T.sub, marginBottom: 4 }}>
            <span>Subscription</span>
            <span style={{ fontFamily: T.mono, color: ipo.subscription_times >= 1 ? T.green : T.amber, fontWeight: 700 }}>
              {ipo.subscription_times.toFixed(1)}×
            </span>
          </div>
          <div style={{ height: 6, background: T.el, borderRadius: 4, overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${Math.min(100, ipo.subscription_times * 10)}%`, background: ipo.subscription_times >= 1 ? T.green : T.amber }} />
          </div>
        </div>
      )}

      {/* Listing gain (listed) */}
      {ipo.status === 'LISTED' && gain != null && (
        <div style={{ marginTop: 13, display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: T.el, borderRadius: 8, padding: '9px 12px' }}>
          <span style={{ fontSize: 11.5, color: T.sub }}>Listing Gain</span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 15, fontWeight: 700, fontFamily: T.mono, color: gain >= 0 ? T.green : T.red }}>
            {gain >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
            {gain >= 0 ? '+' : ''}{gain.toFixed(1)}%
          </span>
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 13, paddingTop: 11, borderTop: `1px solid ${T.b}`, fontSize: 11, color: T.muted }}>
        <Calendar style={{ width: 12, height: 12 }} />
        {ipo.status === 'LISTED'
          ? <span>Listed {fmtDate(ipo.listing_date)}{ipo.listing_price ? ` @ ₹${ipo.listing_price}` : ''}</span>
          : <span>Open {fmtDate(ipo.open_date)} → Close {fmtDate(ipo.close_date)} · Lists {fmtDate(ipo.listing_date)}</span>}
      </div>
    </div>
  )
}

function Field({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div>
      <div style={{ fontSize: 9.5, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</div>
      <div style={{ fontSize: 13, fontWeight: 600, fontFamily: T.mono, color: color || T.text, marginTop: 3 }}>{value}</div>
    </div>
  )
}
