'use client'

import { useState } from 'react'
import { RefreshCw, TrendingUp, Shield, Activity, Zap } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { BT_STATS, BT_CHART, BT_COLORS, T } from '@/lib/stockData'

const card = (x = {}) => ({ background: T.card, border: `1px solid ${T.b}`, borderRadius: 10, ...x })
const sc = v => v >= 70 ? T.green : v >= 45 ? T.amber : T.red

function CT({ active, payload, label }: { active?: any; payload?: any; label?: any } = {}) {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: T.el, border: `1px solid ${T.b}`, borderRadius: 6, padding: '8px 12px', fontSize: 12 }}>
      <div style={{ color: T.muted, marginBottom: 4 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color || T.text, fontFamily: T.mono }}>
          {typeof p.value === 'number' ? p.value.toFixed(2) : p.value}
        </div>
      ))}
    </div>
  )
}

export default function Backtester() {
  const [sel, setSel] = useState('Composite Score')
  const strategies = Object.keys(BT_STATS).filter(s => s !== 'Nifty 50')
  const stat = BT_STATS[sel]

  return (
    <div style={{ padding: '26px 30px', maxWidth: 1100, fontFamily: T.sans }}>
      <div style={{ marginBottom: 22 }}>
        <div style={{ fontSize: 22, fontWeight: 700, color: T.text }}>Strategy Backtester</div>
        <div style={{ fontSize: 13, color: T.sub, marginTop: 3 }}>Factor-based strategies · Nifty 500 universe · Jun 2022 – Jun 2025</div>
      </div>

      <div style={{ display: 'flex', gap: 10, marginBottom: 22 }}>
        {strategies.map(s => {
          const c = BT_COLORS[s]
          return (
            <button
              key={s}
              onClick={() => setSel(s)}
              style={{
                padding: '8px 18px', borderRadius: 8, border: `1px solid ${sel === s ? c : T.b}`,
                background: sel === s ? `${c}22` : 'transparent', color: sel === s ? c : T.sub,
                fontSize: 13, fontWeight: sel === s ? 600 : 400, cursor: 'pointer',
              }}
            >
              {s}
            </button>
          )
        })}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 18 }}>
        {[
          ['3Y Return', `+${stat.ret.toFixed(1)}%`, T.green, 'vs +56.2% Nifty 50'],
          ['CAGR', `${stat.cagr.toFixed(1)}%`, T.blue, 'vs 16.2% Nifty 50'],
          ['Sharpe', stat.sharpe.toFixed(2), T.amber, 'vs 0.94 Nifty 50'],
          ['Max DD', `${stat.maxDD.toFixed(1)}%`, T.red, 'vs -22.1% Nifty 50'],
        ].map(([l, v, c, sub]) => (
          <div key={l} style={card({ padding: '13px 16px' })}>
            <div style={{ fontSize: 10, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 5 }}>{l}</div>
            <div style={{ fontSize: 21, fontWeight: 700, fontFamily: T.mono, color: c }}>{v}</div>
            <div style={{ fontSize: 10, color: T.muted, marginTop: 3 }}>{sub}</div>
          </div>
        ))}
      </div>

      <div style={card({ padding: '16px 18px', marginBottom: 14 })}>
        <div style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 14 }}>Portfolio Growth (Base 100) · All Strategies vs Nifty 50</div>
        <ResponsiveContainer width="100%" height={270}>
          <LineChart data={BT_CHART} margin={{ top: 4, right: 16, bottom: 0, left: 40 }}>
            <CartesianGrid stroke={T.b} strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 9, fill: T.muted }} tickLine={false} axisLine={false} interval={5} />
            <YAxis tick={{ fontSize: 10, fill: T.muted, fontFamily: T.mono }} tickLine={false} axisLine={false} domain={[80, 'auto']} tickFormatter={v => v.toFixed(0)} />
            <Tooltip content={<CT />} />
            <Legend wrapperStyle={{ fontSize: 11, color: T.sub }} />
            {Object.entries(BT_COLORS).map(([k, c]) => (
              <Line
                key={k}
                type="monotone"
                dataKey={k}
                stroke={c}
                strokeWidth={k === sel ? 2.5 : k === 'Nifty 50' ? 1.5 : 1}
                dot={false}
                opacity={k === sel || k === 'Nifty 50' ? 1 : 0.35}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div style={card({ padding: '15px 18px' })}>
        <div style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 12 }}>Strategy Descriptions</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 12 }}>
          {[
            ['High Momentum', 'Top-decile 12-1 month price momentum. Equal-weight. Quarterly rebalance. Nifty 500 universe.', T.amber],
            ['Quality Value', 'Intersection of top-quartile Quality (ROE, margins, low debt) and Value (EV/EBITDA, PB). Semi-annual rebalance.', '#a78bfa'],
            ['Composite Score', 'Multi-factor: 25% Momentum + 25% Quality + 20% Value + 20% Growth + 10% Low Volatility. Monthly rebalance.', T.blue],
          ].map(([n, d, c]) => (
            <div key={n} style={{ background: T.el, borderRadius: 8, padding: '12px 14px', border: `1px solid ${T.b}` }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: c, marginBottom: 5 }}>{n}</div>
              <div style={{ fontSize: 11, color: T.sub, lineHeight: 1.6 }}>{d}</div>
            </div>
          ))}
        </div>
        <div style={{ marginTop: 10, fontSize: 10, color: T.muted }}>⚠️ Backtest results are illustrative. Past performance ≠ future returns. Transaction costs/slippage not fully modeled.</div>
      </div>
    </div>
  )
}
