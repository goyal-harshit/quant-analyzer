'use client'

import { useState, useEffect } from 'react'
import { TrendingUp, Activity, Shield, Database, Plus, Trash2, RefreshCw } from 'lucide-react'
import { AreaChart, Area, PieChart, Pie, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { T, fI, pct } from '@/lib/stockData'
import { usePortfolios, usePortfolio, useAddPosition, useCreatePortfolio, useRemovePosition, usePortfolioPerformance } from '@/lib/hooks'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from 'react-hot-toast'

const card = (x = {}) => ({ background: T.card, border: `1px solid ${T.b}`, borderRadius: 10, ...x })
const sc = v => v >= 70 ? T.green : v >= 45 ? T.amber : T.red

function Badge({ v }) {
  const c = sc(v)
  return <span style={{ background: `${c}22`, color: c, border: `1px solid ${c}44`, borderRadius: 4, padding: '2px 9px', fontSize: 12, fontFamily: T.mono, fontWeight: 700 }}>{v}</span>
}

function Tag({ children, color = '#a78bfa' }) {
  return <span style={{ background: `${color}22`, color, border: `1px solid ${color}44`, borderRadius: 4, padding: '2px 7px', fontSize: 10, fontWeight: 700 }}>{children}</span>
}

function Stat({ label, value, sub, color, icon: Icon }: { label: any; value: any; sub?: any; color?: any; icon?: any }) {
  return (
    <div style={card({ padding: '15px 18px' })}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <span style={{ fontSize: 10, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.07em' }}>{label}</span>
        {Icon && <Icon size={13} color={T.muted} />}
      </div>
      <div style={{ fontSize: 21, fontWeight: 700, fontFamily: T.mono, color: color || T.text }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: T.sub, marginTop: 3 }}>{sub}</div>}
    </div>
  )
}

function CT({ active, payload, label }: { active?: any; payload?: any; label?: any } = {}) {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: T.el, border: `1px solid ${T.b}`, borderRadius: 6, padding: '8px 12px', fontSize: 12 }}>
      <div style={{ color: T.muted, marginBottom: 4 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color || T.text, fontFamily: T.mono }}>
          {p.name}: {typeof p.value === 'number' ? p.value.toFixed(1) : p.value}%
        </div>
      ))}
    </div>
  )
}

export default function Portfolio() {
  const qc = useQueryClient()
  const { data: portfolios, isLoading: ploading } = usePortfolios()
  const [selId, setSelId] = useState<number | null>(null)
  const [refreshSeed, setRefreshSeed] = useState(0)
  const { data: portfolio, isLoading: p2loading } = usePortfolio(selId || 0, refreshSeed)
  const createPortfolio = useCreatePortfolio()
  const addPosition = useAddPosition()
  const removePosition = useRemovePosition()
  const [showAdd, setShowAdd] = useState(false)
  const [addTicker, setAddTicker] = useState('')
  const [addQty, setAddQty] = useState('')
  const [addCost, setAddCost] = useState('')

  useEffect(() => {
    if (portfolios && portfolios.length > 0 && !selId) {
      setSelId(portfolios[0].id)
    }
  }, [portfolios, selId])

  const creating = createPortfolio.isPending
  const adding = addPosition.isPending

  const handleCreate = async () => {
    try {
      const p = await createPortfolio.mutateAsync({ name: 'My Portfolio' })
      setSelId(p.id)
      toast.success('Portfolio created')
    } catch {
      toast.error('Failed to create portfolio')
    }
  }

  const handleAddPosition = async () => {
    if (!addTicker.trim() || !addQty || !addCost || !selId) return
    try {
      await addPosition.mutateAsync({
        id: selId,
        position: { ticker: addTicker.toUpperCase(), quantity: +addQty, avg_cost: +addCost }
      })
      setShowAdd(false)
      setAddTicker('')
      setAddQty('')
      setAddCost('')
      toast.success('Position added')
    } catch {
      toast.error('Failed to add position')
    }
  }

  const handleRemove = async (positionId: number) => {
    if (!selId) return
    try {
      await removePosition.mutateAsync({ portfolioId: selId, positionId })
      toast.success('Position removed')
    } catch {
      toast.error('Failed to remove position')
    }
  }

  if (ploading) {
    return (
      <div style={{ padding: '26px 30px', maxWidth: 1200, fontFamily: T.sans }}>
        <div style={{ color: T.sub, fontSize: 14 }}>Loading portfolios...</div>
      </div>
    )
  }

  if (portfolios && portfolios.length === 0) {
    return (
      <div style={{ padding: '26px 30px', maxWidth: 1200, fontFamily: T.sans }}>
        <div style={{ marginBottom: 22 }}>
          <div style={{ fontSize: 22, fontWeight: 700, color: T.text }}>Portfolio Analytics</div>
          <div style={{ fontSize: 13, color: T.sub, marginTop: 3 }}>India Equity Portfolio · NSE Listed</div>
        </div>
        <div style={card({ padding: '60px 20px', textAlign: 'center' })}>
          <div style={{ fontSize: 16, color: T.sub, marginBottom: 16 }}>No portfolio yet. Create one to start tracking your positions.</div>
          <button
            onClick={handleCreate}
            disabled={creating}
            style={{
              background: T.blue, color: '#fff', border: 'none', cursor: 'pointer',
              padding: '10px 24px', borderRadius: 8, fontSize: 14, fontWeight: 600,
              fontFamily: T.sans, opacity: creating ? 0.6 : 1,
            }}
          >
            {creating ? 'Creating...' : 'Create Portfolio'}
          </button>
        </div>
      </div>
    )
  }

  if (!portfolio) {
    return (
      <div style={{ padding: '26px 30px', maxWidth: 1200, fontFamily: T.sans }}>
        <div style={{ color: T.sub, fontSize: 14 }}>Loading portfolio data...</div>
      </div>
    )
  }

  const { data: perfData } = usePortfolioPerformance(selId || 0, 'NIFTY50', '1y', refreshSeed)
  const positions = portfolio.positions || []
  const totVal = portfolio.total_value || 0
  const totCst = portfolio.total_cost || 0
  const totPnl = portfolio.total_pnl || 0
  const COLS = [T.blue, T.green, T.amber, '#a78bfa', T.red]
  const pie = positions.map((p, i) => ({ name: p.ticker, v: p.current_value || 0, c: COLS[i % COLS.length] }))
  const portPts = perfData?.performance?.map((x: any) => ({ d: x.date, v: x.portfolio, b: x.benchmark })) || []

  return (
    <div style={{ padding: '26px 30px', maxWidth: 1200, fontFamily: T.sans }}>
      <div style={{ marginBottom: 22, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: 22, fontWeight: 700, color: T.text }}>Portfolio Analytics</div>
          <div style={{ fontSize: 13, color: T.sub, marginTop: 3 }}>{portfolio.name} · India Equity Portfolio</div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={() => setRefreshSeed(prev => prev + 1)}
            style={{
              background: T.el, border: `1px solid ${T.b}`, color: T.sub, cursor: 'pointer',
              padding: '9px 14px', borderRadius: 8, fontSize: 12, fontWeight: 600,
              fontFamily: T.sans, display: 'flex', alignItems: 'center', gap: 6,
            }}
          >
            <RefreshCw size={14} className={p2loading ? 'animate-spin' : ''} /> Refresh
          </button>
          <button
            onClick={() => setShowAdd(true)}
            style={{
              background: T.blue, color: '#fff', border: 'none', cursor: 'pointer',
              padding: '9px 18px', borderRadius: 8, fontSize: 12, fontWeight: 600,
              fontFamily: T.sans, display: 'flex', alignItems: 'center', gap: 6,
            }}
          >
            <Plus size={14} /> Add Position
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 18 }}>
        <Stat label="Portfolio Value" value={fI(totVal)} sub="Current market value" icon={Database} />
        <Stat
          label="Total P&L"
          value={(totPnl >= 0 ? '+' : '') + fI(totPnl)}
          sub={pct(portfolio.total_pnl_pct || 0)}
          color={totPnl >= 0 ? T.green : T.red}
          icon={TrendingUp}
        />
        <Stat label="Portfolio Beta" value={portfolio.beta ?? 'N/A'} sub="vs Nifty 50" icon={Activity} />
        <Stat label="Sharpe Ratio" value={portfolio.sharpe ?? 'N/A'} sub="12-month trailing" icon={Shield} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 14, marginBottom: 14 }}>
        <div style={card({ padding: '16px 18px' })}>
          <div style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 14 }}>Performance vs Benchmark (1Y)</div>
          <ResponsiveContainer width="100%" height={185}>
            <AreaChart data={portPts} margin={{ top: 4, right: 4, bottom: 0, left: 20 }}>
              <defs>
                <linearGradient id="pg" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={T.green} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={T.green} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="d" tick={{ fontSize: 10, fill: T.muted }} tickLine={false} axisLine={false} interval={portPts.length ? Math.max(1, Math.floor(portPts.length / 8)) : 15} />
              <YAxis
                tick={{ fontSize: 10, fill: T.muted, fontFamily: T.mono }}
                tickLine={false} axisLine={false} domain={['auto', 'auto']}
                tickFormatter={v => v.toFixed(0) + '%'}
              />
              <Tooltip content={<CT />} />
              <Area type="monotone" dataKey="v" stroke={T.green} strokeWidth={2} fill="url(#pg)" dot={false} name="Portfolio" />
              <Area type="monotone" dataKey="b" stroke={T.muted} strokeWidth={1.5} fill="none" dot={false} name="Benchmark (Nifty 50)" strokeDasharray="4 4" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div style={card({ padding: '16px 18px' })}>
          <div style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 8 }}>Allocation</div>
          {pie.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={150}>
                <PieChart>
                  <Pie cx="50%" cy="50%" innerRadius={42} outerRadius={65} dataKey="v" data={pie} paddingAngle={3}>
                    {pie.map((e, i) => <Cell key={i} fill={e.c} />)}
                  </Pie>
                  <Tooltip formatter={(v: any) => [fI(typeof v === 'number' ? v : 0), 'Value']} />
                </PieChart>
              </ResponsiveContainer>
              {pie.map((d, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 7, marginTop: 5 }}>
                  <div style={{ width: 8, height: 8, borderRadius: '50%', background: d.c, flexShrink: 0 }} />
                  <span style={{ fontSize: 11, fontFamily: T.mono, color: T.sub }}>{d.name}</span>
                  <span style={{ fontSize: 11, color: T.muted, marginLeft: 'auto' }}>{totVal > 0 ? (d.v / totVal * 100).toFixed(1) : '0.0'}%</span>
                </div>
              ))}
            </>
          ) : (
            <div style={{ color: T.muted, fontSize: 12, textAlign: 'center', padding: '40px 0' }}>No positions</div>
          )}
        </div>
      </div>

      <div style={card({ overflow: 'auto' })}>
        <div style={{ padding: '13px 18px', borderBottom: `1px solid ${T.b}`, fontSize: 13, fontWeight: 600, color: T.text }}>
          Positions · {positions.length}
        </div>
        {positions.length > 0 ? (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${T.b}` }}>
                {['Ticker', 'Sector', 'Qty', 'Avg Cost', 'LTP', 'Value', 'P&L', 'P&L%', 'Score', ''].map(h => (
                  <th
                    key={h}
                    style={{
                      padding: '9px 15px', fontSize: 10, color: T.muted,
                      textAlign: h === 'Ticker' || h === 'Sector' ? 'left' : 'right',
                      fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em',
                    }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {positions.map((p, i) => (
                <tr key={p.id} style={{ borderBottom: `1px solid ${T.b}`, background: i % 2 === 0 ? 'transparent' : `${T.el}55` }}>
                  <td style={{ padding: '11px 15px', fontFamily: T.mono, fontWeight: 700, fontSize: 12, color: T.text }}>{p.ticker}</td>
                  <td style={{ padding: '11px 15px' }}><Tag>{p.sector || 'N/A'}</Tag></td>
                  <td style={{ padding: '11px 15px', textAlign: 'right', fontFamily: T.mono, fontSize: 12, color: T.text }}>{p.quantity}</td>
                  <td style={{ padding: '11px 15px', textAlign: 'right', fontFamily: T.mono, fontSize: 12, color: T.sub }}>
                    ₹{p.avg_cost.toLocaleString('en-IN')}
                  </td>
                  <td style={{ padding: '11px 15px', textAlign: 'right', fontFamily: T.mono, fontSize: 12, color: T.text }}>
                    ₹{(p.current_price || 0).toLocaleString('en-IN')}
                  </td>
                  <td style={{ padding: '11px 15px', textAlign: 'right', fontFamily: T.mono, fontSize: 12, color: T.text }}>{fI(p.current_value || 0)}</td>
                  <td style={{ padding: '11px 15px', textAlign: 'right', fontFamily: T.mono, fontSize: 12, color: (p.pnl || 0) >= 0 ? T.green : T.red }}>
                    {(p.pnl || 0) >= 0 ? '+' : ''}{fI(p.pnl || 0)}
                  </td>
                  <td style={{ padding: '11px 15px', textAlign: 'right', fontFamily: T.mono, fontSize: 12, color: (p.pnl_pct || 0) >= 0 ? T.green : T.red }}>
                    {pct(p.pnl_pct || 0)}
                  </td>
                  <td style={{ padding: '11px 15px', textAlign: 'right' }}><Badge v={p.factor_score || 0} /></td>
                  <td style={{ padding: '11px 15px', textAlign: 'center' }}>
                    <button
                      onClick={() => handleRemove(p.id)}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', color: T.red, padding: 4 }}
                      title="Remove position"
                    >
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div style={{ padding: '40px 20px', textAlign: 'center', color: T.muted, fontSize: 13 }}>
            No positions. Click "Add Position" to start building your portfolio.
          </div>
        )}
        <div style={{ padding: '13px 18px', borderTop: `1px solid ${T.b}`, display: 'flex', gap: 32 }}>
          {[
            ['Beta', portfolio.beta?.toString() || 'N/A'],
            ['Volatility (Ann.)', portfolio.volatility ? `${portfolio.volatility}%` : 'N/A'],
            ['Sharpe Ratio', portfolio.sharpe?.toString() || 'N/A'],
            ['Max Drawdown', portfolio.max_drawdown ? `${portfolio.max_drawdown}%` : 'N/A'],
            ['Positions', positions.length.toString()],
          ].map(([l, v]) => (
            <div key={l}>
              <div style={{ fontSize: 10, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{l}</div>
              <div style={{ fontSize: 15, fontFamily: T.mono, fontWeight: 700, color: T.text, marginTop: 2 }}>{v}</div>
            </div>
          ))}
        </div>
      </div>

      {showAdd && (
        <div
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex',
            alignItems: 'center', justifyContent: 'center', zIndex: 1000,
          }}
          onClick={() => setShowAdd(false)}
        >
          <div
            style={card({ padding: '24px', width: 380, maxWidth: '90vw' })}
            onClick={e => e.stopPropagation()}
          >
            <div style={{ fontSize: 16, fontWeight: 700, color: T.text, marginBottom: 18 }}>Add Position</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div>
                <div style={{ fontSize: 10, color: T.muted, marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Ticker</div>
                <input
                  value={addTicker}
                  onChange={e => setAddTicker(e.target.value.toUpperCase())}
                  placeholder="e.g. RELIANCE"
                  style={{
                    width: '100%', padding: '8px 12px', background: T.el, border: `1px solid ${T.b}`,
                    borderRadius: 6, fontSize: 13, color: T.text, outline: 'none', fontFamily: T.mono,
                  }}
                />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <div style={{ fontSize: 10, color: T.muted, marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Quantity</div>
                  <input
                    type="number" min={1} value={addQty}
                    onChange={e => setAddQty(e.target.value)}
                    placeholder="10"
                    style={{
                      width: '100%', padding: '8px 12px', background: T.el, border: `1px solid ${T.b}`,
                      borderRadius: 6, fontSize: 13, color: T.text, outline: 'none', fontFamily: T.mono,
                    }}
                  />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: T.muted, marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Avg Cost (₹)</div>
                  <input
                  type="number" min={0} step={0.01} value={addCost}
                    onChange={e => setAddCost(e.target.value)}
                    placeholder="1000"
                    style={{
                      width: '100%', padding: '8px 12px', background: T.el, border: `1px solid ${T.b}`,
                      borderRadius: 6, fontSize: 13, color: T.text, outline: 'none', fontFamily: T.mono,
                    }}
                  />
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
              <button
                onClick={() => setShowAdd(false)}
                style={{
                  flex: 1, padding: '9px 0', background: 'none', border: `1px solid ${T.b}`,
                  borderRadius: 8, fontSize: 13, color: T.sub, cursor: 'pointer', fontFamily: T.sans,
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleAddPosition}
                disabled={adding || !addTicker || !addQty || !addCost}
                style={{
                  flex: 1, padding: '9px 0', background: T.blue, color: '#fff', border: 'none',
                  borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer', fontFamily: T.sans,
                  opacity: adding || !addTicker || !addQty || !addCost ? 0.6 : 1,
                }}
              >
                {adding ? 'Adding...' : 'Add'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
