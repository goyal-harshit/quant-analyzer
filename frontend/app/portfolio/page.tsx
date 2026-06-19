'use client'

import { TrendingUp, Activity, Shield, Database } from 'lucide-react'
import { AreaChart, Area, PieChart, Pie, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { STOCKS, SEED_POSITIONS, T, fI, pct, genPrices } from '@/lib/stockData'

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
          {typeof p.value === 'number' ? p.value.toFixed(2) : p.value}
        </div>
      ))}
    </div>
  )
}

export default function Portfolio() {
  const positions = SEED_POSITIONS.map(pos => {
    const stk = STOCKS.find(s => s.ticker === pos.ticker)
    const cur = stk.price * pos.qty
    const cst = pos.cost * pos.qty
    return { ...pos, stk, cur, cst, pnl: cur - cst, pp: ((cur - cst) / cst) * 100 }
  })
  const totVal = positions.reduce((a, p) => a + p.cur, 0)
  const totCst = positions.reduce((a, p) => a + p.cst, 0)
  const totPnl = totVal - totCst
  const COLS = [T.blue, T.green, T.amber, '#a78bfa', T.red]
  const pie = positions.map((p, i) => ({ name: p.ticker, v: p.cur, c: COLS[i] }))
  const portPts = genPrices(totVal, 777, 120).map(x => ({ ...x, v: x.p }))

  return (
    <div style={{ padding: '26px 30px', maxWidth: 1200, fontFamily: T.sans }}>
      <div style={{ marginBottom: 22 }}>
        <div style={{ fontSize: 22, fontWeight: 700, color: T.text }}>Portfolio Analytics</div>
        <div style={{ fontSize: 13, color: T.sub, marginTop: 3 }}>India Equity Portfolio · NSE Listed</div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 18 }}>
        <Stat label="Portfolio Value" value={fI(totVal)} sub="Current market value" icon={Database} />
        <Stat
          label="Total P&L"
          value={(totPnl >= 0 ? '+' : '') + fI(totPnl)}
          sub={pct((totPnl / totCst) * 100)}
          color={totPnl >= 0 ? T.green : T.red}
          icon={TrendingUp}
        />
        <Stat label="Portfolio Beta" value="1.12" sub="vs Nifty 50" icon={Activity} />
        <Stat label="Sharpe Ratio" value="1.28" sub="12-month trailing" icon={Shield} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 14, marginBottom: 14 }}>
        <div style={card({ padding: '16px 18px' })}>
          <div style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 14 }}>Portfolio Value (6M)</div>
          <ResponsiveContainer width="100%" height={185}>
            <AreaChart data={portPts} margin={{ top: 4, right: 4, bottom: 0, left: 60 }}>
              <defs>
                <linearGradient id="pg" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={T.green} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={T.green} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="d" tick={{ fontSize: 10, fill: T.muted }} tickLine={false} axisLine={false} interval={15} />
              <YAxis
                tick={{ fontSize: 10, fill: T.muted, fontFamily: T.mono }}
                tickLine={false} axisLine={false} domain={['auto', 'auto']}
                tickFormatter={v => '₹' + (v / 100000).toFixed(0) + 'L'}
              />
              <Tooltip content={<CT />} />
              <Area type="monotone" dataKey="v" stroke={T.green} strokeWidth={2} fill="url(#pg)" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div style={card({ padding: '16px 18px' })}>
          <div style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 8 }}>Allocation</div>
          <ResponsiveContainer width="100%" height={150}>
            <PieChart>
              <Pie data={pie} cx="50%" cy="50%" innerRadius={42} outerRadius={65} dataKey="v" paddingAngle={3}>
                {pie.map((e, i) => <Cell key={i} fill={e.c} />)}
              </Pie>
              <Tooltip formatter={(v: any) => [fI(typeof v === 'number' ? v : 0), 'Value']} />
            </PieChart>
          </ResponsiveContainer>
          {pie.map((d, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 7, marginTop: 5 }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: d.c, flexShrink: 0 }} />
              <span style={{ fontSize: 11, fontFamily: T.mono, color: T.sub }}>{d.name}</span>
              <span style={{ fontSize: 11, color: T.muted, marginLeft: 'auto' }}>{(d.v / totVal * 100).toFixed(1)}%</span>
            </div>
          ))}
        </div>
      </div>

      <div style={card({ overflow: 'auto' })}>
        <div style={{ padding: '13px 18px', borderBottom: `1px solid ${T.b}`, fontSize: 13, fontWeight: 600, color: T.text }}>Positions</div>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: `1px solid ${T.b}` }}>
              {['Ticker', 'Sector', 'Qty', 'Avg Cost', 'LTP', 'Value', 'P&L', 'P&L%', 'Score'].map(h => (
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
              <tr key={p.ticker} style={{ borderBottom: `1px solid ${T.b}`, background: i % 2 === 0 ? 'transparent' : `${T.el}55` }}>
                <td style={{ padding: '11px 15px', fontFamily: T.mono, fontWeight: 700, fontSize: 12, color: T.text }}>{p.ticker}</td>
                <td style={{ padding: '11px 15px' }}><Tag>{p.stk?.sector}</Tag></td>
                <td style={{ padding: '11px 15px', textAlign: 'right', fontFamily: T.mono, fontSize: 12, color: T.text }}>{p.qty}</td>
                <td style={{ padding: '11px 15px', textAlign: 'right', fontFamily: T.mono, fontSize: 12, color: T.sub }}>
                  ₹{p.cost.toLocaleString('en-IN')}
                </td>
                <td style={{ padding: '11px 15px', textAlign: 'right', fontFamily: T.mono, fontSize: 12, color: T.text }}>
                  ₹{p.stk?.price.toLocaleString('en-IN')}
                </td>
                <td style={{ padding: '11px 15px', textAlign: 'right', fontFamily: T.mono, fontSize: 12, color: T.text }}>{fI(p.cur)}</td>
                <td style={{ padding: '11px 15px', textAlign: 'right', fontFamily: T.mono, fontSize: 12, color: p.pnl >= 0 ? T.green : T.red }}>
                  {p.pnl >= 0 ? '+' : ''}{fI(p.pnl)}
                </td>
                <td style={{ padding: '11px 15px', textAlign: 'right', fontFamily: T.mono, fontSize: 12, color: p.pp >= 0 ? T.green : T.red }}>
                  {pct(p.pp)}
                </td>
                <td style={{ padding: '11px 15px', textAlign: 'right' }}><Badge v={p.stk?.composite || 0} /></td>
              </tr>
            ))}
          </tbody>
        </table>
        <div style={{ padding: '13px 18px', borderTop: `1px solid ${T.b}`, display: 'flex', gap: 32 }}>
          {[
            ['Beta', '1.12'],
            ['Volatility (Ann.)', '18.4%'],
            ['Sharpe Ratio', '1.28'],
            ['Max Drawdown', '-12.3%'],
            ['Positions', '5'],
          ].map(([l, v]) => (
            <div key={l}>
              <div style={{ fontSize: 10, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{l}</div>
              <div style={{ fontSize: 15, fontFamily: T.mono, fontWeight: 700, color: T.text, marginTop: 2 }}>{v}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
