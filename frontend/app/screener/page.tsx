'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Filter, Search } from 'lucide-react'
import { STOCKS, T, pct } from '@/lib/stockData'

const card = (x = {}) => ({ background: T.card, border: `1px solid ${T.b}`, borderRadius: 10, ...x })
const sc = v => v >= 70 ? T.green : v >= 45 ? T.amber : T.red

function Badge({ v }) {
  const c = sc(v)
  return <span style={{ background: `${c}22`, color: c, border: `1px solid ${c}44`, borderRadius: 4, padding: '2px 9px', fontSize: 12, fontFamily: T.mono, fontWeight: 700 }}>{v}</span>
}

function Tag({ children, color = '#a78bfa' }) {
  return <span style={{ background: `${color}22`, color, border: `1px solid ${color}44`, borderRadius: 4, padding: '2px 7px', fontSize: 10, fontWeight: 700 }}>{children}</span>
}

export default function Screener() {
  const router = useRouter()
  const [flt, setFlt] = useState({ sector: 'All', minRoe: 0, maxPe: 100, minMom: 0, minQual: 0, minScore: 0 })
  const [sort, setSort] = useState({ key: 'composite', dir: -1 })
  const [q, setQ] = useState('')
  const sectors = ['All', ...new Set(STOCKS.map(s => s.sector))]

  const rows = [...STOCKS]
    .filter(s =>
      (flt.sector === 'All' || s.sector === flt.sector) &&
      s.roe >= flt.minRoe &&
      s.pe <= flt.maxPe &&
      s.mom >= flt.minMom &&
      s.qual >= flt.minQual &&
      s.composite >= flt.minScore &&
      (q === '' || s.ticker.includes(q.toUpperCase()) || s.name.toLowerCase().includes(q.toLowerCase()))
    )
    .sort((a, b) => {
      const va = a[sort.key], vb = b[sort.key]
      return (typeof va === 'string' ? va.localeCompare(vb) : va - vb) * sort.dir
    })

  function Th({ label, k, left }: { label: any; k: any; left?: boolean }) {
    return (
      <th
        onClick={() => setSort(p => ({ key: k, dir: p.key === k ? -p.dir : -1 }))}
        style={{
          padding: '10px 13px', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.06em',
          color: sort.key === k ? T.blue : T.muted, cursor: 'pointer', textAlign: left ? 'left' : 'right',
          fontWeight: 600, whiteSpace: 'nowrap',
        }}
      >
        {label}{sort.key === k ? (sort.dir === -1 ? ' \u2193' : ' \u2191') : ''}
      </th>
    )
  }

  return (
    <div style={{ padding: '26px 30px', maxWidth: 1400, fontFamily: T.sans }}>
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 22, fontWeight: 700, color: T.text }}>Factor Screener</div>
        <div style={{ fontSize: 13, color: T.sub, marginTop: 3 }}>Screening {rows.length} of {STOCKS.length} stocks — Nifty 500 universe</div>
      </div>

      <div style={card({ padding: '14px 18px', marginBottom: 18 })}>
        <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <div>
            <div style={{ fontSize: 10, color: T.muted, marginBottom: 4 }}>SECTOR</div>
            <select
              value={flt.sector}
              onChange={e => setFlt(f => ({ ...f, sector: e.target.value }))}
              style={{ background: T.el, border: `1px solid ${T.b}`, borderRadius: 6, padding: '6px 10px', fontSize: 12, color: T.text, cursor: 'pointer' }}
            >
              {sectors.map(s => <option key={s}>{s}</option>)}
            </select>
          </div>

          {[
            { label: 'MIN ROE%', k: 'minRoe', max: 40 },
            { label: 'MAX PE', k: 'maxPe', max: 100 },
            { label: 'MIN MOM', k: 'minMom', max: 100 },
            { label: 'MIN QUAL', k: 'minQual', max: 100 },
            { label: 'MIN SCORE', k: 'minScore', max: 100 },
          ].map(({ label, k, max }) => (
            <div key={k} style={{ minWidth: 110 }}>
              <div style={{ fontSize: 10, color: T.muted, marginBottom: 4 }}>
                {label}: <span style={{ color: T.blue, fontFamily: T.mono }}>{flt[k]}</span>
              </div>
              <input
                type="range" min={0} max={max} value={flt[k]}
                onChange={e => setFlt(f => ({ ...f, [k]: +e.target.value }))}
                style={{ width: '100%', accentColor: T.blue }}
              />
            </div>
          ))}

          <div style={{ marginLeft: 'auto' }}>
            <input
              value={q} onChange={e => setQ(e.target.value)}
              placeholder="Search ticker..."
              style={{
                background: T.el, border: `1px solid ${T.b}`, borderRadius: 6, padding: '6px 12px',
                fontSize: 12, color: T.text, width: 170, outline: 'none',
              }}
            />
          </div>
        </div>
      </div>

      <div style={card({ overflow: 'auto' })}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: `1px solid ${T.b}` }}>
              <Th label="Ticker" k="ticker" left />
              <Th label="Sector" k="sector" left />
              <Th label="Price" k="price" />
              <Th label="Chg%" k="chg" />
              <Th label="PE" k="pe" />
              <Th label="PB" k="pb" />
              <Th label="ROE%" k="roe" />
              <Th label="Rev.G%" k="rev" />
              <Th label="Mom" k="mom" />
              <Th label="Qual" k="qual" />
              <Th label="Val" k="val" />
              <Th label="Grw" k="grw" />
              <Th label="Score" k="composite" />
            </tr>
          </thead>
          <tbody>
            {rows.map((stk, i) => (
              <tr
                key={stk.ticker}
                onClick={() => router.push(`/stocks/${stk.ticker}`)}
                style={{
                  borderBottom: `1px solid ${T.b}`, cursor: 'pointer',
                  background: i % 2 === 0 ? 'transparent' : `${T.el}66`,
                }}
                onMouseEnter={e => e.currentTarget.style.background = T.el}
                onMouseLeave={e => e.currentTarget.style.background = i % 2 === 0 ? 'transparent' : `${T.el}66`}
              >
                <td style={{ padding: '9px 13px' }}>
                  <div style={{ fontFamily: T.mono, fontWeight: 700, fontSize: 12, color: T.text }}>{stk.ticker}</div>
                  <div style={{ fontSize: 10, color: T.muted, marginTop: 1 }}>{stk.name}</div>
                </td>
                <td style={{ padding: '9px 13px' }}><Tag>{stk.sector}</Tag></td>
                <td style={{ padding: '9px 13px', textAlign: 'right', fontFamily: T.mono, fontSize: 12, color: T.text }}>
                  ₹{stk.price.toLocaleString('en-IN')}
                </td>
                <td style={{ padding: '9px 13px', textAlign: 'right', fontFamily: T.mono, fontSize: 12, color: stk.chg >= 0 ? T.green : T.red }}>
                  {pct(stk.chg)}
                </td>
                {[stk.pe, stk.pb, stk.roe, stk.rev].map((v, j) => (
                  <td key={j} style={{ padding: '9px 13px', textAlign: 'right', fontFamily: T.mono, fontSize: 12, color: T.text }}>
                    {v.toFixed(1)}
                  </td>
                ))}
                {[stk.mom, stk.qual, stk.val, stk.grw].map((v, j) => (
                  <td key={j} style={{ padding: '9px 13px', textAlign: 'right', fontFamily: T.mono, fontSize: 11, color: sc(v), fontWeight: 700 }}>
                    {v}
                  </td>
                ))}
                <td style={{ padding: '9px 13px', textAlign: 'right' }}><Badge v={stk.composite} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
