'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { RefreshCw, Play } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import toast from 'react-hot-toast'
import { T } from '@/lib/stockData'
import { backtestApi } from '@/lib/api'

const card = (x = {}) => ({ background: T.card, border: `1px solid ${T.b}`, borderRadius: 10, ...x })

function CT({ active, payload, label }: { active?: any; payload?: any; label?: any } = {}) {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: T.el, border: `1px solid ${T.b}`, borderRadius: 6, padding: '8px 12px', fontSize: 12 }}>
      <div style={{ color: T.muted, marginBottom: 4 }}>{label}</div>
      {payload.map((p: any, i: number) => (
        <div key={i} style={{ color: p.color || T.text, fontFamily: T.mono }}>
          <span style={{ color: T.sub }}>{p.name}: </span>
          {typeof p.value === 'number' ? p.value.toFixed(1) : p.value}
        </div>
      ))}
    </div>
  )
}

export default function Backtester() {
  const router = useRouter()
  const [strategy, setStrategy] = useState('Composite Multi-Factor')
  const [rebalFreq, setRebalFreq] = useState('monthly')
  const [topN, setTopN] = useState(15)
  const [txCost, setTxCost] = useState(0.001) // 0.1%
  const [isLoading, setIsLoading] = useState(false)
  const [backtestResult, setBacktestResult] = useState<any>(null)

  const strategies = [
    {
      name: 'High Momentum',
      desc: 'Top-decile 12-1 month price momentum. Equal-weight. Nifty 500 constituents.',
      weights: { momentum: 1.0 },
      defaultFreq: 'quarterly'
    },
    {
      name: 'Quality Value',
      desc: 'Top Quality (ROE, low debt) + Value (EV/EBITDA, PB) intersection.',
      weights: { quality: 0.5, value: 0.5 },
      defaultFreq: 'semi-annual'
    },
    {
      name: 'Composite Multi-Factor',
      desc: 'Balanced combination of Momentum (25%), Quality (25%), Value (20%), Growth (20%), and Low Vol (10%).',
      weights: { momentum: 0.25, quality: 0.25, value: 0.20, growth: 0.20, low_volatility: 0.10 },
      defaultFreq: 'monthly'
    },
    {
      name: 'Low Volatility Defensive',
      desc: 'Defensive tilt focusing on bottom-volatility stock ranking.',
      weights: { low_volatility: 1.0 },
      defaultFreq: 'quarterly'
    }
  ]

  const activeStrategy = strategies.find(s => s.name === strategy) || strategies[2]

  const runBacktest = async () => {
    setIsLoading(true)
    try {
      const res = await backtestApi.run({
        strategy_name: strategy,
        universe: 'NIFTY500',
        start_date: '2024-01-01',
        end_date: '2026-06-01',
        rebalance_freq: rebalFreq,
        top_n: topN,
        factor_weights: activeStrategy.weights,
        transaction_cost: txCost,
        benchmark: 'NIFTY50'
      })
      setBacktestResult(res)
    } catch {
      toast.error('Backtest failed — the backend server is unreachable. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  // Re-run automatically when the strategy changes; other parameters apply on "Run Backtest".
  useEffect(() => {
    runBacktest()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [strategy])

  const metrics = backtestResult?.metrics || {
    total_return: 0,
    annualised_return: 0,
    benchmark_return: 0,
    sharpe_ratio: 0,
    max_drawdown: 0,
    win_rate: 0
  }

  const chartData = (backtestResult?.equity_curve || []).map((pt: any) => ({
    date: pt.date,
    'Strategy Portfolio': pt.portfolio_value,
    'Nifty 50': pt.benchmark_value
  }))

  return (
    <div style={{ padding: '26px 30px', maxWidth: 1100, fontFamily: T.sans }}>
      <div style={{ marginBottom: 22, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: 22, fontWeight: 700, color: T.text }}>Strategy Backtester</div>
          <div style={{ fontSize: 13, color: T.sub, marginTop: 3 }}>
            Factor-based historical strategy simulations · Nifty 500 constituents
          </div>
        </div>
        <button
          onClick={runBacktest}
          disabled={isLoading}
          style={{
            marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6,
            padding: '8px 16px', background: T.blue, border: 'none',
            borderRadius: 6, fontSize: 13, color: '#fff', fontWeight: 600, cursor: 'pointer'
          }}
        >
          {isLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-white" />}
          Run Backtest
        </button>
      </div>

      {/* Select strategy row */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 18, overflowX: 'auto' }}>
        {strategies.map(s => (
          <button
            key={s.name}
            onClick={() => {
              setStrategy(s.name)
              setRebalFreq(s.defaultFreq)
            }}
            style={{
              padding: '8px 18px', borderRadius: 8, border: `1px solid ${strategy === s.name ? T.blue : T.b}`,
              background: strategy === s.name ? `${T.blue}22` : 'transparent', color: strategy === s.name ? T.blue : T.sub,
              fontSize: 13, fontWeight: strategy === s.name ? 600 : 400, cursor: 'pointer', whiteSpace: 'nowrap'
            }}
          >
            {s.name}
          </button>
        ))}
      </div>

      {/* Strategy options panel */}
      <div style={card({ padding: '14px 18px', marginBottom: 18 })}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
          <div>
            <div style={{ fontSize: 10, color: T.muted, marginBottom: 4 }}>REBALANCE FREQUENCY</div>
            <select
              value={rebalFreq}
              onChange={e => setRebalFreq(e.target.value)}
              style={{
                width: '100%', background: T.el, border: `1px solid ${T.b}`, borderRadius: 6,
                padding: '6px 10px', fontSize: 12, color: T.text, cursor: 'pointer',
              }}
            >
              <option value="monthly">Monthly</option>
              <option value="quarterly">Quarterly</option>
              <option value="semi-annual">Semi-Annual</option>
              <option value="annual">Annual</option>
            </select>
          </div>

          <div>
            <div style={{ fontSize: 10, color: T.muted, marginBottom: 4 }}>CONSTITUENT COUNT (TOP N)</div>
            <select
              value={topN}
              onChange={e => setTopN(Number(e.target.value))}
              style={{
                width: '100%', background: T.el, border: `1px solid ${T.b}`, borderRadius: 6,
                padding: '6px 10px', fontSize: 12, color: T.text, cursor: 'pointer',
              }}
            >
              <option value="5">Hold Top 5</option>
              <option value="10">Hold Top 10</option>
              <option value="15">Hold Top 15</option>
              <option value="20">Hold Top 20</option>
              <option value="30">Hold Top 30</option>
            </select>
          </div>

          <div>
            <div style={{ fontSize: 10, color: T.muted, marginBottom: 4 }}>TRANSACTION SLIPPAGE (ONE-WAY)</div>
            <select
              value={txCost}
              onChange={e => setTxCost(Number(e.target.value))}
              style={{
                width: '100%', background: T.el, border: `1px solid ${T.b}`, borderRadius: 6,
                padding: '6px 10px', fontSize: 12, color: T.text, cursor: 'pointer',
              }}
            >
              <option value="0">0.00% (No slippage)</option>
              <option value="0.0005">0.05% (Institutional)</option>
              <option value="0.001">0.10% (Standard Retail)</option>
              <option value="0.002">0.20% (High turnover)</option>
            </select>
          </div>
        </div>
        <div style={{ fontSize: 11, color: T.sub, marginTop: 10, borderTop: `1px solid ${T.b}`, paddingTop: 8 }}>
          <strong>Strategy description:</strong> {activeStrategy.desc}
        </div>
      </div>

      {/* Metrics Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 18 }}>
        {[
          ['Total Return', `${metrics.total_return >= 0 ? '+' : ''}${metrics.total_return.toFixed(1)}%`, T.green, `vs ${metrics.benchmark_return >= 0 ? '+' : ''}${metrics.benchmark_return.toFixed(1)}% Nifty`],
          ['CAGR', `${metrics.annualised_return.toFixed(1)}%`, T.blue, 'Strategy annualised rate'],
          ['Sharpe Ratio', metrics.sharpe_ratio.toFixed(2), T.amber, 'Risk-adjusted ratio'],
          ['Max Drawdown', `-${Math.abs(metrics.max_drawdown).toFixed(1)}%`, T.red, 'Max peak-to-trough fall'],
        ].map(([l, v, c, sub]) => (
          <div key={l} style={card({ padding: '13px 16px' })}>
            <div style={{ fontSize: 10, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 5 }}>{l}</div>
            <div style={{ fontSize: 21, fontWeight: 700, fontFamily: T.mono, color: c }}>{v}</div>
            <div style={{ fontSize: 10, color: T.muted, marginTop: 3 }}>{sub}</div>
          </div>
        ))}
      </div>

      {/* Chart container */}
      <div style={card({ padding: '16px 18px', marginBottom: 14 })}>
        <div style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
          <span>Portfolio Growth (Base 100) vs Benchmark</span>
          {isLoading && <RefreshCw className="w-4 h-4 text-brand animate-spin" />}
        </div>
        <ResponsiveContainer width="100%" height={270}>
          {isLoading && chartData.length === 0 ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
              <RefreshCw className="w-8 h-8 text-brand animate-spin" />
            </div>
          ) : chartData.length === 0 ? (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', fontSize: 13, color: T.sub, textAlign: 'center', padding: '0 20px' }}>
              No backtest results yet — the backend may be unreachable. Click &ldquo;Run Backtest&rdquo; to retry.
            </div>
          ) : (
            <LineChart data={chartData} margin={{ top: 4, right: 16, bottom: 0, left: 40 }}>
              <CartesianGrid stroke={T.b} strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fontSize: 9, fill: T.muted }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 10, fill: T.muted, fontFamily: T.mono }} tickLine={false} axisLine={false} domain={['auto', 'auto']} tickFormatter={v => v.toFixed(0)} />
              <Tooltip content={<CT />} />
              <Legend wrapperStyle={{ fontSize: 11, color: T.sub }} />
              <Line type="monotone" dataKey="Strategy Portfolio" stroke={T.blue} strokeWidth={2.5} dot={false} />
              <Line type="monotone" dataKey="Nifty 50" stroke={T.muted} strokeWidth={1.5} dot={false} />
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>

      {/* Holds/Turnover info */}
      {backtestResult && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
          <div style={card({ padding: '14px 18px' })}>
            <div style={{ fontSize: 12, fontWeight: 600, color: T.text, marginBottom: 10 }}>Current Holding Constituents (Top 10)</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {(backtestResult.top_holdings_last || []).map((h: any) => (
                <span
                  key={h.ticker}
                  onClick={() => router.push(`/stocks/${h.ticker}`)}
                  style={{
                    background: T.el, border: `1px solid ${T.b}`, borderRadius: 4,
                    padding: '4px 8px', fontSize: 11, fontFamily: T.mono, fontWeight: 600, color: T.blue, cursor: 'pointer'
                  }}
                >
                  {h.ticker}
                </span>
              ))}
            </div>
          </div>
          <div style={card({ padding: '14px 18px', display: 'flex', flexDirection: 'column', justifyContent: 'center' })}>
            <div style={{ fontSize: 12, fontWeight: 600, color: T.text, marginBottom: 4 }}>Portfolio Turnover Rate</div>
            <div style={{ fontSize: 24, fontWeight: 700, fontFamily: T.mono, color: T.text }}>
              {backtestResult.turnover_avg?.toFixed(1)}%
            </div>
            <div style={{ fontSize: 11, color: T.sub, marginTop: 4 }}>
              Average proportion of assets replaced during each rebalancing session
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
