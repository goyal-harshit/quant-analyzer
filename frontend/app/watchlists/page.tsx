'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Star, TrendingUp, TrendingDown } from 'lucide-react'
import { STOCKS, T, pct, scoreColor } from '@/lib/stockData'

const card = (x = {}) => ({ background: T.card, border: `1px solid ${T.b}`, borderRadius: 10, ...x })

export default function WatchlistsPage() {
  const [selectedSector, setSelectedSector] = useState('All')
  const sectors = ['All', ...new Set(STOCKS.map(s => s.sector))]
  const [q, setQ] = useState('')

  const filtered = STOCKS.filter(s =>
    (selectedSector === 'All' || s.sector === selectedSector) &&
    (q === '' || s.ticker.includes(q.toUpperCase()) || s.name.toLowerCase().includes(q.toLowerCase()))
  )

  return (
    <div style={{ padding: '26px 30px', maxWidth: 1400, fontFamily: T.sans }}>
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 22, fontWeight: 700, color: T.text }}>Watchlist</div>
        <div style={{ fontSize: 13, color: T.sub, marginTop: 3 }}>
          Browse all tracked NSE stocks · {filtered.length} stocks
        </div>
      </div>

      <div style={card({ padding: '14px 18px', marginBottom: 18 })}>
        <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div>
            <div style={{ fontSize: 10, color: T.muted, marginBottom: 4 }}>SECTOR</div>
            <select
              value={selectedSector}
              onChange={e => setSelectedSector(e.target.value)}
              style={{
                background: T.el, border: `1px solid ${T.b}`, borderRadius: 6,
                padding: '6px 10px', fontSize: 12, color: T.text, cursor: 'pointer',
              }}
            >
              {sectors.map(s => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div style={{ marginLeft: 'auto' }}>
            <input
              value={q}
              onChange={e => setQ(e.target.value)}
              placeholder="Search ticker..."
              style={{
                background: T.el, border: `1px solid ${T.b}`, borderRadius: 6,
                padding: '6px 12px', fontSize: 12, color: T.text, width: 170, outline: 'none',
              }}
            />
          </div>
        </div>
      </div>

      <div style={card({ overflow: 'auto' })}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: `1px solid ${T.b}` }}>
              {['Ticker', 'Name', 'Sector', 'Price', 'Chg%', 'Score'].map(h => (
                <th key={h} style={{
                  padding: '10px 13px', fontSize: 10, textTransform: 'uppercase',
                  letterSpacing: '0.06em', color: T.muted, fontWeight: 600,
                  textAlign: h === 'Ticker' || h === 'Name' || h === 'Sector' ? 'left' : 'right',
                  whiteSpace: 'nowrap',
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((stk, i) => (
              <tr
                key={stk.ticker}
                style={{
                  borderBottom: `1px solid ${T.b}`,
                  cursor: 'pointer',
                  background: i % 2 === 0 ? 'transparent' : `${T.el}66`,
                }}
                onMouseEnter={e => { e.currentTarget.style.background = T.el }}
                onMouseLeave={e => { e.currentTarget.style.background = i % 2 === 0 ? 'transparent' : `${T.el}66` }}
              >
                <td style={{ padding: '9px 13px' }}>
                  <Link href={`/stocks/${stk.ticker}`} style={{
                    fontFamily: T.mono, fontWeight: 700, fontSize: 12,
                    color: T.blue, textDecoration: 'none',
                  }}>
                    {stk.ticker}
                  </Link>
                  <div style={{ fontSize: 10, color: T.muted, marginTop: 1 }}>{stk.name}</div>
                </td>
                <td style={{ padding: '9px 13px', fontSize: 12, color: T.text }}>{stk.name}</td>
                <td style={{ padding: '9px 13px' }}>
                  <span style={{
                    background: `${T.purple}22`, color: T.purple,
                    border: `1px solid ${T.purple}44`, borderRadius: 4,
                    padding: '2px 7px', fontSize: 10, fontWeight: 700,
                  }}>{stk.sector}</span>
                </td>
                <td style={{ padding: '9px 13px', textAlign: 'right', fontFamily: T.mono, fontSize: 12, color: T.text }}>
                  ₹{stk.price.toLocaleString('en-IN')}
                </td>
                <td style={{
                  padding: '9px 13px', textAlign: 'right', fontFamily: T.mono,
                  fontSize: 12, color: stk.chg >= 0 ? T.green : T.red,
                }}>
                  {pct(stk.chg)}
                </td>
                <td style={{ padding: '9px 13px', textAlign: 'right' }}>
                  <span style={{
                    background: `${scoreColor(stk.composite)}22`,
                    color: scoreColor(stk.composite),
                    border: `1px solid ${scoreColor(stk.composite)}44`,
                    borderRadius: 4, padding: '2px 9px', fontSize: 12,
                    fontFamily: T.mono, fontWeight: 700,
                  }}>{stk.composite}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
