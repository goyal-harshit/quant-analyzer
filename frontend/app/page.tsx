'use client'

import { useRouter } from 'next/navigation'
import { Home, TrendingUp, TrendingDown, Database, Activity, Shield, Target, Zap } from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { STOCKS, T, fI, pct, genPrices } from '@/lib/stockData'

const card = (x = {}) => ({ background: T.card, border: `1px solid ${T.b}`, borderRadius: 10, ...x })
const sc = v => v >= 70 ? T.green : v >= 45 ? T.amber : T.red

function Badge({ v }) {
  const c = sc(v)
  return <span style={{ background: `${c}22`, color: c, border: `1px solid ${c}44`, borderRadius: 4, padding: '2px 9px', fontSize: 12, fontFamily: T.mono, fontWeight: 700 }}>{v}</span>
}

function CT({ active, payload, label }: { active?: any; payload?: any; label?: any } = {}) {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: T.el, border: `1px solid ${T.b}`, borderRadius: 6, padding: '8px 12px', fontSize: 12 }}>
      <div style={{ color: T.muted, marginBottom: 4 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color || T.text, fontFamily: T.mono }}>
          {p.name && <span style={{ color: T.sub }}>{p.name}: </span>}
          {typeof p.value === 'number' ? p.value.toFixed(2) : p.value}
        </div>
      ))}
    </div>
  )
}

export default function Dashboard() {
  const router = useRouter()
  const indices = [
    { label: 'NIFTY 50', val: 24857.2, chg: 0.89 },
    { label: 'SENSEX', val: 81865.4, chg: 0.74 },
    { label: 'BANK NIFTY', val: 53241.8, chg: 1.12 },
    { label: 'INDIA VIX', val: 13.42, chg: -0.85 },
  ]
  const sorted = [...STOCKS].sort((a, b) => b.composite - a.composite)
  const byChg = [...STOCKS].sort((a, b) => b.chg - a.chg)
  const niftyPts = genPrices(24857.2, 999, 120).slice(-88)

  return (
    <div style={{ padding: '26px 30px', maxWidth: 1200, fontFamily: T.sans }}>
      <div style={{ marginBottom: 24 }}>
        <div style={{ fontSize: 22, fontWeight: 700, color: T.text }}>Market Dashboard</div>
        <div style={{ fontSize: 13, color: T.sub, marginTop: 3 }}>
          NSE · BSE · India Equities — {new Date().toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 20 }}>
        {indices.map(({ label, val, chg }) => (
          <div key={label} style={card({ padding: '13px 16px' })}>
            <div style={{ fontSize: 10, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 5 }}>{label}</div>
            <div style={{ fontSize: 20, fontWeight: 700, fontFamily: T.mono, color: T.text }}>{val.toLocaleString('en-IN')}</div>
            <div style={{ fontSize: 12, fontFamily: T.mono, color: chg >= 0 ? T.green : T.red, marginTop: 2 }}>{chg >= 0 ? '\u25B2' : '\u25BC'} {Math.abs(chg).toFixed(2)}%</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 14, marginBottom: 14 }}>
        <div style={card({ padding: '16px 18px' })}>
          <div style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 14 }}>Nifty 50 — 90 Days</div>
          <ResponsiveContainer width="100%" height={195}>
            <AreaChart data={niftyPts} margin={{ top: 4, right: 4, bottom: 0, left: 44 }}>
              <defs>
                <linearGradient id="g0" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={T.blue} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={T.blue} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="d" tick={{ fontSize: 10, fill: T.muted }} tickLine={false} axisLine={false} interval={15} />
              <YAxis tick={{ fontSize: 10, fill: T.muted, fontFamily: T.mono }} tickLine={false} axisLine={false} domain={['auto', 'auto']} tickFormatter={v => v.toLocaleString('en-IN')} />
              <Tooltip content={<CT />} />
              <Area type="monotone" dataKey="p" stroke={T.blue} strokeWidth={2} fill="url(#g0)" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div style={card({ padding: '16px 18px' })}>
          <div style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 12 }}>Top Factor Signals</div>
          {sorted.slice(0, 6).map(stk => (
            <div
              key={stk.ticker}
              onClick={() => router.push(`/stocks/${stk.ticker}`)}
              style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '7px 0', borderBottom: `1px solid ${T.b}`, cursor: 'pointer' }}
            >
              <div>
                <div style={{ fontSize: 12, fontWeight: 600, color: T.text, fontFamily: T.mono }}>{stk.ticker}</div>
                <div style={{ fontSize: 10, color: T.muted }}>{stk.sector}</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <Badge v={stk.composite} />
                <div style={{ fontSize: 10, fontFamily: T.mono, color: stk.chg >= 0 ? T.green : T.red, marginTop: 2 }}>{pct(stk.chg)}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
        {[{ title: 'Top Gainers', data: byChg.slice(0, 5) }, { title: 'Top Losers', data: [...byChg].reverse().slice(0, 5) }].map(({ title, data }) => (
          <div key={title} style={card({ padding: '15px 18px' })}>
            <div style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 10 }}>{title}</div>
            {data.map(stk => (
              <div
                key={stk.ticker}
                onClick={() => router.push(`/stocks/${stk.ticker}`)}
                style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', borderBottom: `1px solid ${T.b}`, cursor: 'pointer' }}
              >
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: T.text, fontFamily: T.mono }}>{stk.ticker}</div>
                  <div style={{ fontSize: 10, color: T.muted }}>{stk.name}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 12, fontFamily: T.mono, color: T.text }}>₹{stk.price.toLocaleString('en-IN')}</div>
                  <div style={{ fontSize: 11, fontFamily: T.mono, color: stk.chg >= 0 ? T.green : T.red }}>{pct(stk.chg)}</div>
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}
