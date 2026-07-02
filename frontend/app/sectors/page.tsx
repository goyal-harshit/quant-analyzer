'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { RefreshCw, TrendingUp, TrendingDown, Layers, Activity } from 'lucide-react'
import PageShell from '@/components/layout/PageShell'
import Card from '@/components/ui/Card'
import { sectorsApi, type SectorPerf } from '@/lib/api'
import { scoreColor } from '@/lib/stockData'

// Map a daily % move to a heatmap background (red → neutral → green).
function heatColor(pct: number): string {
  const c = Math.max(-3, Math.min(3, pct))
  if (c >= 0) return `rgba(16,185,129,${0.1 + (c / 3) * 0.55})`
  return `rgba(239,68,68,${0.1 + (-c / 3) * 0.55})`
}

const pctStr = (n: number | null | undefined) => `${(n ?? 0) >= 0 ? '+' : ''}${(n ?? 0).toFixed(2)}%`

export default function SectorsPage() {
  const router = useRouter()
  const [refreshSeed, setRefreshSeed] = useState(0)
  const [selected, setSelected] = useState<string | null>(null)

  const { data, isLoading, isFetching, isError, refetch } = useQuery({
    queryKey: ['sectors', 'performance', refreshSeed],
    queryFn: () => sectorsApi.getPerformance(refreshSeed > 0),
    staleTime: 60000,
  })

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
        <RefreshCw className="w-8 h-8 text-brand animate-spin" />
        <span className="text-textSub text-sm">Aggregating sector telemetry…</span>
      </div>
    )
  }

  const sectors = data?.sectors ?? []
  const sentiment = data?.sentiment ?? { bullish: 0, neutral: 0, bearish: 0 }
  const selectedSector = sectors.find((s) => s.name === selected)

  return (
    <PageShell
      title="Sector Heatmap"
      subtitle="Live sector performance, breadth & factor strength across the NSE universe"
      actions={
        <button
          onClick={() => setRefreshSeed((p) => p + 1)}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-elevated hover:bg-border border border-border rounded-lg text-xs font-semibold text-textSub hover:text-textPrimary transition-all"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin' : ''}`} /> Refresh
        </button>
      }
    >
      {/* Sentiment + movers */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card padding="md">
          <Card.Header title="Market Breadth" icon={Activity} />
          <div className="flex items-end gap-2 h-12">
            <Bar label="Bullish" value={sentiment.bullish} total={sectors.length} color="#10b981" />
            <Bar label="Neutral" value={sentiment.neutral} total={sectors.length} color="#64748b" />
            <Bar label="Bearish" value={sentiment.bearish} total={sectors.length} color="#ef4444" />
          </div>
          <div className="flex justify-between mt-2 text-[11px] text-textMuted">
            <span className="text-success">{sentiment.bullish} up</span>
            <span>{sentiment.neutral} flat</span>
            <span className="text-danger">{sentiment.bearish} down</span>
          </div>
        </Card>

        <Card padding="md">
          <Card.Header title="Top Gainers" icon={TrendingUp} />
          <MoverList items={data?.top_gainers ?? []} positive onClick={(t) => router.push(`/stocks/${t}`)} />
        </Card>

        <Card padding="md">
          <Card.Header title="Top Losers" icon={TrendingDown} />
          <MoverList items={data?.top_losers ?? []} onClick={(t) => router.push(`/stocks/${t}`)} />
        </Card>
      </div>

      {/* Heatmap grid */}
      <Card padding="md">
        <Card.Header title="Sector Heatmap" subtitle="Click a tile for constituents · color = today's move" icon={Layers} />
        {sectors.length === 0 && (
          <div className="flex flex-col items-center gap-3 py-10 text-center">
            <span className="text-sm text-textSub">
              {isError
                ? 'Sector data is unavailable right now — the market feed could not be reached.'
                : 'No sector data available yet.'}
            </span>
            <button
              onClick={() => refetch()}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-elevated hover:bg-border border border-border rounded-lg text-xs font-semibold text-textSub hover:text-textPrimary transition-all"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Retry
            </button>
          </div>
        )}
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3">
          {sectors.map((s) => {
            const up = s.change_pct >= 0
            return (
              <button
                key={s.name}
                onClick={() => setSelected(selected === s.name ? null : s.name)}
                style={{ backgroundColor: heatColor(s.change_pct) }}
                className={`text-left rounded-xl border p-3 transition-all hover:scale-[1.02] ${
                  selected === s.name ? 'border-brand' : 'border-border/40'
                }`}
              >
                <div className="flex items-start justify-between">
                  <span className="text-sm font-semibold text-textPrimary leading-tight">{s.name}</span>
                  <span className={`font-mono text-xs font-bold ${up ? 'text-success' : 'text-danger'}`}>{pctStr(s.change_pct)}</span>
                </div>
                <div className="mt-2 flex items-center justify-between text-[11px] text-textMuted">
                  <span>{s.advancers}▲ {s.decliners}▼ · {s.stock_count}</span>
                  {s.momentum_score != null && (
                    <span className="font-mono" style={{ color: scoreColor(s.momentum_score) }}>M {s.momentum_score.toFixed(0)}</span>
                  )}
                </div>
                {s.top_gainer && (
                  <div className="mt-1.5 text-[11px] text-textSub font-mono truncate">
                    ↑ {s.top_gainer.ticker} {pctStr(s.top_gainer.change_pct)}
                  </div>
                )}
              </button>
            )
          })}
        </div>
      </Card>

      {/* Detail panel */}
      {selectedSector && (
        <Card padding="md">
          <Card.Header
            title={`${selectedSector.name} — Constituents`}
            subtitle={`${selectedSector.stock_count} stocks · avg P/E ${selectedSector.avg_pe ?? '—'} · avg ROE ${selectedSector.avg_roe ?? '—'}%`}
            right={
              <div className="flex items-center gap-3 text-xs font-mono">
                <span className="text-textMuted">1W {pctStr(selectedSector.week_pct)}</span>
                <span className="text-textMuted">1M {pctStr(selectedSector.month_pct)}</span>
              </div>
            }
          />
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="border-b border-border/50 text-textMuted text-xs font-semibold uppercase">
                  <th className="py-2">Ticker</th>
                  <th className="py-2 text-right">Price</th>
                  <th className="py-2 text-right">Change</th>
                  <th className="py-2 text-right">Composite</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/30">
                {selectedSector.components.map((c) => {
                  const up = c.change_pct >= 0
                  return (
                    <tr key={c.ticker} className="hover:bg-elevated/40 cursor-pointer" onClick={() => router.push(`/stocks/${c.ticker}`)}>
                      <td className="py-2.5">
                        <span className="font-mono font-bold text-brand">{c.ticker}</span>
                        <span className="text-[11px] text-textMuted ml-2">{c.name}</span>
                      </td>
                      <td className="py-2.5 text-right font-mono text-textPrimary">₹{c.price.toFixed(2)}</td>
                      <td className={`py-2.5 text-right font-mono font-semibold ${up ? 'text-success' : 'text-danger'}`}>{pctStr(c.change_pct)}</td>
                      <td className="py-2.5 text-right">
                        {c.composite_score != null && (
                          <span className="badge text-xs" style={{ backgroundColor: `${scoreColor(c.composite_score)}15`, color: scoreColor(c.composite_score) }}>
                            {c.composite_score.toFixed(0)}
                          </span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </PageShell>
  )
}

function Bar({ label, value, total, color }: { label: string; value: number; total: number; color: string }) {
  const h = total > 0 ? Math.max(8, (value / total) * 100) : 8
  return (
    <div className="flex-1 flex flex-col items-center justify-end h-full" title={`${label}: ${value}`}>
      <div className="w-full rounded-t" style={{ height: `${h}%`, backgroundColor: color, opacity: 0.8 }} />
    </div>
  )
}

function MoverList({ items, positive, onClick }: { items: { ticker: string; name: string; price: number; change_pct: number }[]; positive?: boolean; onClick: (t: string) => void }) {
  return (
    <div className="space-y-1">
      {items.map((m) => (
        <div key={m.ticker} onClick={() => onClick(m.ticker)}
          className="flex justify-between items-center py-1.5 px-2 hover:bg-elevated/50 rounded cursor-pointer">
          <span className={`font-mono font-bold text-sm ${positive ? 'text-success' : 'text-danger'}`}>{m.ticker}</span>
          <div className="text-right">
            <div className="font-mono text-textPrimary text-xs">₹{m.price.toFixed(1)}</div>
            <div className={`font-mono text-[11px] font-semibold ${m.change_pct >= 0 ? 'text-success' : 'text-danger'}`}>{pctStr(m.change_pct)}</div>
          </div>
        </div>
      ))}
    </div>
  )
}
