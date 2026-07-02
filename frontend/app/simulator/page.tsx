'use client'

import { useEffect, useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid,
} from 'recharts'
import {
  TrendingUp, TrendingDown, Plus, Trash2, Wallet, Activity, RefreshCw, LineChart,
} from 'lucide-react'
import PageShell from '@/components/layout/PageShell'
import Card from '@/components/ui/Card'
import { simulatorApi, type SimPortfolioRef } from '@/lib/api'

const LS_KEY = 'sim_portfolios'
const LS_SELECTED = 'sim_selected'

const inr = (n: number | null | undefined, dp = 0) =>
  '₹' + (n ?? 0).toLocaleString('en-IN', { minimumFractionDigits: dp, maximumFractionDigits: dp })

const pct = (n: number | null | undefined) => `${(n ?? 0) >= 0 ? '+' : ''}${(n ?? 0).toFixed(2)}%`

function loadLocal(): SimPortfolioRef[] {
  if (typeof window === 'undefined') return []
  try { return JSON.parse(localStorage.getItem(LS_KEY) || '[]') } catch { return [] }
}
function saveLocal(list: SimPortfolioRef[]) {
  if (typeof window !== 'undefined') localStorage.setItem(LS_KEY, JSON.stringify(list))
}

export default function SimulatorPage() {
  const qc = useQueryClient()
  const [local, setLocal] = useState<SimPortfolioRef[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [newCapital, setNewCapital] = useState(100000)

  // Trade form
  const [ticker, setTicker] = useState('')
  const [qty, setQty] = useState<number>(1)
  const [tradeMsg, setTradeMsg] = useState<{ ok: boolean; text: string } | null>(null)

  // Hydrate the portfolio list: localStorage (guests) + server (logged-in), merged by id.
  useEffect(() => {
    const ls = loadLocal()
    setLocal(ls)
    const sel = Number(localStorage.getItem(LS_SELECTED) || '')
    if (sel && ls.some((p) => p.id === sel)) setSelectedId(sel)
    else if (ls.length) setSelectedId(ls[0].id)

    simulatorApi.listPortfolios().then((server) => {
      if (!server?.length) return
      const merged = [...server]
      for (const p of ls) if (!merged.some((m) => m.id === p.id)) merged.push(p)
      setLocal(merged); saveLocal(merged)
      setSelectedId((cur) => cur ?? merged[0]?.id ?? null)
    }).catch(() => {})
  }, [])

  useEffect(() => {
    if (selectedId) localStorage.setItem(LS_SELECTED, String(selectedId))
  }, [selectedId])

  const stateQ = useQuery({
    queryKey: ['sim', 'state', selectedId],
    queryFn: () => simulatorApi.getPortfolio(selectedId as number),
    enabled: !!selectedId,
    refetchInterval: 30000,
  })
  const perfQ = useQuery({
    queryKey: ['sim', 'perf', selectedId],
    queryFn: () => simulatorApi.getPerformance(selectedId as number),
    enabled: !!selectedId,
  })
  const tradesQ = useQuery({
    queryKey: ['sim', 'trades', selectedId],
    queryFn: () => simulatorApi.getTrades(selectedId as number),
    enabled: !!selectedId,
  })

  const invalidateAll = () => {
    qc.invalidateQueries({ queryKey: ['sim', 'state', selectedId] })
    qc.invalidateQueries({ queryKey: ['sim', 'perf', selectedId] })
    qc.invalidateQueries({ queryKey: ['sim', 'trades', selectedId] })
  }

  const createMut = useMutation({
    mutationFn: () => simulatorApi.createPortfolio({ name: newName.trim() || 'My Portfolio', starting_capital: newCapital }),
    onSuccess: (p) => {
      const next = [...local, p]; setLocal(next); saveLocal(next)
      setSelectedId(p.id); setShowCreate(false); setNewName('')
    },
  })

  const tradeMut = useMutation({
    mutationFn: (side: 'BUY' | 'SELL') =>
      simulatorApi.trade(selectedId as number, { ticker: ticker.trim().toUpperCase(), side, quantity: qty }),
    onSuccess: (tx, side) => {
      setTradeMsg({ ok: true, text: `${side} ${tx.quantity} ${tx.ticker} @ ${inr(tx.price, 2)} (fees ${inr(tx.fees, 2)})` })
      invalidateAll()
    },
    onError: (err: any) => {
      setTradeMsg({ ok: false, text: err?.response?.data?.detail || 'Trade failed' })
    },
  })

  const deleteMut = useMutation({
    mutationFn: (id: number) => simulatorApi.delete(id),
    onSuccess: (_, id) => {
      const next = local.filter((p) => p.id !== id); setLocal(next); saveLocal(next)
      setSelectedId(next[0]?.id ?? null)
    },
  })

  const state = stateQ.data
  const perf = perfQ.data
  const totalUp = (state?.total_pnl ?? 0) >= 0

  const chartData = useMemo(
    () => (perf?.equity_curve ?? []).map((e) => ({ date: e.date, value: e.value })),
    [perf]
  )

  // ── Empty state: no portfolio yet ──
  if (!selectedId) {
    return (
      <PageShell title="Trading Simulator" subtitle="Practice with virtual capital at live NSE/BSE prices — no real money">
        <Card padding="lg" className="max-w-lg mx-auto text-center">
          <LineChart className="w-10 h-10 text-brand mx-auto mb-3" />
          <div className="text-lg font-semibold text-textPrimary mb-1">Start paper trading</div>
          <p className="text-sm text-textSub mb-5">
            Create a virtual portfolio, buy and sell real stocks at live prices, and track your P&amp;L and performance.
          </p>
          <CreateForm
            show name={newName} setName={setNewName} capital={newCapital} setCapital={setNewCapital}
            onCreate={() => createMut.mutate()} pending={createMut.isPending}
          />
        </Card>
      </PageShell>
    )
  }

  return (
    <PageShell
      title="Trading Simulator"
      subtitle="Practice with virtual capital at live NSE/BSE prices"
      actions={
        <div className="flex items-center gap-2">
          <select
            value={selectedId}
            onChange={(e) => setSelectedId(Number(e.target.value))}
            className="bg-elevated border border-border rounded-lg text-xs font-semibold text-textPrimary px-2.5 py-1.5"
          >
            {local.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <button
            onClick={() => setShowCreate((s) => !s)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-brand/10 border border-brand/20 rounded-lg text-xs font-semibold text-brand hover:bg-brand/20 transition-all"
          >
            <Plus className="w-3.5 h-3.5" /> New
          </button>
          <button
            onClick={() => { invalidateAll(); }}
            className="p-1.5 bg-elevated border border-border rounded-lg text-textSub hover:text-textPrimary transition-all"
            title="Refresh prices"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      }
    >
      {showCreate && (
        <Card padding="md" className="max-w-lg">
          <CreateForm
            show name={newName} setName={setNewName} capital={newCapital} setCapital={setNewCapital}
            onCreate={() => createMut.mutate()} pending={createMut.isPending}
          />
        </Card>
      )}

      {/* Metrics row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricTile label="Total Value" value={inr(state?.total_value)} sub={`Cash ${inr(state?.cash)}`} icon={Wallet} />
        <MetricTile
          label="Total P&L"
          value={inr(state?.total_pnl)}
          sub={pct(state?.total_pnl_pct)}
          tone={totalUp ? 'pos' : 'neg'}
          icon={totalUp ? TrendingUp : TrendingDown}
        />
        <MetricTile label="Invested" value={inr(state?.invested)} sub={`${state?.holdings_count ?? 0} holdings`} icon={Activity} />
        <MetricTile
          label="Realized P&L"
          value={inr(state?.realized_pnl)}
          sub={`Unrealized ${inr(state?.unrealized_pnl)}`}
          tone={(state?.realized_pnl ?? 0) >= 0 ? 'pos' : 'neg'}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* LEFT: trade panel + holdings */}
        <div className="lg:col-span-2 space-y-6">
          {/* Trade panel */}
          <Card padding="md">
            <Card.Header title="Place Order" subtitle="Executes at the live market price" />
            <div className="flex flex-wrap items-end gap-3">
              <div className="flex-1 min-w-[140px]">
                <label className="metric-label">Ticker</label>
                <input
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value.toUpperCase())}
                  placeholder="e.g. RELIANCE"
                  className="w-full mt-1 bg-elevated border border-border rounded-lg px-3 py-2 text-sm font-mono text-textPrimary focus:border-brand outline-none"
                />
              </div>
              <div className="w-28">
                <label className="metric-label">Quantity</label>
                <input
                  type="number" min={1} value={qty}
                  onChange={(e) => setQty(Math.max(1, Number(e.target.value)))}
                  className="w-full mt-1 bg-elevated border border-border rounded-lg px-3 py-2 text-sm font-mono text-textPrimary focus:border-brand outline-none"
                />
              </div>
              <button
                onClick={() => tradeMut.mutate('BUY')}
                disabled={!ticker || tradeMut.isPending}
                className="px-5 py-2 bg-success/15 text-success border border-success/30 rounded-lg text-sm font-bold hover:bg-success/25 disabled:opacity-40 transition-all"
              >
                Buy
              </button>
              <button
                onClick={() => tradeMut.mutate('SELL')}
                disabled={!ticker || tradeMut.isPending}
                className="px-5 py-2 bg-danger/15 text-danger border border-danger/30 rounded-lg text-sm font-bold hover:bg-danger/25 disabled:opacity-40 transition-all"
              >
                Sell
              </button>
            </div>
            {tradeMsg && (
              <div className={`mt-3 text-xs font-medium px-3 py-2 rounded-lg ${tradeMsg.ok ? 'bg-success/10 text-success' : 'bg-danger/10 text-danger'}`}>
                {tradeMsg.text}
              </div>
            )}
          </Card>

          {/* Holdings */}
          <Card padding="md">
            <Card.Header title="Holdings" subtitle="Marked to live prices" icon={Wallet} />
            {(state?.holdings?.length ?? 0) === 0 ? (
              <div className="text-sm text-textMuted py-8 text-center">No open positions. Place a buy order to get started.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-border/50 text-textMuted text-xs font-semibold uppercase">
                      <th className="py-2.5">Stock</th>
                      <th className="py-2.5 text-right">Qty</th>
                      <th className="py-2.5 text-right">Avg Cost</th>
                      <th className="py-2.5 text-right">LTP</th>
                      <th className="py-2.5 text-right">Value</th>
                      <th className="py-2.5 text-right">Unreal. P&L</th>
                      <th className="py-2.5 text-right">Wt</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/30">
                    {state!.holdings.map((h) => {
                      const up = h.unrealized_pnl >= 0
                      return (
                        <tr key={h.ticker} className="hover:bg-elevated/40 transition-colors">
                          <td className="py-3">
                            <div className="font-mono font-bold text-brand text-sm">{h.ticker}</div>
                            <div className="text-[11px] text-textMuted truncate max-w-[140px]">{h.name}</div>
                          </td>
                          <td className="py-3 text-right font-mono text-textPrimary">{h.quantity}</td>
                          <td className="py-3 text-right font-mono text-textSub">{inr(h.avg_cost, 2)}</td>
                          <td className="py-3 text-right font-mono text-textPrimary">{inr(h.current_price, 2)}</td>
                          <td className="py-3 text-right font-mono text-textPrimary">{inr(h.market_value)}</td>
                          <td className={`py-3 text-right font-mono font-semibold ${up ? 'text-success' : 'text-danger'}`}>
                            {inr(h.unrealized_pnl)}<span className="text-[11px] ml-1">({pct(h.unrealized_pnl_pct)})</span>
                          </td>
                          <td className="py-3 text-right font-mono text-textMuted text-xs">{h.weight_pct}%</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>

        {/* RIGHT: performance + journal */}
        <div className="space-y-6">
          <Card padding="md">
            <Card.Header title="Performance" subtitle="Equity curve & risk stats" icon={Activity} />
            {chartData.length >= 2 ? (
              <div className="h-44 -ml-2">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData}>
                    <defs>
                      <linearGradient id="eq" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#6366f1" stopOpacity={0.35} />
                        <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" vertical={false} />
                    <XAxis dataKey="date" hide />
                    <YAxis domain={['auto', 'auto']} hide />
                    <Tooltip
                      contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, fontSize: 12 }}
                      labelStyle={{ color: '#cbd5e1' }}
                      formatter={(v: any) => [inr(v), 'Value']}
                    />
                    <Area type="monotone" dataKey="value" stroke="#6366f1" strokeWidth={2} fill="url(#eq)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="text-xs text-textMuted py-6 text-center">
                Equity curve builds as trading days pass.
              </div>
            )}
            <div className="grid grid-cols-2 gap-x-4 gap-y-2.5 mt-4 text-sm">
              <Stat label="Total Return" value={pct(perf?.total_return_pct)} tone={(perf?.total_return_pct ?? 0) >= 0 ? 'pos' : 'neg'} />
              <Stat label="Win Rate" value={`${((perf?.win_rate ?? 0) * 100).toFixed(0)}%`} />
              <Stat label="Closed Trades" value={String(perf?.sells_closed ?? 0)} />
              <Stat label="Max Drawdown" value={pct(perf?.max_drawdown_pct)} tone="neg" />
              <Stat label="Sharpe" value={(perf?.sharpe_ratio ?? 0).toFixed(2)} />
              <Stat label="Best / Worst" value={`${inr(perf?.best_trade)} / ${inr(perf?.worst_trade)}`} />
            </div>
          </Card>

          {/* Trade journal */}
          <Card padding="md">
            <Card.Header
              title="Trade Journal"
              right={
                <button
                  onClick={() => deleteMut.mutate(selectedId)}
                  className="flex items-center gap-1 text-[11px] text-danger hover:text-danger/80"
                  title="Delete this portfolio"
                >
                  <Trash2 className="w-3 h-3" /> Delete
                </button>
              }
            />
            {(tradesQ.data?.length ?? 0) === 0 ? (
              <div className="text-sm text-textMuted py-6 text-center">No trades yet.</div>
            ) : (
              <div className="space-y-1 max-h-72 overflow-y-auto">
                {tradesQ.data!.map((t) => (
                  <div key={t.id} className="flex items-center justify-between py-2 px-2 border-b border-border/30 last:border-0 text-xs">
                    <div className="flex items-center gap-2">
                      <span className={`px-1.5 py-0.5 rounded font-bold ${t.side === 'BUY' ? 'bg-success/15 text-success' : 'bg-danger/15 text-danger'}`}>
                        {t.side}
                      </span>
                      <span className="font-mono font-semibold text-textPrimary">{t.quantity} {t.ticker}</span>
                    </div>
                    <div className="text-right">
                      <div className="font-mono text-textSub">{inr(t.price, 2)}</div>
                      {t.side === 'SELL' && (
                        <div className={`font-mono text-[11px] ${t.realized_pnl >= 0 ? 'text-success' : 'text-danger'}`}>
                          {inr(t.realized_pnl)}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </PageShell>
  )
}

// ── Small presentational helpers ─────────────────────────────────
function MetricTile({ label, value, sub, tone, icon: Icon }: {
  label: string; value: string; sub?: string; tone?: 'pos' | 'neg'; icon?: React.ElementType
}) {
  const toneCls = tone === 'pos' ? 'text-success' : tone === 'neg' ? 'text-danger' : 'text-textPrimary'
  return (
    <Card padding="sm">
      <div className="flex items-center justify-between">
        <div className="metric-label">{label}</div>
        {Icon && <Icon className={`w-3.5 h-3.5 ${tone === 'pos' ? 'text-success' : tone === 'neg' ? 'text-danger' : 'text-textMuted'}`} />}
      </div>
      <div className={`metric-value mt-1.5 text-xl font-mono ${toneCls}`}>{value}</div>
      {sub && <div className="text-[11px] text-textMuted mt-0.5 font-mono">{sub}</div>}
    </Card>
  )
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: 'pos' | 'neg' }) {
  const toneCls = tone === 'pos' ? 'text-success' : tone === 'neg' ? 'text-danger' : 'text-textPrimary'
  return (
    <div className="flex justify-between items-center">
      <span className="text-textMuted text-xs">{label}</span>
      <span className={`font-mono font-semibold ${toneCls}`}>{value}</span>
    </div>
  )
}

function CreateForm({ name, setName, capital, setCapital, onCreate, pending }: {
  show: boolean; name: string; setName: (s: string) => void
  capital: number; setCapital: (n: number) => void; onCreate: () => void; pending: boolean
}) {
  return (
    <div className="flex flex-wrap items-end gap-3">
      <div className="flex-1 min-w-[160px] text-left">
        <label className="metric-label">Portfolio name</label>
        <input
          value={name} onChange={(e) => setName(e.target.value)} placeholder="My Portfolio"
          className="w-full mt-1 bg-elevated border border-border rounded-lg px-3 py-2 text-sm text-textPrimary focus:border-brand outline-none"
        />
      </div>
      <div className="w-40 text-left">
        <label className="metric-label">Starting capital (₹)</label>
        <input
          type="number" min={1000} step={1000} value={capital}
          onChange={(e) => setCapital(Math.max(1000, Number(e.target.value)))}
          className="w-full mt-1 bg-elevated border border-border rounded-lg px-3 py-2 text-sm font-mono text-textPrimary focus:border-brand outline-none"
        />
      </div>
      <button
        onClick={onCreate} disabled={pending}
        className="px-5 py-2 bg-brand text-white rounded-lg text-sm font-bold hover:bg-brand/90 disabled:opacity-50 transition-all"
      >
        {pending ? 'Creating…' : 'Create'}
      </button>
    </div>
  )
}
