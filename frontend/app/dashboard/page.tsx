// /frontend/app/page.tsx
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { TrendingUp, TrendingDown, RefreshCw, Layers } from 'lucide-react'
import { useMarketSummary, useTopGainersLosers, useSectorPerformance, useFactorSignals } from '@/lib/hooks'
import PageShell from '@/components/layout/PageShell'
import Card from '@/components/ui/Card'
import { scoreColor } from '@/lib/stockData'

const DEMO_INDICES = [
  { name: 'NIFTY 50', last: 24857.3, change_pct: 0.62 },
  { name: 'SENSEX', last: 81721.1, change_pct: 0.58 },
  { name: 'NIFTY BANK', last: 53412.8, change_pct: -0.31 },
  { name: 'NIFTY IT', last: 38194.5, change_pct: 1.24 },
]

const DEMO_FACTOR_SIGNALS = {
  signals: [
    { ticker: 'RELIANCE', sector: 'Energy', price: 2847.5, change_pct: 0.82, composite_score: 78 },
    { ticker: 'TCS', sector: 'IT', price: 3921.0, change_pct: 1.43, composite_score: 85 },
    { ticker: 'HDFCBANK', sector: 'Banking', price: 1712.3, change_pct: -0.29, composite_score: 71 },
    { ticker: 'INFY', sector: 'IT', price: 1843.6, change_pct: 2.11, composite_score: 82 },
    { ticker: 'ICICIBANK', sector: 'Banking', price: 1284.9, change_pct: 0.55, composite_score: 76 },
    { ticker: 'BHARTIARTL', sector: 'Telecom', price: 1672.4, change_pct: 1.87, composite_score: 80 },
    { ticker: 'MARUTI', sector: 'Auto', price: 12340.0, change_pct: -0.48, composite_score: 66 },
  ]
}

const DEMO_MOVERS = {
  gainers: [
    { ticker: 'INFY', name: 'Infosys Ltd', price: 1843.6, change_pct: 2.11 },
    { ticker: 'BHARTIARTL', name: 'Bharti Airtel', price: 1672.4, change_pct: 1.87 },
    { ticker: 'WIPRO', name: 'Wipro Ltd', price: 563.2, change_pct: 1.65 },
    { ticker: 'HCLTECH', name: 'HCL Technologies', price: 1924.8, change_pct: 1.52 },
    { ticker: 'TCS', name: 'Tata Consultancy', price: 3921.0, change_pct: 1.43 },
  ],
  losers: [
    { ticker: 'ONGC', name: 'Oil & Natural Gas', price: 248.3, change_pct: -1.82 },
    { ticker: 'POWERGRID', name: 'Power Grid Corp', price: 312.7, change_pct: -1.14 },
    { ticker: 'NTPC', name: 'NTPC Ltd', price: 378.4, change_pct: -0.93 },
    { ticker: 'MARUTI', name: 'Maruti Suzuki', price: 12340.0, change_pct: -0.48 },
    { ticker: 'HDFCBANK', name: 'HDFC Bank', price: 1712.3, change_pct: -0.29 },
  ],
}

const DEMO_SECTOR_PERF: Record<string, { '1d': number }> = {
  'Information Technology': { '1d': 1.68 },
  'Telecom': { '1d': 1.43 },
  'Consumer Goods': { '1d': 0.74 },
  'Financial Services': { '1d': 0.21 },
  'Energy': { '1d': -0.38 },
  'Utilities': { '1d': -1.02 },
}

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

  // Fall back to demo data when backend is unavailable
  const rawIndices = (Array.isArray(indices) && indices.length > 0) ? indices : DEMO_INDICES
  const resolvedMovers = (movers?.gainers?.length) ? movers : DEMO_MOVERS
  const resolvedSectorPerf = (sectorPerf && Object.keys(sectorPerf).length > 0) ? sectorPerf : DEMO_SECTOR_PERF
  const resolvedFactorSignals = ((factorSignals as any)?.signals?.length) ? factorSignals : DEMO_FACTOR_SIGNALS
  const isDemo = !indices || (Array.isArray(indices) && indices.length === 0)

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
      {isDemo && (
        <div className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-warn/10 border border-warn/30 text-warn text-xs font-medium">
          <span>⚠</span>
          <span>Live backend not connected — showing demo data. Deploy the backend on Render to see real NSE/BSE feeds.</span>
        </div>
      )}

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
                {((resolvedFactorSignals as any)?.signals ?? []).slice(0, 7).map((stk: any) => {
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
            {Object.entries(resolvedSectorPerf || {}).slice(0, 6).map(([sec, val]: any) => {
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
            {(resolvedMovers?.gainers ?? []).map((stk: any) => (
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
            {(resolvedMovers?.losers ?? []).map((stk: any) => (
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
