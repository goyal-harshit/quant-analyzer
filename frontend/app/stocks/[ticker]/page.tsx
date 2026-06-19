// /frontend/app/stocks/[ticker]/page.tsx
'use client'

import { useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { 
  ArrowLeft, RefreshCw, Zap, TrendingUp, TrendingDown, 
  DollarSign, ShieldAlert, Award, Compass, Sparkles, CheckCircle,
  HelpCircle, ArrowUpRight, Percent, Calendar, Target
} from 'lucide-react'

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
  
  const [includeAi, setIncludeAi] = useState(true)
  
  // Real data fetching hooks
  const { data: quote, isLoading: quoteLoading, refetch: refetchQuote } = useStockQuote(ticker)
  const { data: fundamentals, isLoading: fundLoading } = useStockFundamentals(ticker)
  const { data: historyData, isLoading: historyLoading } = useStockHistory(ticker, '5y')
  const { data: insight, isLoading: insightLoading, refetch: refetchInsight } = useStockInsight(ticker, includeAi)

  const handleBack = () => {
    router.push('/screener')
  }

  const isLoading = quoteLoading || fundLoading || historyLoading

  // Parsing helper to convert raw AI bullet points into structured visual cards
  const parseAIAnalysis = (text: string | undefined | null) => {
    if (!text) return null
    const lines = text.split('\n').map(l => l.trim()).filter(l => l.length > 0)
    
    const items = lines.map(line => {
      // Matches: "- Valuation: text" or "1. Momentum: text"
      const match = line.match(/^[-•\d\.\s]*\s*(Valuation|Momentum|Risk|Verdict)\s*:\s*(.*)$/i)
      if (match) {
        return {
          title: match[1].charAt(0).toUpperCase() + match[1].slice(1).toLowerCase(),
          content: match[2]
        }
      }
      return null
    }).filter((item): item is { title: string; content: string } => item !== null)
    
    if (items.length >= 3) {
      return items
    }
    return null
  }

  // Loading skeleton screen
  if (isLoading) {
    return (
      <div className="flex flex-col gap-6 animate-pulse p-4 md:p-8">
        <div className="flex justify-between items-center pb-4 border-b border-border/50">
          <div className="space-y-2.5">
            <div className="h-9 w-40 bg-elevated rounded-lg" />
            <div className="h-4 w-72 bg-elevated rounded-lg" />
          </div>
          <div className="h-10 w-24 bg-elevated rounded-lg" />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-24 bg-card border border-border/50 rounded-xl p-4 space-y-3">
              <div className="h-3.5 w-20 bg-elevated rounded" />
              <div className="h-6 w-32 bg-elevated rounded" />
              <div className="h-3 w-16 bg-elevated rounded" />
            </div>
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-2 space-y-6">
            <div className="h-[460px] bg-card border border-border/50 rounded-xl" />
            <div className="h-80 bg-card border border-border/50 rounded-xl" />
          </div>
          <div className="space-y-6">
            <div className="h-[380px] bg-card border border-border/50 rounded-xl" />
            <div className="h-[380px] bg-card border border-border/50 rounded-xl" />
          </div>
        </div>
      </div>
    )
  }

  const changePct = quote?.change_pct ?? 0
  const isPositive = changePct >= 0
  const history = historyData?.data ?? []
  const parsedAi = parseAIAnalysis(insight?.ai_summary)

  return (
    <PageShell 
      title={`${ticker}`} 
      subtitle={quote?.name || 'NSE Equities Market'}
      actions={
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              refetchQuote()
              refetchInsight()
            }}
            className="flex items-center justify-center p-2 bg-elevated border border-border/80 hover:bg-border/40 text-textSub hover:text-textPrimary rounded-lg transition-all"
            title="Refresh Feed"
          >
            <RefreshCw className={`w-4 h-4 ${(quoteLoading || insightLoading) ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={handleBack}
            className="flex items-center gap-2 px-4 py-2 bg-elevated/80 border border-border/80 hover:bg-border/40 text-textSub hover:text-textPrimary rounded-lg text-xs font-bold transition-all shadow-md"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Screener
          </button>
        </div>
      }
    >
      {/* Top Banner stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Price Card */}
        <div className="glass rounded-xl p-5 border border-border/60 shadow-md bg-card/40 hover:border-brand/40 transition-all duration-300 relative group overflow-hidden">
          <div className="absolute top-0 left-0 w-1 h-full bg-brand group-hover:h-full transition-all" />
          <div className="flex justify-between items-center text-textMuted uppercase tracking-wider font-semibold text-[10px]">
            <span>Current Price</span>
            <DollarSign className="w-3.5 h-3.5 text-brand" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-textPrimary leading-none">
            ₹{(quote?.price ?? 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </div>
          <div className={`flex items-center gap-1 font-mono text-xs font-bold mt-2.5 ${isPositive ? 'text-success' : 'text-danger'}`}>
            {isPositive ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
            {isPositive ? '+' : ''}{(quote?.change_pct ?? 0).toFixed(2)}%
          </div>
        </div>

        {/* 52W High Card */}
        <div className="glass rounded-xl p-5 border border-border/60 shadow-md bg-card/40 hover:border-warn/40 transition-all duration-300 relative group overflow-hidden">
          <div className="absolute top-0 left-0 w-1 h-full bg-warn group-hover:h-full transition-all" />
          <div className="flex justify-between items-center text-textMuted uppercase tracking-wider font-semibold text-[10px]">
            <span>52W High</span>
            <TrendingUp className="w-3.5 h-3.5 text-warn" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-textPrimary leading-none">
            ₹{(quote?.fifty_two_week_high ?? quote?.price ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}
          </div>
          <div className="text-[10px] text-textMuted mt-3">Trailing 12-month peak</div>
        </div>

        {/* 52W Low Card */}
        <div className="glass rounded-xl p-5 border border-border/60 shadow-md bg-card/40 hover:border-purple/40 transition-all duration-300 relative group overflow-hidden">
          <div className="absolute top-0 left-0 w-1 h-full bg-purple group-hover:h-full transition-all" />
          <div className="flex justify-between items-center text-textMuted uppercase tracking-wider font-semibold text-[10px]">
            <span>52W Low</span>
            <TrendingDown className="w-3.5 h-3.5 text-purple" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-textPrimary leading-none">
            ₹{(quote?.fifty_two_week_low ?? quote?.price ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}
          </div>
          <div className="text-[10px] text-textMuted mt-3">Trailing 12-month floor</div>
        </div>

        {/* Quant score Card */}
        <div className="glass rounded-xl p-5 border border-border/60 shadow-md bg-card/40 hover:border-success/40 transition-all duration-300 relative group overflow-hidden">
          <div className="absolute top-0 left-0 w-1 h-full bg-success group-hover:h-full transition-all" />
          <div className="flex justify-between items-center text-textMuted uppercase tracking-wider font-semibold text-[10px]">
            <span>Quant Score</span>
            <Award className="w-3.5 h-3.5 text-success" />
          </div>
          <div className="mt-1.5 flex items-baseline gap-2.5">
            <span 
              className="text-3xl font-mono font-black"
              style={{ color: scoreColor(fundamentals?.factor_scores?.composite ?? 50) }}
            >
              {fundamentals?.factor_scores?.composite ?? '50'}
            </span>
            <span className="text-[9px] text-textMuted uppercase font-bold tracking-widest">
              Percentile
            </span>
          </div>
          <div className="text-[9px] text-textSub mt-2.5 flex items-center gap-1 font-semibold uppercase">
            <Sparkles className="w-3 h-3 text-success animate-pulse" />
            Factor strength score
          </div>
        </div>
      </div>

      {/* Main Content Layout Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
        {/* Left 2 Columns: Chart & Ratios */}
        <div className="md:col-span-2 space-y-6">
          {/* Interactive Price Chart with Duration Options */}
          {history.length > 0 ? (
            <StockChart data={history} />
          ) : (
            <div className="glass border border-border/60 p-8 rounded-xl text-center text-textMuted bg-card/40">
              No historical price telemetry available for {ticker}.
            </div>
          )}

          {/* Fundamentals Grid */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Percent className="w-4.5 h-4.5 text-brand" />
              <h2 className="section-title text-base font-bold uppercase tracking-wider">Corporate Ratios</h2>
            </div>
            <FundamentalsPanel data={fundamentals} />
          </div>
        </div>

        {/* Right Column: AI Analysis & Factor breakdown */}
        <div className="space-y-6">
          {/* QuantAI Research Narrative Card */}
          <div className="glass border border-border/60 bg-gradient-to-b from-[#0a1120] to-[#040914] rounded-xl p-5 md:p-6 shadow-xl relative overflow-hidden flex flex-col justify-between min-h-[350px]">
            {/* Ambient AI Glow background effect */}
            <div className="absolute -top-12 -left-12 w-32 h-32 bg-brand/15 rounded-full blur-[40px] pointer-events-none" />
            
            <div className="flex justify-between items-center pb-3 border-b border-border/40">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-brand animate-bounce" />
                <div>
                  <span className="text-xs font-black text-textPrimary uppercase tracking-widest font-display">
                    QuantAI Insights
                  </span>
                  <div className="text-[10px] text-textMuted mt-0.5 font-mono">
                    llama3.2 @ local-ollama
                  </div>
                </div>
              </div>

              <button
                onClick={() => refetchInsight()}
                disabled={insightLoading}
                className="flex items-center gap-1.5 px-2.5 py-1 bg-brand text-white border border-brand/50 hover:bg-brand/80 rounded-md text-[10px] font-bold transition-all shadow-md shadow-brand/20 disabled:opacity-50"
              >
                <Zap className="w-3 h-3" />
                {insightLoading ? 'Analyzing...' : 'Analyze'}
              </button>
            </div>

            {/* AI Insights content area */}
            <div className="flex-1 py-4 overflow-y-auto min-h-[220px]">
              {insightLoading ? (
                <div className="flex flex-col items-center justify-center h-full gap-3 text-textSub text-xs">
                  <RefreshCw className="w-6 h-6 text-brand animate-spin" />
                  <span>AI Agent parsing telemetry...</span>
                </div>
              ) : parsedAi ? (
                /* Beautiful parsed layout cards */
                <div className="space-y-3">
                  {parsedAi.map((item) => {
                    let iconColor = 'text-brand'
                    let IconComponent = HelpCircle
                    let cardBorder = 'border-border/30'

                    if (item.title === 'Valuation') {
                      IconComponent = DollarSign
                      iconColor = 'text-cyan'
                    } else if (item.title === 'Momentum') {
                      IconComponent = Compass
                      iconColor = 'text-purple'
                    } else if (item.title === 'Risk') {
                      IconComponent = ShieldAlert
                      iconColor = 'text-danger'
                      cardBorder = 'border-danger/25 bg-danger/5'
                    } else if (item.title === 'Verdict') {
                      IconComponent = CheckCircle
                      iconColor = 'text-success'
                      cardBorder = 'border-success/25 bg-success/5'
                    }

                    return (
                      <div 
                        key={item.title} 
                        className={`p-3 rounded-lg border bg-elevated/40 backdrop-blur-sm transition-all hover:scale-[1.01] ${cardBorder}`}
                      >
                        <div className="flex items-center gap-2 mb-1">
                          <IconComponent className={`w-3.5 h-3.5 ${iconColor}`} />
                          <span className={`text-[11px] font-bold uppercase tracking-wider ${iconColor}`}>
                            {item.title}
                          </span>
                        </div>
                        <p className="text-xs text-textPrimary leading-relaxed">
                          {item.content}
                        </p>
                      </div>
                    )
                  })}
                </div>
              ) : (
                /* Raw fallback layout */
                <div className="text-xs text-textPrimary leading-relaxed whitespace-pre-line font-mono bg-elevated/20 p-3 rounded-lg border border-border/30">
                  {insight?.ai_summary || 'No AI insights have been compiled for this stock yet. Click analyze to trigger.'}
                </div>
              )}
            </div>

            {/* AI Disclaimer */}
            <div className="text-[9px] text-textMuted border-t border-border/40 pt-3 flex items-start gap-1 font-mono uppercase">
              <span className="text-warn font-bold">⚠️ Notice:</span>
              <span>Educational snapshot only. No investment advice.</span>
            </div>
          </div>

          {/* Factor metrics panel */}
          <div className="glass border border-border/60 bg-card/40 rounded-xl p-5 shadow-lg space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b border-border/40">
              <Target className="w-4 h-4 text-brand" />
              <span className="text-xs font-bold text-textPrimary uppercase tracking-widest font-display">
                Factor Strengths
              </span>
            </div>
            
            <div className="space-y-4.5">
              {[
                { name: 'Momentum', val: fundamentals?.factor_scores?.momentum ?? 50 },
                { name: 'Quality', val: fundamentals?.factor_scores?.quality ?? 50 },
                { name: 'Value', val: fundamentals?.factor_scores?.value ?? 50 },
                { name: 'Growth', val: fundamentals?.factor_scores?.growth ?? 50 },
                { name: 'Low Volatility', val: fundamentals?.factor_scores?.low_volatility ?? 50 },
              ].map((f) => (
                <div key={f.name} className="space-y-1.5 group">
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-textSub font-medium group-hover:text-textPrimary transition-colors">
                      {f.name}
                    </span>
                    <span 
                      className="font-mono font-bold text-xs" 
                      style={{ color: scoreColor(f.val) }}
                    >
                      {f.val}/100
                    </span>
                  </div>
                  {/* Progress track */}
                  <div className="h-2 bg-elevated rounded-full overflow-hidden border border-border/40 p-0.5">
                    <div 
                      className="h-full rounded-full transition-all duration-1000 bg-gradient-to-r" 
                      style={{ 
                        width: `${f.val}%`,
                        backgroundImage: `linear-gradient(90deg, #f43f5e, ${scoreColor(f.val)})`
                      }} 
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </PageShell>
  )
}
