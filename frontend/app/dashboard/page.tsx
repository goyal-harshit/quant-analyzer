// /frontend/app/page.tsx
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { TrendingUp, TrendingDown, RefreshCw, Layers } from 'lucide-react'
import { useMarketSummary, useTopGainersLosers, useSectorPerformance, useFactorSignals } from '@/lib/hooks'
import PageShell from '@/components/layout/PageShell'
import Card from '@/components/ui/Card'
import { scoreColor } from '@/lib/stockData'

export default function Dashboard() {
  const router = useRouter()
  const [refreshSeed, setRefreshSeed] = useState(0)

  // Real hooks querying backend APIs
  const { data: indices, isLoading: indicesLoading } = useMarketSummary(refreshSeed)
  const { data: movers, isLoading: moversLoading } = useTopGainersLosers(refreshSeed)
  const { data: sectorPerf, isLoading: sectorsLoading } = useSectorPerformance(refreshSeed)
  const { data: factorSignals, isLoading: factorsLoading } = useFactorSignals(refreshSeed)

  const handleStockClick = (ticker: string) => {
    router.push(`/stocks/${ticker}`)
  }

  const isLoading = indicesLoading || moversLoading || sectorsLoading || factorsLoading

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
        <RefreshCw className="w-8 h-8 text-brand animate-spin" />
        <span className="text-textSub text-sm">QuantAI is synchronizing live NSE/BSE feeds...</span>
      </div>
    )
  }

  // Handle API format: indices can be array or dict
  const rawIndices = Array.isArray(indices) ? indices : []

  return (
    <PageShell 
      title="Quant Terminal" 
      subtitle="Real-time multi-factor signals & market telemetry"
      actions={
        <button 
          onClick={() => { setRefreshSeed(prev => prev + 1) }}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-elevated hover:bg-border border border-border rounded-lg text-xs font-semibold text-textSub hover:text-textPrimary transition-all"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh Feed
        </button>
      }
    >
      {/* Index telemetry row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {rawIndices.map((idx: any) => {
          const isPos = idx.change_pct >= 0
          return (
            <Card key={idx.name} padding="sm">
              <div className="metric-label">{idx.name}</div>
              <div className="metric-value mt-1.5 text-2xl font-mono">
                {idx.last ? idx.last.toLocaleString('en-IN') : 'N/A'}
              </div>
              <div className={`flex items-center gap-1 font-mono text-xs font-semibold mt-1 ${isPos ? 'text-success' : 'text-danger'}`}>
                {isPos ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                {isPos ? '+' : ''}{(idx.change_pct ?? 0).toFixed(2)}%
              </div>
            </Card>
          )
        })}
      </div>

      {/* Main Grid: Sector Allocation and Factors */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Factor signals card */}
        <Card padding="md" className="col-span-2">
          <Card.Header 
            title="Composite Factor Rankings" 
            subtitle="Top ranked constituents in the Nifty 500 universe" 
          />
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-border/50 text-textMuted text-xs font-semibold uppercase">
                  <th className="py-2.5">Ticker</th>
                  <th className="py-2.5">Sector</th>
                  <th className="py-2.5 text-right">Price</th>
                  <th className="py-2.5 text-right">Change</th>
                  <th className="py-2.5 text-right">Composite</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/30">
                {((factorSignals as any)?.signals ?? []).slice(0, 7).map((stk: any) => {
                  const isPos = stk.change_pct >= 0
                  return (
                    <tr 
                      key={stk.ticker} 
                      className="hover:bg-elevated/40 cursor-pointer transition-colors"
                      onClick={() => handleStockClick(stk.ticker)}
                    >
                      <td className="py-3 font-mono font-bold text-brand">{stk.ticker}</td>
                      <td className="py-3 text-textSub text-xs">{stk.sector}</td>
                      <td className="py-3 text-right font-mono text-textPrimary">₹{stk.price?.toFixed(1)}</td>
                      <td className={`py-3 text-right font-mono text-xs font-semibold ${isPos ? 'text-success' : 'text-danger'}`}>
                        {isPos ? '+' : ''}{(stk.change_pct ?? 0).toFixed(2)}%
                      </td>
                      <td className="py-3 text-right">
                        <span 
                          className="badge text-xs"
                          style={{
                            backgroundColor: `${scoreColor(stk.composite_score ?? 60)}15`,
                            color: scoreColor(stk.composite_score ?? 60),
                          }}
                        >
                          {stk.composite_score ?? 60}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </Card>

        {/* Sector strength index */}
        <Card padding="md">
          <Card.Header title="Sector Strengths" subtitle="Daily change across key industry indices" />
          <div className="space-y-3.5">
            {Object.entries(sectorPerf || {}).slice(0, 6).map(([sec, val]: any) => {
              const isPos = val['1d'] >= 0
              return (
                <div key={sec} className="flex justify-between items-center py-1.5 border-b border-border/30 last:border-0">
                  <div className="flex items-center gap-2">
                    <Layers className="w-3.5 h-3.5 text-brand" />
                    <span className="text-textSub font-medium">{sec}</span>
                  </div>
                  <span className={`font-mono text-xs font-semibold ${isPos ? 'text-success' : 'text-danger'}`}>
                    {isPos ? '+' : ''}{(val['1d'] ?? 0).toFixed(2)}%
                  </span>
                </div>
              )
            })}
          </div>
        </Card>
      </div>

      {/* Gainers and Losers tables */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Gainers */}
        <Card padding="md">
          <Card.Header title="Top Movers — Gainers" icon={TrendingUp} />
          <div className="space-y-1">
            {(movers?.gainers ?? []).map((stk: any) => (
              <div 
                key={stk.ticker}
                onClick={() => handleStockClick(stk.ticker)}
                className="flex justify-between items-center py-2.5 px-2 hover:bg-elevated/50 rounded-lg cursor-pointer transition-colors border-b border-border/30 last:border-0"
              >
                <div>
                  <div className="font-mono font-bold text-success text-sm">{stk.ticker}</div>
                  <div className="text-[11px] text-textMuted">{stk.name}</div>
                </div>
                <div className="text-right">
                  <div className="font-mono text-textPrimary text-sm">₹{stk.price?.toFixed(1)}</div>
                  <div className="font-mono text-success text-xs font-semibold">+{stk.change_pct?.toFixed(2)}%</div>
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Losers */}
        <Card padding="md">
          <Card.Header title="Top Movers — Losers" icon={TrendingDown} />
          <div className="space-y-1">
            {(movers?.losers ?? []).map((stk: any) => (
              <div 
                key={stk.ticker}
                onClick={() => handleStockClick(stk.ticker)}
                className="flex justify-between items-center py-2.5 px-2 hover:bg-elevated/50 rounded-lg cursor-pointer transition-colors border-b border-border/30 last:border-0"
              >
                <div>
                  <div className="font-mono font-bold text-danger text-sm">{stk.ticker}</div>
                  <div className="text-[11px] text-textMuted">{stk.name}</div>
                </div>
                <div className="text-right">
                  <div className="font-mono text-textPrimary text-sm">₹{stk.price?.toFixed(1)}</div>
                  <div className="font-mono text-danger text-xs font-semibold">{stk.change_pct?.toFixed(2)}%</div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </PageShell>
  )
}
