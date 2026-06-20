'use client'

import { useState } from 'react'
import { Search, TrendingUp, Activity, RefreshCw, Calculator, PiggyBank } from 'lucide-react'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { T, fI } from '@/lib/stockData'
import { useMFSearch, useMFPopular, useMFScheme, useMFReturns, useMFRisk } from '@/lib/hooks'
import { mfApi } from '@/lib/api'

const card = (x: any = {}) => ({ background: T.card, border: `1px solid ${T.b}`, borderRadius: 10, ...x })

function CT({ active, payload, label }: any = {}) {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: T.el, border: `1px solid ${T.b}`, borderRadius: 6, padding: '8px 12px', fontSize: 12 }}>
      <div style={{ color: T.muted, marginBottom: 4 }}>{label}</div>
      <div style={{ color: T.blue, fontFamily: T.mono }}>NAV: ₹{Number(payload[0].value).toFixed(2)}</div>
    </div>
  )
}

const PERIODS = ['1m', '3m', '6m', '1y', '3y', '5y']

function pctColor(v: number | null | undefined) {
  if (v == null) return T.sub
  return v >= 0 ? T.green : T.red
}
function fmtPct(v: number | null | undefined) {
  if (v == null) return '—'
  return `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`
}

export default function MutualFundsPage() {
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState<number | null>(null)
  const [period, setPeriod] = useState('3y')

  const { data: search, isFetching: searching } = useMFSearch(query)
  const { data: popular } = useMFPopular()
  const { data: scheme, isLoading: loadingScheme } = useMFScheme(selected, period)
  const { data: returns } = useMFReturns(selected)
  const { data: risk } = useMFRisk(selected)

  const results = (query.trim().length > 1 ? search?.results : popular?.results) || []

  return (
    <div style={{ padding: '26px 30px', maxWidth: 1280, fontFamily: T.sans }}>
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 22, fontWeight: 700, color: T.text }}>Mutual Funds</div>
        <div style={{ fontSize: 13, color: T.sub, marginTop: 3 }}>
          14,000+ Indian schemes · live NAV via mfapi.in · returns, risk & SIP analytics
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '340px 1fr', gap: 16, alignItems: 'start' }}>
        {/* ── Search / list column ── */}
        <div style={card({ padding: 14 })}>
          <div style={{ position: 'relative', marginBottom: 12 }}>
            <Search style={{ position: 'absolute', left: 10, top: 9, width: 15, height: 15, color: T.muted }} />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search fund or AMC…"
              style={{
                width: '100%', padding: '8px 10px 8px 32px', background: T.el,
                border: `1px solid ${T.b}`, borderRadius: 8, color: T.text, fontSize: 13, outline: 'none',
              }}
            />
          </div>
          <div style={{ fontSize: 10, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>
            {query.trim().length > 1 ? (searching ? 'Searching…' : `${results.length} results`) : 'Popular schemes'}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 560, overflowY: 'auto' }}>
            {results.map((s: any) => (
              <button
                key={s.scheme_code}
                onClick={() => setSelected(s.scheme_code)}
                style={{
                  textAlign: 'left', padding: '9px 11px', borderRadius: 8, cursor: 'pointer',
                  background: selected === s.scheme_code ? T.el : 'transparent',
                  border: `1px solid ${selected === s.scheme_code ? T.bhi : 'transparent'}`,
                }}
              >
                <div style={{ fontSize: 12.5, color: T.text, fontWeight: 500, lineHeight: 1.3 }}>{s.scheme_name}</div>
                {s.category && <div style={{ fontSize: 10.5, color: T.muted, marginTop: 2 }}>{s.category}</div>}
              </button>
            ))}
            {results.length === 0 && query.trim().length > 1 && !searching && (
              <div style={{ fontSize: 12, color: T.muted, padding: 12 }}>No schemes found.</div>
            )}
          </div>
        </div>

        {/* ── Detail column ── */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {!selected ? (
            <div style={card({ padding: 40, textAlign: 'center', color: T.sub })}>
              <PiggyBank style={{ width: 34, height: 34, color: T.muted, margin: '0 auto 12px' }} />
              <div style={{ fontSize: 14 }}>Select a scheme to view NAV history, returns & risk.</div>
            </div>
          ) : loadingScheme ? (
            <div style={card({ padding: 40, textAlign: 'center' })}>
              <RefreshCw className="w-7 h-7 text-brand animate-spin" style={{ margin: '0 auto' }} />
              <div style={{ fontSize: 13, color: T.sub, marginTop: 10 }}>Loading scheme…</div>
            </div>
          ) : scheme ? (
            <>
              {/* Header + NAV */}
              <div style={card({ padding: '16px 18px' })}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 10 }}>
                  <div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: T.text }}>{scheme.meta?.scheme_name}</div>
                    <div style={{ fontSize: 12, color: T.sub, marginTop: 3 }}>
                      {scheme.meta?.fund_house} · {scheme.meta?.scheme_category || scheme.meta?.scheme_type}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 22, fontWeight: 700, fontFamily: T.mono, color: T.text }}>
                      ₹{scheme.latest_nav?.toFixed(2) ?? '—'}
                    </div>
                    <div style={{ fontSize: 11, color: T.muted }}>NAV · {scheme.latest_date}</div>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: 6, margin: '14px 0 10px' }}>
                  {PERIODS.map((p) => (
                    <button key={p} onClick={() => setPeriod(p)}
                      style={{
                        padding: '4px 11px', fontSize: 11, borderRadius: 6, cursor: 'pointer', textTransform: 'uppercase',
                        fontFamily: T.mono, letterSpacing: '0.04em',
                        background: period === p ? T.blue : T.el,
                        color: period === p ? '#fff' : T.sub,
                        border: `1px solid ${period === p ? T.blue : T.b}`,
                      }}>{p}</button>
                  ))}
                </div>

                <ResponsiveContainer width="100%" height={230}>
                  <AreaChart data={scheme.nav_history || []} margin={{ top: 6, right: 8, bottom: 0, left: 8 }}>
                    <defs>
                      <linearGradient id="navg" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={T.blue} stopOpacity={0.35} />
                        <stop offset="95%" stopColor={T.blue} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke={T.b} strokeDasharray="3 3" />
                    <XAxis dataKey="date" tick={{ fontSize: 9, fill: T.muted }} tickLine={false} axisLine={false} minTickGap={50} />
                    <YAxis tick={{ fontSize: 10, fill: T.muted, fontFamily: T.mono }} tickLine={false} axisLine={false} domain={['auto', 'auto']} tickFormatter={(v) => '₹' + Math.round(v)} width={48} />
                    <Tooltip content={<CT />} />
                    <Area type="monotone" dataKey="nav" stroke={T.blue} strokeWidth={2} fill="url(#navg)" dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
                {scheme._synthetic && (
                  <div style={{ fontSize: 10.5, color: T.amber, marginTop: 6 }}>
                    ⚠ Showing offline sample data (mfapi.in unreachable from server).
                  </div>
                )}
              </div>

              {/* Returns */}
              <div style={card({ padding: '14px 18px' })}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 12 }}>
                  <TrendingUp style={{ width: 15, height: 15, color: T.green }} />
                  <span style={{ fontSize: 13, fontWeight: 600, color: T.text }}>Trailing Returns</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7,1fr)', gap: 8 }}>
                  {[
                    ['1M', returns?.ret_1m], ['3M', returns?.ret_3m], ['6M', returns?.ret_6m],
                    ['1Y', returns?.ret_1y], ['3Y CAGR', returns?.cagr_3y], ['5Y CAGR', returns?.cagr_5y],
                    ['Incep.', returns?.cagr_since_inception],
                  ].map(([l, v]: any) => (
                    <div key={l} style={{ textAlign: 'center', background: T.el, borderRadius: 7, padding: '9px 4px' }}>
                      <div style={{ fontSize: 9.5, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.04em' }}>{l}</div>
                      <div style={{ fontSize: 13.5, fontWeight: 700, fontFamily: T.mono, color: pctColor(v), marginTop: 4 }}>{fmtPct(v)}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Risk */}
              <div style={card({ padding: '14px 18px' })}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 12 }}>
                  <Activity style={{ width: 15, height: 15, color: T.amber }} />
                  <span style={{ fontSize: 13, fontWeight: 600, color: T.text }}>Risk Metrics (3Y)</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5,1fr)', gap: 8 }}>
                  {[
                    ['Volatility', risk?.volatility_pct != null ? risk.volatility_pct.toFixed(1) + '%' : '—', T.text],
                    ['Sharpe', risk?.sharpe_ratio ?? '—', T.text],
                    ['Sortino', risk?.sortino_ratio ?? '—', T.text],
                    ['Max DD', risk?.max_drawdown_pct != null ? risk.max_drawdown_pct.toFixed(1) + '%' : '—', T.red],
                    ['Risk Grade', risk?.risk_grade ?? '—', T.amber],
                  ].map(([l, v, c]: any) => (
                    <div key={l} style={{ textAlign: 'center', background: T.el, borderRadius: 7, padding: '9px 4px' }}>
                      <div style={{ fontSize: 9.5, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.04em' }}>{l}</div>
                      <div style={{ fontSize: 14, fontWeight: 700, fontFamily: T.mono, color: c, marginTop: 4 }}>{v}</div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : null}

          <SIPCalculator />
        </div>
      </div>
    </div>
  )
}

function SIPCalculator() {
  const [monthly, setMonthly] = useState(10000)
  const [years, setYears] = useState(10)
  const [ret, setRet] = useState(12)
  const [result, setResult] = useState<any>(null)
  const [busy, setBusy] = useState(false)

  async function run() {
    setBusy(true)
    try {
      const r = await mfApi.sipCalculator({ monthly_amount: monthly, years, expected_return: ret })
      setResult(r)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={card({ padding: '16px 18px' })}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 14 }}>
        <Calculator style={{ width: 15, height: 15, color: T.purple }} />
        <span style={{ fontSize: 13, fontWeight: 600, color: T.text }}>SIP Calculator</span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr) auto', gap: 12, alignItems: 'end' }}>
        {[
          ['Monthly (₹)', monthly, setMonthly, 500],
          ['Years', years, setYears, 1],
          ['Expected return %', ret, setRet, 0.5],
        ].map(([label, val, setter, step]: any) => (
          <label key={label} style={{ fontSize: 11, color: T.sub }}>
            {label}
            <input type="number" value={val} step={step} min={0}
              onChange={(e) => setter(parseFloat(e.target.value) || 0)}
              style={{ width: '100%', marginTop: 5, padding: '7px 9px', background: T.el, border: `1px solid ${T.b}`, borderRadius: 7, color: T.text, fontSize: 13, fontFamily: T.mono, outline: 'none' }} />
          </label>
        ))}
        <button onClick={run} disabled={busy}
          style={{ padding: '8px 16px', background: T.purple, color: '#fff', border: 'none', borderRadius: 7, fontSize: 12.5, fontWeight: 600, cursor: 'pointer', height: 35 }}>
          {busy ? '…' : 'Calculate'}
        </button>
      </div>
      {result && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 10, marginTop: 16 }}>
          {[
            ['Invested', fI(result.total_invested), T.sub],
            ['Future Value', fI(result.future_value), T.green],
            ['Est. Gain', fI(result.estimated_gain), T.blue],
            ['Wealth ×', `${result.wealth_multiple}×`, T.amber],
          ].map(([l, v, c]: any) => (
            <div key={l} style={{ background: T.el, borderRadius: 8, padding: '11px 13px' }}>
              <div style={{ fontSize: 10, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{l}</div>
              <div style={{ fontSize: 17, fontWeight: 700, fontFamily: T.mono, color: c, marginTop: 4 }}>{v}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
