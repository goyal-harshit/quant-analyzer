'use client'

import { useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, TrendingUp, TrendingDown, RefreshCw, Layers } from 'lucide-react'
import PageShell from '@/components/layout/PageShell'
import Card from '@/components/ui/Card'
import StockChart from '@/components/stocks/StockChart'
import { indicesApi, stocksApi } from '@/lib/api'
import { slugToSymbol } from '@/lib/indices'

const pctStr = (n: number | null | undefined) => `${(n ?? 0) >= 0 ? '+' : ''}${(n ?? 0).toFixed(2)}%`

export default function IndexDetailClient() {
  const params = useParams()
  const router = useRouter()
  const symbol = slugToSymbol((params?.slug as string) || '') || ''
  const [refreshSeed, setRefreshSeed] = useState(0)

  const { data: detail, isLoading } = useQuery({
    queryKey: ['index', 'detail', symbol, refreshSeed],
    queryFn: () => indicesApi.detail(symbol, refreshSeed > 0),
    enabled: !!symbol,
    refetchInterval: 60000,
  })
  const { data: historyData } = useQuery({
    queryKey: ['index', 'history', symbol],
    queryFn: () => stocksApi.getHistory(symbol, '1y'),
    enabled: !!symbol,
  })

  const history = historyData?.data ?? []
  const up = (detail?.change_pct ?? 0) >= 0
  const isVix = detail?.group === 'Volatility'
  const upColor = isVix ? (up ? 'text-warn' : 'text-success') : (up ? 'text-success' : 'text-danger')

  if (isLoading && !detail) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
        <RefreshCw className="w-8 h-8 text-brand animate-spin" />
        <span className="text-textSub text-sm">Loading index…</span>
      </div>
    )
  }

  return (
    <PageShell
      title={detail?.name || symbol || 'Index'}
      subtitle={`${detail?.group || 'Index'} · live NSE/BSE`}
      actions={
        <div className="flex items-center gap-2">
          <button onClick={() => router.push('/indices')}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-elevated border border-border rounded-lg text-xs font-semibold text-textSub hover:text-textPrimary">
            <ArrowLeft className="w-3.5 h-3.5" /> All Indices
          </button>
          <button onClick={() => setRefreshSeed((p) => p + 1)}
            aria-label="Refresh index data"
            className="p-1.5 bg-elevated border border-border rounded-lg text-textSub hover:text-textPrimary">
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      }
    >
      {/* Header metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card padding="sm">
          <div className="metric-label">Level</div>
          <div className="metric-value mt-1.5 text-2xl font-mono">{detail?.last?.toLocaleString('en-IN') ?? '—'}</div>
        </Card>
        <Card padding="sm">
          <div className="metric-label">Day Change</div>
          <div className={`metric-value mt-1.5 text-2xl font-mono flex items-center gap-1 ${upColor}`}>
            {up ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
            {pctStr(detail?.change_pct)}
          </div>
        </Card>
        <Card padding="sm">
          <div className="metric-label">Advancers</div>
          <div className="metric-value mt-1.5 text-2xl font-mono text-success">{detail?.advancers ?? '—'}</div>
        </Card>
        <Card padding="sm">
          <div className="metric-label">Decliners</div>
          <div className="metric-value mt-1.5 text-2xl font-mono text-danger">{detail?.decliners ?? '—'}</div>
        </Card>
      </div>

      {/* Chart */}
      {history.length > 0 ? (
        <StockChart data={history} />
      ) : (
        <Card padding="lg" className="text-center text-textMuted">Loading index chart…</Card>
      )}

      {/* Constituents */}
      <Card padding="md">
        <Card.Header
          title="Constituents"
          subtitle={`${detail?.constituents?.length ?? 0} stocks · sorted by today's change`}
          icon={Layers}
        />
        {(detail?.constituents?.length ?? 0) === 0 ? (
          <div className="text-sm text-textMuted py-6 text-center">
            {isVix ? 'Volatility index — no constituents.' : 'No constituent data.'}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-sm">
              <thead>
                <tr className="border-b border-border/50 text-textMuted text-xs font-semibold uppercase">
                  <th className="py-2.5">Stock</th>
                  <th className="py-2.5">Sector</th>
                  <th className="py-2.5 text-right">Price</th>
                  <th className="py-2.5 text-right">Change</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/30">
                {detail!.constituents.map((c) => {
                  const cu = c.change_pct >= 0
                  return (
                    <tr key={c.ticker} className="hover:bg-elevated/40 cursor-pointer" onClick={() => router.push(`/stocks/${c.ticker}`)}>
                      <td className="py-2.5">
                        <span className="font-mono font-bold text-brand">{c.ticker}</span>
                        <span className="text-[11px] text-textMuted ml-2 truncate">{c.name}</span>
                      </td>
                      <td className="py-2.5 text-textSub text-xs">{c.sector}</td>
                      <td className="py-2.5 text-right font-mono text-textPrimary">₹{c.price.toLocaleString('en-IN')}</td>
                      <td className={`py-2.5 text-right font-mono font-semibold ${cu ? 'text-success' : 'text-danger'}`}>{pctStr(c.change_pct)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </PageShell>
  )
}
