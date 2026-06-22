'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Filter, Search, RefreshCw } from 'lucide-react'
import { T, pct } from '@/lib/stockData'
import { useScreener, useSectors } from '@/lib/hooks'

const card = (x = {}) => ({ background: T.card, border: `1px solid ${T.b}`, borderRadius: 10, ...x })
const sc = v => v >= 70 ? T.green : v >= 45 ? T.amber : T.red

function Badge({ v }) {
  const c = sc(v)
  return <span style={{ background: `${c}22`, color: c, border: `1px solid ${c}44`, borderRadius: 4, padding: '2px 9px', fontSize: 12, fontFamily: T.mono, fontWeight: 700 }}>{v !== null && v !== undefined ? Math.round(v) : 'N/A'}</span>
}

function Tag({ children, color = '#a78bfa' }) {
  return <span style={{ background: `${color}22`, color, border: `1px solid ${color}44`, borderRadius: 4, padding: '2px 7px', fontSize: 10, fontWeight: 700 }}>{children}</span>
}

export default function Screener() {
  const router = useRouter()
  const [flt, setFlt] = useState({ sector: 'All', minRoe: 0, maxPe: 100, minMom: 0, minQual: 0, minScore: 0 })
  const [sort, setSort] = useState({ key: 'composite_score', dir: 'desc' })
  const [q, setQ] = useState('')
  const [refreshSeed, setRefreshSeed] = useState(0)

  // Fetch available sectors
  const { data: sectorData } = useSectors()
  const sectors = ['All', ...(sectorData?.sectors || [])]

  // Construct filters payload for the backend API
  const apiFilters = {
    sector: flt.sector === 'All' ? null : flt.sector,
    min_pe: null,
    max_pe: flt.maxPe === 100 ? null : flt.maxPe,
    min_roe: flt.minRoe === 0 ? null : flt.minRoe,
    min_momentum: flt.minMom === 0 ? null : flt.minMom,
    min_quality: flt.minQual === 0 ? null : flt.minQual,
    min_composite: flt.minScore === 0 ? null : flt.minScore,
    sort_by: sort.key,
    sort_dir: sort.dir,
    limit: 100,
    offset: 0
  }

  const { data: screenData, isLoading } = useScreener(apiFilters, refreshSeed)

  const rows = (screenData?.results || []).filter(s =>
    q === '' || s.ticker.includes(q.toUpperCase()) || s.name.toLowerCase().includes(q.toLowerCase())
  )

  const handleThClick = (k: string) => {
    setSort(p => ({
      key: k,
      dir: p.key === k ? (p.dir === 'desc' ? 'asc' : 'desc') : 'desc'
    }))
  }

  function Th({ label, k, left }: { label: any; k: any; left?: boolean }) {
    return (
      <th
        onClick={() => handleThClick(k)}
        style={{
          padding: '10px 13px', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.06em',
          color: sort.key === k ? T.blue : T.muted, cursor: 'pointer', textAlign: left ? 'left' : 'right',
          fontWeight: 600, whiteSpace: 'nowrap',
        }}
      >
        {label}{sort.key === k ? (sort.dir === 'desc' ? ' \u2193' : ' \u2191') : ''}
      </th>
    )
  }

  return (
    <div style={{ padding: '26px 30px', maxWidth: 1400, fontFamily: T.sans }}>
      <div style={{ marginBottom: 20, display: 'flex', justifyContent: 'between', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: 22, fontWeight: 700, color: T.text }}>Factor Screener</div>
          <div style={{ fontSize: 13, color: T.sub, marginTop: 3 }}>
            Screening {rows.length} of {screenData?.total || 0} stocks — Nifty 500 universe
          </div>
        </div>
        <button 
          onClick={() => setRefreshSeed(prev => prev + 1)} 
          style={{
            marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6,
            padding: '6px 12px', background: T.el, border: `1px solid ${T.b}`,
            borderRadius: 6, fontSize: 12, color: T.sub, cursor: 'pointer'
          }}
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh
        </button>
      </div>

      <div style={card({ padding: '14px 18px', marginBottom: 18 })}>
        {/* Quick preset chips */}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 14, alignItems: 'center' }}>
          <div style={{ fontSize: 10, color: T.muted, marginRight: 4 }}>QUICK FILTERS:</div>
          {[
            { label: 'High Momentum', apply: { minMom: 70, minRoe: 0, maxPe: 100, minQual: 0, minScore: 0 } },
            { label: 'Quality > 60', apply: { minQual: 60, minMom: 0, minRoe: 0, maxPe: 100, minScore: 0 } },
            { label: 'Value (Low PE)', apply: { maxPe: 20, minMom: 0, minQual: 0, minRoe: 0, minScore: 0 } },
            { label: 'High ROE', apply: { minRoe: 20, minMom: 0, minQual: 0, maxPe: 100, minScore: 0 } },
            { label: 'Top Composite', apply: { minScore: 70, minMom: 0, minQual: 0, minRoe: 0, maxPe: 100 } },
          ].map(p => {
            const isActive = Object.entries(p.apply).every(([k, v]) => flt[k as keyof typeof flt] === v) && flt.sector === 'All'
            return (
              <button
                key={p.label}
                onClick={() => setFlt(f => ({ ...f, ...p.apply, sector: 'All' }))}
                style={{
                  padding: '4px 12px', borderRadius: 100, fontSize: 11, fontWeight: 600,
                  cursor: 'pointer', fontFamily: T.sans,
                  background: isActive ? `${T.blue}22` : T.el,
                  border: `1px solid ${isActive ? `${T.blue}66` : T.b}`,
                  color: isActive ? T.blue : T.sub,
                  transition: 'all 0.15s',
                }}
              >
                {p.label}
              </button>
            )
          })}
          <button
            onClick={() => setFlt({ sector: 'All', minRoe: 0, maxPe: 100, minMom: 0, minQual: 0, minScore: 0 })}
            style={{
              padding: '4px 12px', borderRadius: 100, fontSize: 11, fontWeight: 600,
              cursor: 'pointer', fontFamily: T.sans,
              background: 'transparent', border: `1px dashed ${T.b}`, color: T.muted,
              marginLeft: 'auto',
            }}
          >
            Reset
          </button>
        </div>

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
        {isLoading ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '40px 0', gap: 10 }}>
            <RefreshCw className="w-6 h-6 text-brand animate-spin" />
            <span style={{ fontSize: 12, color: T.sub }}>Computing live factor scores...</span>
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${T.b}` }}>
                <Th label="Ticker" k="ticker" left />
                <Th label="Sector" k="sector" left />
                <Th label="Price" k="price" />
                <Th label="Chg%" k="change_pct" />
                <Th label="PE" k="pe_ratio" />
                <Th label="PB" k="pb_ratio" />
                <Th label="ROE%" k="roe" />
                <Th label="Rev.G%" k="revenue_growth" />
                <Th label="Mom" k="momentum_score" />
                <Th label="Qual" k="quality_score" />
                <Th label="Val" k="value_score" />
                <Th label="Grw" k="growth_score" />
                <Th label="Score" k="composite_score" />
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
                    ₹{stk.price ? stk.price.toLocaleString('en-IN') : 'N/A'}
                  </td>
                  <td style={{ padding: '9px 13px', textAlign: 'right', fontFamily: T.mono, fontSize: 12, color: (stk.change_pct ?? 0) >= 0 ? T.green : T.red }}>
                    {pct(stk.change_pct ?? 0)}
                  </td>
                  {[stk.pe_ratio, stk.pb_ratio, stk.roe, stk.revenue_growth].map((v, j) => (
                    <td key={j} style={{ padding: '9px 13px', textAlign: 'right', fontFamily: T.mono, fontSize: 12, color: T.text }}>
                      {v !== null && v !== undefined ? v.toFixed(1) : '-'}
                    </td>
                  ))}
                  {[stk.momentum_score, stk.quality_score, stk.value_score, stk.growth_score].map((v, j) => (
                    <td key={j} style={{ padding: '9px 13px', textAlign: 'right', fontFamily: T.mono, fontSize: 11, color: sc(v || 50), fontWeight: 700 }}>
                      {v !== null && v !== undefined ? Math.round(v) : '-'}
                    </td>
                  ))}
                  <td style={{ padding: '9px 13px', textAlign: 'right' }}><Badge v={stk.composite_score} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
