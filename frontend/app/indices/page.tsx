'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { TrendingUp, TrendingDown, RefreshCw, ArrowUpRight } from 'lucide-react'
import PageShell from '@/components/layout/PageShell'
import Card from '@/components/ui/Card'
import { indicesApi, type IndexQuote } from '@/lib/api'

const GROUP_ORDER = ['Broad', 'Sectoral', 'Thematic', 'Volatility']
const pctStr = (n: number) => `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`

export default function IndicesPage() {
  const router = useRouter()
  const [refreshSeed, setRefreshSeed] = useState(0)

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['indices', 'all', refreshSeed],
    queryFn: () => indicesApi.all(refreshSeed > 0),
    staleTime: 30000,
    refetchInterval: 60000,
  })

  const indices = data?.indices ?? []
  const grouped = GROUP_ORDER.map((g) => ({ group: g, items: indices.filter((i) => i.group === g) })).filter((g) => g.items.length)

  const open = (symbol: string) => router.push(`/indices/${encodeURIComponent(symbol)}`)

  return (
    <PageShell
      title="Market Indices"
      subtitle="All live NSE/BSE indices — broad, sectoral & thematic. Click any to see its chart & constituents."
      actions={
        <button onClick={() => setRefreshSeed((p) => p + 1)}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-elevated hover:bg-border border border-border rounded-lg text-xs font-semibold text-textSub hover:text-textPrimary transition-all">
          <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin' : ''}`} /> Refresh
        </button>
      }
    >
      {isLoading ? (
        <div className="flex flex-col items-center justify-center min-h-[300px] gap-4">
          <RefreshCw className="w-8 h-8 text-brand animate-spin" />
          <span className="text-textSub text-sm">Loading live indices…</span>
        </div>
      ) : (
        grouped.map(({ group, items }) => (
          <div key={group} className="space-y-3">
            <h2 className="text-xs font-bold uppercase tracking-wider text-textMuted">{group}</h2>
            <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
              {items.map((idx: IndexQuote) => {
                const up = idx.change_pct >= 0
                const isVix = idx.group === 'Volatility'
                return (
                  <button key={idx.symbol} onClick={() => open(idx.symbol)}
                    className="group text-left rounded-xl border border-border bg-card hover:border-brand/40 hover:bg-elevated/40 p-4 transition-all">
                    <div className="flex items-center justify-between">
                      <span className="metric-label">{idx.name}</span>
                      <ArrowUpRight className="w-3.5 h-3.5 text-textMuted group-hover:text-brand transition-colors" />
                    </div>
                    <div className="metric-value mt-1.5 text-xl font-mono">{idx.last.toLocaleString('en-IN')}</div>
                    <div className={`flex items-center gap-1 font-mono text-xs font-semibold mt-1 ${
                      isVix ? (up ? 'text-warn' : 'text-success') : (up ? 'text-success' : 'text-danger')
                    }`}>
                      {up ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                      {pctStr(idx.change_pct)}
                    </div>
                  </button>
                )
              })}
            </div>
          </div>
        ))
      )}
    </PageShell>
  )
}
