// /frontend/components/stocks/FundamentalsPanel.tsx
import Card from '../ui/Card'
import { Fundamentals } from '@/lib/api'

interface FundamentalsPanelProps {
  data: Fundamentals | null | undefined
}

export default function FundamentalsPanel({ data }: FundamentalsPanelProps) {
  if (!data) {
    return (
      <Card padding="md">
        <div className="text-center text-textMuted py-8">No fundamentals data available.</div>
      </Card>
    )
  }

  // Format functions
  const formatVal = (val: number | null | undefined, suffix = '', decimals = 2) => {
    if (val === null || val === undefined) return 'N/A'
    return `${val.toFixed(decimals)}${suffix}`
  }

  const formatAmount = (val: number | null | undefined) => {
    if (val === null || val === undefined) return 'N/A'
    if (val >= 10000000) return `₹${(val / 10000000).toFixed(2)} Cr`
    if (val >= 100000) return `₹${(val / 100000).toFixed(2)} L`
    return `₹${val.toLocaleString('en-IN')}`
  }

  // Ratios evaluation alerts
  const peColor = (pe: number | null | undefined) => {
    if (!pe) return 'text-textPrimary'
    if (pe < 20) return 'text-success'
    if (pe < 45) return 'text-warn'
    return 'text-danger'
  }

  const roeColor = (roe: number | null | undefined) => {
    if (!roe) return 'text-textPrimary'
    if (roe > 18) return 'text-success'
    if (roe > 10) return 'text-warn'
    return 'text-danger'
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {/* Valuation Card */}
      <Card padding="md">
        <Card.Header title="Valuation Metrics" subtitle="Multiples and corporate pricing ratios" />
        <div className="space-y-3.5">
          <div className="flex justify-between items-center py-2 border-b border-border/50">
            <span className="text-textSub">P/E Ratio</span>
            <span className={`font-mono font-semibold ${peColor(data.pe_ratio)}`}>
              {formatVal(data.pe_ratio, 'x', 1)}
            </span>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-border/50">
            <span className="text-textSub">P/B Ratio</span>
            <span className="font-mono font-semibold text-textPrimary">
              {formatVal(data.pb_ratio, 'x', 1)}
            </span>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-border/50">
            <span className="text-textSub">EV / EBITDA</span>
            <span className="font-mono font-semibold text-textPrimary">
              {formatVal(data.ev_ebitda, 'x', 1)}
            </span>
          </div>
          <div className="flex justify-between items-center py-2">
            <span className="text-textSub">P/S Ratio</span>
            <span className="font-mono font-semibold text-textPrimary">
              {formatVal(data.ps_ratio, 'x', 1)}
            </span>
          </div>
        </div>
      </Card>

      {/* Profitability Card */}
      <Card padding="md">
        <Card.Header title="Profitability" subtitle="Capital efficiency and margin ratios" />
        <div className="space-y-3.5">
          <div className="flex justify-between items-center py-2 border-b border-border/50">
            <span className="text-textSub">Return on Equity (ROE)</span>
            <span className={`font-mono font-semibold ${roeColor(data.roe)}`}>
              {formatVal(data.roe, '%', 1)}
            </span>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-border/50">
            <span className="text-textSub">Return on Capital (ROCE)</span>
            <span className="font-mono font-semibold text-textPrimary">
              {formatVal(data.roce, '%', 1)}
            </span>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-border/50">
            <span className="text-textSub">Net Margin</span>
            <span className="font-mono font-semibold text-textPrimary">
              {formatVal(data.net_margin, '%', 1)}
            </span>
          </div>
          <div className="flex justify-between items-center py-2">
            <span className="text-textSub">Revenue Growth (YoY)</span>
            <span className="font-mono font-semibold text-textPrimary">
              {formatVal(data.revenue_growth, '%', 1)}
            </span>
          </div>
        </div>
      </Card>

      {/* Solvency and Solvency health */}
      <Card padding="md">
        <Card.Header title="Financial Health" subtitle="Balance sheet solvency & leverage" />
        <div className="space-y-3.5">
          <div className="flex justify-between items-center py-2 border-b border-border/50">
            <span className="text-textSub">Debt / Equity</span>
            <span className="font-mono font-semibold text-textPrimary">
              {formatVal(data.debt_equity, '', 2)}
            </span>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-border/50">
            <span className="text-textSub">Current Ratio</span>
            <span className="font-mono font-semibold text-textPrimary">
              {formatVal(data.current_ratio, '', 2)}
            </span>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-border/50">
            <span className="text-textSub">Market Capitalization</span>
            <span className="font-mono font-semibold text-brand">
              {formatAmount(data.market_cap)}
            </span>
          </div>
          <div className="flex justify-between items-center py-2">
            <span className="text-textSub">Dividend Yield</span>
            <span className="font-mono font-semibold text-textPrimary">
              {formatVal(data.dividend_yield, '%', 2)}
            </span>
          </div>
        </div>
      </Card>
    </div>
  )
}
