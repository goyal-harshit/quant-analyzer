'use client'

import { Globe, Activity, TrendingUp, TrendingDown, Landmark, DollarSign } from 'lucide-react'
import { LineChart, Line, AreaChart, Area, BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { MACRO, T } from '@/lib/stockData'

const card = (x = {}) => ({ background: T.card, border: `1px solid ${T.b}`, borderRadius: 10, ...x })
const sc = v => v >= 70 ? T.green : v >= 45 ? T.amber : T.red

function CT({ active, payload, label }: { active?: any; payload?: any; label?: any } = {}) {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: T.el, border: `1px solid ${T.b}`, borderRadius: 6, padding: '8px 12px', fontSize: 12 }}>
      <div style={{ color: T.muted, marginBottom: 4 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color || T.text, fontFamily: T.mono }}>
          {p.name && <span style={{ color: T.sub }}>{p.name}: </span>}
          {typeof p.value === 'number' ? p.value.toFixed(2) : p.value}
        </div>
      ))}
    </div>
  )
}

export default function MacroDashboard() {
  return (
    <div style={{ padding: '26px 30px', maxWidth: 1200, fontFamily: T.sans }}>
      <div style={{ marginBottom: 22 }}>
        <div style={{ fontSize: 22, fontWeight: 700, color: T.text }}>Macro Dashboard</div>
        <div style={{ fontSize: 13, color: T.sub, marginTop: 3 }}>
          India macroeconomic indicators · RBI DBIE · MOSPI · NSE (all free, public sources)
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 18 }}>
        {[
          ['RBI Repo Rate', '5.75%', 'Jun 2026', T.blue],
          ['CPI Inflation', '2.60%', 'May 2026', T.green],
          ['GDP Growth FY25', '7.6%', 'Advance Est.', T.amber],
          ['USD / INR', '84.32', 'Jun 2026', T.text],
        ].map(([l, v, s, c]) => (
          <div key={l} style={card({ padding: '13px 16px' })}>
            <div style={{ fontSize: 10, color: T.muted, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 5 }}>{l}</div>
            <div style={{ fontSize: 21, fontWeight: 700, fontFamily: T.mono, color: c }}>{v}</div>
            <div style={{ fontSize: 11, color: T.sub, marginTop: 3 }}>{s}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
        <div style={card({ padding: '16px 18px' })}>
          <div style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 14 }}>RBI Repo Rate (%)</div>
          <ResponsiveContainer width="100%" height={175}>
            <LineChart data={MACRO.repo} margin={{ top: 4, right: 8, bottom: 0, left: 30 }}>
              <CartesianGrid stroke={T.b} strokeDasharray="3 3" />
              <XAxis dataKey="q" tick={{ fontSize: 9, fill: T.muted }} tickLine={false} axisLine={false} interval={2} />
              <YAxis tick={{ fontSize: 10, fill: T.muted, fontFamily: T.mono }} tickLine={false} axisLine={false} domain={[5, 7]} tickFormatter={v => v + '%'} />
              <Tooltip content={<CT />} />
              <Line type="stepAfter" dataKey="v" stroke={T.blue} strokeWidth={2.5} dot={{ r: 3, fill: T.blue }} name="Repo Rate" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div style={card({ padding: '16px 18px' })}>
          <div style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 14 }}>CPI Inflation India (%)</div>
          <ResponsiveContainer width="100%" height={175}>
            <AreaChart data={MACRO.cpi} margin={{ top: 4, right: 8, bottom: 0, left: 30 }}>
              <defs>
                <linearGradient id="cg" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={T.amber} stopOpacity={0.4} />
                  <stop offset="95%" stopColor={T.amber} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke={T.b} strokeDasharray="3 3" />
              <XAxis dataKey="m" tick={{ fontSize: 9, fill: T.muted }} tickLine={false} axisLine={false} interval={2} />
              <YAxis tick={{ fontSize: 10, fill: T.muted, fontFamily: T.mono }} tickLine={false} axisLine={false} domain={[2, 7]} tickFormatter={v => v + '%'} />
              <Tooltip content={<CT />} />
              <Area type="monotone" dataKey="v" stroke={T.amber} strokeWidth={2} fill="url(#cg)" name="CPI%" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div style={card({ padding: '16px 18px' })}>
          <div style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 14 }}>USD / INR Exchange Rate</div>
          <ResponsiveContainer width="100%" height={175}>
            <LineChart data={MACRO.inr} margin={{ top: 4, right: 8, bottom: 0, left: 40 }}>
              <CartesianGrid stroke={T.b} strokeDasharray="3 3" />
              <XAxis dataKey="m" tick={{ fontSize: 9, fill: T.muted }} tickLine={false} axisLine={false} interval={2} />
              <YAxis tick={{ fontSize: 10, fill: T.muted, fontFamily: T.mono }} tickLine={false} axisLine={false} domain={[83, 87]} tickFormatter={v => '₹' + v} />
              <Tooltip content={<CT />} />
              <Line type="monotone" dataKey="v" stroke={'#a78bfa'} strokeWidth={2} dot={{ r: 3, fill: '#a78bfa' }} name="USD/INR" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div style={card({ padding: '16px 18px' })}>
          <div style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 14 }}>FII Net Flows (₹ Cr)</div>
          <ResponsiveContainer width="100%" height={175}>
            <BarChart data={MACRO.fii} margin={{ top: 4, right: 8, bottom: 0, left: 50 }}>
              <CartesianGrid stroke={T.b} strokeDasharray="3 3" />
              <XAxis dataKey="m" tick={{ fontSize: 9, fill: T.muted }} tickLine={false} axisLine={false} interval={2} />
              <YAxis tick={{ fontSize: 10, fill: T.muted, fontFamily: T.mono }} tickLine={false} axisLine={false} tickFormatter={v => (v / 1000).toFixed(0) + 'K'} />
              <Tooltip formatter={v => ['₹' + v.toLocaleString('en-IN') + ' Cr', 'FII Flow']} />
              <Bar dataKey="v" name="FII Flow">
                {MACRO.fii.map((e, i) => <Cell key={i} fill={e.v >= 0 ? T.green : T.red} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div style={card({ padding: '15px 18px', marginTop: 14 })}>
        <div style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 12 }}>Current Macro Regime Analysis</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 12 }}>
          {[
            ['\u{1F3E6}', 'Monetary Policy', 'Easing', T.green, 'RBI in rate-cut cycle. Repo at 5.75%. Favours Banking, NBFC, Real Estate.'],
            ['\u{1F4C9}', 'Inflation', 'Controlled', T.green, 'CPI at 2.6% — below RBI 4% target. Creates room for 25-50 bps more cuts in FY26.'],
            ['\u{1F30D}', 'FII Sentiment', 'Recovering', T.amber, 'FII flows positive for 3 consecutive months after large Jan–Feb 2025 outflows.'],
          ].map(([ic, l, sig, c, desc]) => (
            <div key={l} style={{ background: T.el, borderRadius: 8, padding: '12px 14px', border: `1px solid ${T.b}` }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <span style={{ fontSize: 16 }}>{ic}</span>
                <span style={{ fontSize: 11, color: T.sub }}>{l}</span>
                <span
                  style={{
                    marginLeft: 'auto', background: `${c}22`, color: c, border: `1px solid ${c}44`,
                    borderRadius: 4, padding: '1px 7px', fontSize: 10, fontWeight: 700,
                  }}
                >
                  {sig}
                </span>
              </div>
              <div style={{ fontSize: 11, color: T.muted, lineHeight: 1.6 }}>{desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
