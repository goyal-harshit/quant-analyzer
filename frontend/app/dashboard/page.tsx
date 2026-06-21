// /frontend/app/page.tsx
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { TrendingUp, TrendingDown, RefreshCw, Layers, GitCompareArrows, LineChart, Grid3x3, Filter, ArrowUpRight } from 'lucide-react'
import { useMarketSummary, useTopGainersLosers, useSectorPerformance, useFactorSignals } from '@/lib/hooks'
import { useAuth } from '@/components/auth/AuthProvider'
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

const QUICK_ACTIONS = [
  { label: 'Compare Stocks', href: '/compare', icon: GitCompareArrows, hint: 'Side-by-side analysis' },
  { label: 'Paper Trade', href: '/simulator', icon: LineChart, hint: 'Practice with ₹ virtual' },
  { label: 'Sector Heatmap', href: '/sectors', icon: Grid3x3, hint: 'Rotation & breadth' },
  { label: 'Screener', href: '/screener', icon: Filter, hint: 'Filter the universe' },
]

// Dashboard summary index names → Yahoo symbols (for the clickable detail links).
const INDEX_SYMBOL: Record<string, string> = {
  'NIFTY 50': '^NSEI',
  'SENSEX': '^BSESN',
  'BANK NIFTY': '^NSEBANK',
  'INDIA VIX': '^INDIAVIX',
}

function greeting(): string {
  // IST hour for an India-first product.
  const h = Number(new Date().toLocaleString('en-US', { hour: '2-digit', hour12: false, timeZone: 'Asia/Kolkata' }))
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}

export default function Dashboard() {
  const router = useRouter()
  const { user } = useAuth()
  const [refreshSeed, setRefreshSeed] = useState(0)

  // Real hooks querying backend APIs
  const { data: indices, isLoading: indicesLoading } = useMarketSummary(refreshSeed)
  const { data: movers, isLoading: moversLoading } = useTopGainersLosers(refreshSeed)
  const { data: sectorPerf, isLoading: sectorsLoading } = useSectorPerformance(refreshSeed)
  const { data: factorSignals, isLoading: factorsLoading } = useFactorSignals(refreshSeed)

  const handleStockClick = (ticker: string) => {
    router.push(`/stocks/${ticker}`)
  }

  // Only block the first paint on the fast indices query. The heavier sections
  // (movers, sectors, factor signals) fill in with their own inline loaders, so
  // the page appears immediately instead of waiting on the slowest fetch.
  const isLoading = indicesLoading && !indices

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

  // Key market insight, derived from live indices + sector breadth.
  const nifty = rawIndices.find((i: any) => i.name === 'NIFTY 50') || rawIndices[0]
  const sectorEntries = Object.entries(sectorPerf || {})
    .map(([name, v]: any) => ({ name, d: v?.['1d'] }))
    .filter((x) => typeof x.d === 'number')
    .sort((a, b) => b.d - a.d)
  const bestSector = sectorEntries[0]
  const worstSector = sectorEntries[sectorEntries.length - 1]
  const niftyUp = (nifty?.change_pct ?? 0) >= 0
  const userName = user?.email ? user.email.split('@')[0] : null

  // Data freshness: surface when any feed fell back to cached/seed data so
  // delayed numbers are never silently presented as live.
  const anySeed = rawIndices.some((i: any) => i.source && i.source !== 'live')
  const latestAsOf = rawIndices
    .map((i: any) => i.as_of)
    .filter(Boolean)
    .sort()
    .pop()
  const asOfLabel = latestAsOf
    ? new Date(latestAsOf).toLocaleString('en-IN', {
        hour: '2-digit',
        minute: '2-digit',
        day: '2-digit',
        month: 'short',
        timeZone: 'Asia/Kolkata',
      })
    : null

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

      {/* Hero: greeting + live market insight + quick actions */}
      <Card padding="md" className="bg-gradient-to-br from-brand/10 via-card to-card border-brand/20">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-textPrimary">
              {greeting()}{userName ? <span className="capitalize">, {userName}</span> : ''} 👋
            </h2>
            <p className="text-sm text-textSub mt-1 flex flex-wrap items-center gap-x-2 gap-y-1">
              <span className={niftyUp ? 'text-success font-semibold' : 'text-danger font-semibold'}>
                {niftyUp ? '📈' : '📉'} Markets {niftyUp ? 'up' : 'down'} {Math.abs(nifty?.change_pct ?? 0).toFixed(2)}%
              </span>
              {bestSector && (
                <span className="text-textMuted">
                  · Best sector: <span className="text-success font-medium">{bestSector.name} {bestSector.d >= 0 ? '+' : ''}{bestSector.d.toFixed(2)}%</span>
                </span>
              )}
              {worstSector && worstSector !== bestSector && (
                <span className="text-textMuted">
                  · Weakest: <span className="text-danger font-medium">{worstSector.name} {worstSector.d.toFixed(2)}%</span>
                </span>
              )}
            </p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {QUICK_ACTIONS.map(({ label, href, icon: Icon, hint }) => (
              <button
                key={href}
                onClick={() => router.push(href)}
                className="group flex flex-col gap-1 px-3 py-2.5 bg-elevated/60 hover:bg-elevated border border-border hover:border-brand/40 rounded-lg text-left transition-all"
              >
                <div className="flex items-center justify-between">
                  <Icon className="w-4 h-4 text-brand" />
                  <ArrowUpRight className="w-3.5 h-3.5 text-textMuted group-hover:text-brand transition-colors" />
                </div>
                <span className="text-xs font-semibold text-textPrimary leading-tight">{label}</span>
                <span className="text-[10px] text-textMuted leading-tight">{hint}</span>
              </button>
            ))}
          </div>
        </div>
      </Card>

      {/* Data freshness indicator */}
      <div className="flex items-center gap-2 -mt-2 mb-1">
        <span
          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold ${
            anySeed
              ? 'bg-danger/10 text-danger'
              : 'bg-success/10 text-success'
          }`}
        >
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              anySeed ? 'bg-danger' : 'bg-success animate-pulse'
            }`}
          />
          {anySeed ? 'Some feeds delayed (cached / offline)' : 'Live NSE/BSE'}
        </span>
        {asOfLabel && (
          <span className="text-[11px] text-textMuted font-mono">
            as of {asOfLabel} IST
          </span>
        )}
      </div>

      {/* Index telemetry row */}
      <div className="flex items-center justify-between -mb-2">
        <span className="text-xs font-bold uppercase tracking-wider text-textMuted">Indices</span>
        <button onClick={() => router.push('/indices')} className="flex items-center gap-1 text-xs font-semibold text-brand hover:text-brand/80">
          View all 19 indices <ArrowUpRight className="w-3.5 h-3.5" />
        </button>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {rawIndices.map((idx: any) => {
          const isPos = idx.change_pct >= 0
          const isVix = idx.name === 'INDIA VIX'
          const sym = INDEX_SYMBOL[idx.name]
          return (
            <button
              key={idx.name}
              onClick={() => sym && router.push(`/indices/${encodeURIComponent(sym)}`)}
              className="group text-left rounded-xl border border-border bg-card hover:border-brand/40 hover:bg-elevated/30 shadow-card p-3 transition-all"
            >
              <div className="flex items-center justify-between">
                <div className="metric-label">{idx.name}</div>
                <ArrowUpRight className="w-3.5 h-3.5 text-textMuted group-hover:text-brand transition-colors" />
              </div>
              <div className="metric-value mt-1.5 text-2xl font-mono">
                {idx.last ? idx.last.toLocaleString('en-IN') : 'N/A'}
              </div>
              <div className={`flex items-center gap-1 font-mono text-xs font-semibold mt-1 ${
                isVix ? (isPos ? 'text-warn' : 'text-success') : (isPos ? 'text-success' : 'text-danger')
              }`}>
                {isPos ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                {isPos ? '+' : ''}{(idx.change_pct ?? 0).toFixed(2)}%
              </div>
            </button>
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
                {factorsLoading && !((resolvedFactorSignals as any)?.signals?.length) && (
                  <tr><td colSpan={5} className="py-8 text-center text-textMuted text-xs">
                    <RefreshCw className="w-4 h-4 animate-spin inline mr-2 align-middle" />Ranking the universe…
                  </td></tr>
                )}
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
            {sectorsLoading && !Object.keys(resolvedSectorPerf || {}).length && (
              <div className="py-6 text-center text-textMuted text-xs">
                <RefreshCw className="w-4 h-4 animate-spin inline mr-2 align-middle" />Loading sectors…
              </div>
            )}
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
            {moversLoading && !(resolvedMovers?.gainers?.length) && (
              <div className="py-6 text-center text-textMuted text-xs">
                <RefreshCw className="w-4 h-4 animate-spin inline mr-2 align-middle" />Loading movers…
              </div>
            )}
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
            {moversLoading && !(resolvedMovers?.losers?.length) && (
              <div className="py-6 text-center text-textMuted text-xs">
                <RefreshCw className="w-4 h-4 animate-spin inline mr-2 align-middle" />Loading movers…
              </div>
            )}
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
