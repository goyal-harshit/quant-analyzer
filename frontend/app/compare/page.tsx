'use client'

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import {
  ResponsiveContainer, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  Legend, Tooltip, LineChart, Line,
} from 'recharts'
import { Plus, X, GitCompareArrows, Trophy, Sparkles } from 'lucide-react'
import PageShell from '@/components/layout/PageShell'
import Card from '@/components/ui/Card'
import { compareApi, type CompareResponse, type CompareAsset } from '@/lib/api'

const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#06b6d4']
const SUGGESTIONS = ['RELIANCE', 'INFY', 'TCS', 'HDFCBANK', 'ICICIBANK', 'HCLTECH', 'ITC', 'SBIN', 'TATAMOTORS', 'BHARTIARTL']

const fmt = (v: number | null | undefined, dp = 2, suffix = '') =>
  v === null || v === undefined ? '—' : `${v.toFixed(dp)}${suffix}`
const fmtCr = (v: number | null | undefined) =>
  v === null || v === undefined ? '—' : v >= 1e7 ? `₹${(v / 1e7).toFixed(0)} Cr` : `₹${(v / 1e5).toFixed(0)} L`

// Metric rows for the comparison matrix. `hb` = higher-is-better (for highlighting).
const METRICS: { key: string; label: string; hb: boolean; get: (a: CompareAsset) => number | null; render: (a: CompareAsset) => string }[] = [
  { key: 'price', label: 'Price', hb: true, get: (a) => a.price, render: (a) => `₹${a.price.toFixed(2)}` },
  { key: 'change_pct', label: 'Day Change', hb: true, get: (a) => a.change_pct, render: (a) => fmt(a.change_pct, 2, '%') },
  { key: 'returns_period', label: '1Y Return', hb: true, get: (a) => a.returns_period, render: (a) => fmt(a.returns_period, 1, '%') },
  { key: 'pe_ratio', label: 'P/E', hb: false, get: (a) => a.pe_ratio, render: (a) => fmt(a.pe_ratio, 1) },
  { key: 'pb_ratio', label: 'P/B', hb: false, get: (a) => a.pb_ratio, render: (a) => fmt(a.pb_ratio, 1) },
  { key: 'roe', label: 'ROE', hb: true, get: (a) => a.roe, render: (a) => fmt(a.roe, 1, '%') },
  { key: 'dividend_yield', label: 'Div Yield', hb: true, get: (a) => a.dividend_yield, render: (a) => fmt(a.dividend_yield, 2, '%') },
  { key: 'debt_equity', label: 'Debt/Equity', hb: false, get: (a) => a.debt_equity, render: (a) => fmt(a.debt_equity, 2) },
  { key: 'volatility', label: 'Volatility', hb: false, get: (a) => a.volatility, render: (a) => fmt(a.volatility, 1, '%') },
  { key: 'sharpe_ratio', label: 'Sharpe', hb: true, get: (a) => a.sharpe_ratio, render: (a) => fmt(a.sharpe_ratio, 2) },
  { key: 'max_drawdown', label: 'Max Drawdown', hb: true, get: (a) => a.max_drawdown, render: (a) => fmt(a.max_drawdown, 1, '%') },
  { key: 'market_cap', label: 'Market Cap', hb: true, get: (a) => a.market_cap, render: (a) => fmtCr(a.market_cap) },
  { key: 'composite', label: 'Composite Score', hb: true, get: (a) => a.scores.composite, render: (a) => fmt(a.scores.composite, 0) },
]

export default function ComparePage() {
  const [tickers, setTickers] = useState<string[]>(['INFY', 'TCS'])
  const [input, setInput] = useState('')
  const [result, setResult] = useState<CompareResponse | null>(null)

  const mut = useMutation({
    mutationFn: () => compareApi.compareStocks(tickers),
    onSuccess: (data) => setResult(data),
  })

  const addTicker = (t: string) => {
    const v = t.trim().toUpperCase()
    if (v && !tickers.includes(v) && tickers.length < 5) setTickers([...tickers, v])
    setInput('')
  }
  const removeTicker = (t: string) => setTickers(tickers.filter((x) => x !== t))

  const colorFor = (ticker: string) => COLORS[(result?.assets.findIndex((a) => a.ticker === ticker) ?? 0) % COLORS.length]

  // Best/worst index per metric row (for cell highlighting).
  const extremes = (m: typeof METRICS[number]) => {
    if (!result) return { best: -1, worst: -1 }
    const vals = result.assets.map((a) => m.get(a))
    const valid = vals.map((v, i) => ({ v, i })).filter((x) => x.v !== null) as { v: number; i: number }[]
    if (valid.length < 2) return { best: -1, worst: -1 }
    const sorted = [...valid].sort((a, b) => (m.hb ? b.v - a.v : a.v - b.v))
    return { best: sorted[0].i, worst: sorted[sorted.length - 1].i }
  }

  return (
    <PageShell title="Compare Assets" subtitle="Side-by-side fundamentals, returns, risk & factor scores — up to 5 stocks">
      {/* Selector */}
      <Card padding="md">
        <div className="flex flex-wrap items-center gap-2 mb-3">
          {tickers.map((t) => (
            <span key={t} className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-brand/10 border border-brand/20 rounded-lg text-sm font-mono font-semibold text-brand">
              {t}
              <button onClick={() => removeTicker(t)} className="hover:text-danger"><X className="w-3.5 h-3.5" /></button>
            </span>
          ))}
          {tickers.length < 5 && (
            <input
              value={input}
              onChange={(e) => setInput(e.target.value.toUpperCase())}
              onKeyDown={(e) => { if (e.key === 'Enter') addTicker(input) }}
              placeholder="Add ticker…"
              className="bg-elevated border border-border rounded-lg px-3 py-1.5 text-sm font-mono text-textPrimary focus:border-brand outline-none w-32"
            />
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2 mb-4">
          <span className="text-[11px] text-textMuted">Quick add:</span>
          {SUGGESTIONS.filter((s) => !tickers.includes(s)).slice(0, 7).map((s) => (
            <button key={s} onClick={() => addTicker(s)} disabled={tickers.length >= 5}
              className="px-2 py-0.5 text-[11px] font-mono text-textSub hover:text-brand border border-border rounded disabled:opacity-30">
              + {s}
            </button>
          ))}
        </div>
        <button
          onClick={() => mut.mutate()}
          disabled={tickers.length < 2 || mut.isPending}
          className="flex items-center gap-2 px-5 py-2 bg-brand text-white rounded-lg text-sm font-bold hover:bg-brand/90 disabled:opacity-40 transition-all"
        >
          <GitCompareArrows className="w-4 h-4" />
          {mut.isPending ? 'Comparing…' : `Compare ${tickers.length} stocks`}
        </button>
        {mut.isError && <div className="mt-3 text-xs text-danger">{(mut.error as any)?.response?.data?.detail || 'Comparison failed'}</div>}
      </Card>

      {result && (
        <>
          {/* Recommendation banner */}
          <Card padding="md" className="border-brand/30 bg-brand/5">
            <div className="flex items-start gap-3">
              <Sparkles className="w-5 h-5 text-brand flex-shrink-0 mt-0.5" />
              <div>
                <div className="text-xs font-semibold text-brand uppercase tracking-wide mb-1">QuantAI Verdict</div>
                <p className="text-sm text-textPrimary">{result.recommendation}</p>
              </div>
            </div>
          </Card>

          {/* Best-in-class */}
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
            <BestCard title="Best Value" pick={result.best_value} colorFor={colorFor} />
            <BestCard title="Best Quality" pick={result.best_quality} colorFor={colorFor} />
            <BestCard title="Best Momentum" pick={result.best_momentum} colorFor={colorFor} />
            <BestCard title="Best Risk-Adj." pick={result.best_risk_adjusted} colorFor={colorFor} />
            <BestCard title="Top Return" pick={result.best_return} colorFor={colorFor} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Radar */}
            <Card padding="md">
              <Card.Header title="Factor Radar" subtitle="0-100 scores across six dimensions" />
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={result.radar}>
                    <PolarGrid stroke="#ffffff15" />
                    <PolarAngleAxis dataKey="metric" tick={{ fill: '#cbd5e1', fontSize: 11 }} />
                    <PolarRadiusAxis domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 9 }} />
                    {result.assets.map((a, i) => (
                      <Radar key={a.ticker} name={a.ticker} dataKey={a.ticker}
                        stroke={COLORS[i % COLORS.length]} fill={COLORS[i % COLORS.length]} fillOpacity={0.12} strokeWidth={2} />
                    ))}
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            {/* Price sparklines */}
            <Card padding="md">
              <Card.Header title="1-Year Price Path" subtitle="Normalised trend per asset" />
              <div className="space-y-3">
                {result.assets.map((a, i) => (
                  <div key={a.ticker} className="flex items-center gap-3">
                    <div className="w-20 flex-shrink-0">
                      <div className="font-mono font-bold text-sm" style={{ color: COLORS[i % COLORS.length] }}>{a.ticker}</div>
                      <div className={`text-[11px] font-mono ${(a.returns_period ?? 0) >= 0 ? 'text-success' : 'text-danger'}`}>
                        {fmt(a.returns_period, 1, '%')}
                      </div>
                    </div>
                    <div className="flex-1 h-12">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={a.spark.map((v, idx) => ({ idx, v }))}>
                          <Line type="monotone" dataKey="v" stroke={COLORS[i % COLORS.length]} strokeWidth={1.5} dot={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          {/* Metrics matrix */}
          <Card padding="md">
            <Card.Header title="Metrics Matrix" subtitle="Green = best, red = worst per row" icon={Trophy} />
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-sm">
                <thead>
                  <tr className="border-b border-border/50 text-textMuted text-xs font-semibold uppercase">
                    <th className="py-2.5 pr-4">Metric</th>
                    {result.assets.map((a, i) => (
                      <th key={a.ticker} className="py-2.5 text-right">
                        <span style={{ color: COLORS[i % COLORS.length] }} className="font-mono">{a.ticker}</span>
                        {a.source === 'seed' && <span className="ml-1 text-[9px] text-amber-500" title="Cached/seed fundamentals">⚠</span>}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/30">
                  {METRICS.map((m) => {
                    const { best, worst } = extremes(m)
                    return (
                      <tr key={m.key} className="hover:bg-elevated/30">
                        <td className="py-2.5 pr-4 text-textSub font-medium">{m.label}</td>
                        {result.assets.map((a, i) => (
                          <td key={a.ticker}
                            className={`py-2.5 text-right font-mono ${i === best ? 'text-success font-bold' : i === worst ? 'text-danger' : 'text-textPrimary'}`}>
                            {m.render(a)}
                          </td>
                        ))}
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </PageShell>
  )
}

function BestCard({ title, pick, colorFor }: { title: string; pick: { ticker: string | null; reason: string }; colorFor: (t: string) => string }) {
  return (
    <Card padding="sm">
      <div className="metric-label">{title}</div>
      <div className="text-lg font-mono font-bold mt-1" style={{ color: pick.ticker ? colorFor(pick.ticker) : '#64748b' }}>
        {pick.ticker || '—'}
      </div>
      <div className="text-[11px] text-textMuted mt-1 leading-snug line-clamp-2">{pick.reason}</div>
    </Card>
  )
}
