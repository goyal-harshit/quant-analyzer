// /frontend/app/stocks/[ticker]/page.tsx
'use client'

import { useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { ArrowLeft, RefreshCw, Zap, TrendingUp, TrendingDown } from 'lucide-react'
import { useStockQuote, useStockFundamentals, useStockHistory, useStockInsight } from '@/lib/hooks'
import PageShell from '@/components/layout/PageShell'
import Card from '@/components/ui/Card'
import StockChart from '@/components/stocks/StockChart'
import FundamentalsPanel from '@/components/stocks/FundamentalsPanel'
import { scoreColor } from '@/lib/stockData'

export default function StockDetail() {
  const params = useParams()
  const router = useRouter()
  const ticker = (params.ticker as string).toUpperCase()
  
  const [reportType, setReportType] = useState('full')
  
  // Real data fetching hooks
  const { data: quote, isLoading: quoteLoading, refetch: refetchQuote } = useStockQuote(ticker)
  const { data: fundamentals, isLoading: fundLoading } = useStockFundamentals(ticker)
  const { data: historyData, isLoading: historyLoading } = useStockHistory(ticker, '5y')
  const { data: insight, isLoading: insightLoading, refetch: refetchInsight } = useStockInsight(ticker, true)

  const handleBack = () => {
    router.back()
  }

  const isLoading = quoteLoading || fundLoading || historyLoading

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
        <RefreshCw className="w-8 h-8 text-brand animate-spin" />
        <span className="text-textSub text-sm">Loading market telemetry for {ticker}...</span>
      </div>
    )
  }

  const changePct = quote?.change_pct ?? 0
  const isPositive = changePct >= 0
  const history = historyData?.data ?? []

  return (
    <PageShell 
      title={`${ticker}`} 
      subtitle={quote?.name || 'NSE Equity'}
      actions={
        <button
          onClick={handleBack}
          className="flex items-center gap-2 px-3 py-1.5 bg-elevated hover:bg-border border border-border rounded-lg text-xs font-semibold text-textSub hover:text-textPrimary transition-all"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Back
        </button>
      }
    >
      {/* Overview stats bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card padding="sm">
          <div className="metric-label">Current Price</div>
          <div className="metric-value mt-1 text-2xl font-mono">
            ₹{(quote?.price ?? 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </div>
          <div className={`flex items-center gap-1.5 font-mono text-xs font-semibold mt-1 ${isPositive ? 'text-success' : 'text-danger'}`}>
            {isPositive ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
            {isPositive ? '+' : ''}{(quote?.change_pct ?? 0).toFixed(2)}%
          </div>
        </Card>

        <Card padding="sm">
          <div className="metric-label">52 Week High</div>
          <div className="metric-value mt-1 text-xl font-mono">
            ₹{(quote?.fifty_two_week_high ?? quote?.price ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 1 })}
          </div>
        </Card>

        <Card padding="sm">
          <div className="metric-label">52 Week Low</div>
          <div className="metric-value mt-1 text-xl font-mono">
            ₹{(quote?.fifty_two_week_low ?? quote?.price ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 1 })}
          </div>
        </Card>

        <Card padding="sm">
          <div className="metric-label">Quant Score</div>
          <div className="mt-1 flex items-center gap-2">
            <span 
              className="badge text-sm py-1 px-3 font-mono font-bold"
              style={{
                backgroundColor: `${scoreColor(fundamentals?.factor_scores?.composite ?? 50)}22`,
                color: scoreColor(fundamentals?.factor_scores?.composite ?? 50),
                borderColor: `${scoreColor(fundamentals?.factor_scores?.composite ?? 50)}44`
              }}
            >
              {fundamentals?.factor_scores?.composite ?? 'N/A'}
            </span>
            <span className="text-[10px] text-textMuted uppercase tracking-wider font-semibold">
              Composite Percentile
            </span>
          </div>
        </Card>
      </div>

      {/* Main Stock Chart */}
      {history.length > 0 ? (
        <StockChart data={history} />
      ) : (
        <Card padding="lg" className="text-center py-12 text-textMuted">
          No historical price chart available.
        </Card>
      )}

      {/* Fundamentals Grid */}
      <h2 className="section-title mt-4">Fundamental Ratios</h2>
      <FundamentalsPanel data={fundamentals} />

      {/* AI Research segment */}
      <h2 className="section-title mt-4">AI Research & Insights</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card padding="md" className="col-span-2 flex flex-col justify-between min-h-[300px]">
          <Card.Header 
            title="QuantAI Analysis Narrative" 
            subtitle="Powered by local self-hosted Llama 3.2 model"
            right={
              <button 
                onClick={() => { refetchInsight() }}
                className="flex items-center gap-1.5 px-3 py-1 bg-brand text-white rounded text-xs font-semibold hover:bg-brand-hover transition-colors"
              >
                <Zap className="w-3.5 h-3.5" />
                Regenerate
              </button>
            }
          />
          <div className="flex-1 overflow-y-auto text-sm text-textPrimary leading-relaxed whitespace-pre-line py-2">
            {insight?.analysis || 'No AI Insight computed for this stock yet. Click regenerate to pull.'}
          </div>
          <div className="text-[10px] text-textMuted border-t border-border/50 pt-2.5 mt-2">
            ⚠️ Disclaimer: Educational snapshot. This is not professional investment advice.
          </div>
        </Card>

        {/* Factors Breakdown */}
        <Card padding="md">
          <Card.Header title="Factor Strengths" subtitle="Score out of 100 relative to universe" />
          <div className="space-y-4 py-2">
            {[
              { name: 'Momentum', val: fundamentals?.factor_scores?.momentum ?? 50 },
              { name: 'Quality', val: fundamentals?.factor_scores?.quality ?? 50 },
              { name: 'Value', val: fundamentals?.factor_scores?.value ?? 50 },
              { name: 'Growth', val: fundamentals?.factor_scores?.growth ?? 50 },
              { name: 'Low Volatility', val: fundamentals?.factor_scores?.low_volatility ?? 50 },
            ].map((f) => (
              <div key={f.name} className="space-y-1.5">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-textSub font-medium">{f.name}</span>
                  <span className="font-mono font-bold" style={{ color: scoreColor(f.val) }}>
                    {f.val}/100
                  </span>
                </div>
                <div className="h-1.5 bg-border rounded-full overflow-hidden">
                  <div 
                    className="h-full rounded-full" 
                    style={{ 
                      width: `${f.val}%`,
                      backgroundColor: scoreColor(f.val)
                    }} 
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </PageShell>
  )
}
