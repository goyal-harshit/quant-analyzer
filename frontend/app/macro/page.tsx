'use client'

import { Globe, Activity, TrendingUp, TrendingDown, Landmark, DollarSign, RefreshCw } from 'lucide-react'
import { LineChart, Line, AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { T } from '@/lib/stockData'
import { useMacroIndicators } from '@/lib/hooks'

const card = (x = {}) => ({ background: T.card, border: `1px solid ${T.b}`, borderRadius: 10, ...x })

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
  const { data: macroData, isLoading, refetch } = useMacroIndicators()

  const repoData = macroData?.repo_rate || []
  const cpiData = macroData?.cpi || []
  const usdInrData = macroData?.usd_inr || []
  const fiiData = macroData?.fii_flows || []

  // Extract current values
  const currentRepo = repoData.length > 0 ? `${repoData[repoData.length - 1].value.toFixed(2)}%` : 'N/A'
  const currentCpi = cpiData.length > 0 ? `${cpiData[cpiData.length - 1].value.toFixed(2)}%` : 'N/A'
  const currentUsdInr = usdInrData.length > 0 ? `₹${usdInrData[usdInrData.length - 1].value.toFixed(2)}` : 'N/A'

  return (
    <div style={{ padding: '26px 30px', maxWidth: 1200, fontFamily: T.sans }}>
      <div style={{ marginBottom: 22, display: 'flex', justifyContent: 'between', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: 22, fontWeight: 700, color: T.text }}>Macro Dashboard</div>
          <div style={{ fontSize: 13, color: T.sub, marginTop: 3 }}>
            India macroeconomic indicators · RBI DBIE · MOSPI · FRED (all free, public sources)
          </div>
        </div>
        <button 
          onClick={() => refetch()} 
          style={{
            marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6,
            padding: '6px 12px', background: T.el, border: `1px solid ${T.b}`,
            borderRadius: 6, fontSize: 12, color: T.sub, cursor: 'pointer'
          }}
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh
        </button>
      </div>

      {isLoading ? (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '100px 0', gap: 10 }}>
          <RefreshCw className="w-8 h-8 text-brand animate-spin" />
          <span style={{ fontSize: 13, color: T.sub }}>Synchronizing macroeconomic telemetry...</span>
        </div>
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, marginBottom: 18 }}>
            {[
              ['RBI Repo Rate', currentRepo, 'Latest RBI policy', T.blue],
              ['CPI Inflation', currentCpi, 'Latest MOSPI report', T.green],
              ['GDP Growth FY25', '7.1%', 'Q1 GDP Growth (MOSPI)', T.amber],
              ['USD / INR', currentUsdInr, 'Spot exchange rate', T.text],
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
                <LineChart data={repoData} margin={{ top: 4, right: 8, bottom: 0, left: 30 }}>
                  <CartesianGrid stroke={T.b} strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 9, fill: T.muted }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: T.muted, fontFamily: T.mono }} tickLine={false} axisLine={false} domain={[5, 7]} tickFormatter={v => v + '%'} />
                  <Tooltip content={<CT />} />
                  <Line type="stepAfter" dataKey="value" stroke={T.blue} strokeWidth={2.5} dot={{ r: 3, fill: T.blue }} name="Repo Rate" />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div style={card({ padding: '16px 18px' })}>
              <div style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 14 }}>CPI Inflation India (%)</div>
              <ResponsiveContainer width="100%" height={175}>
                <AreaChart data={cpiData} margin={{ top: 4, right: 8, bottom: 0, left: 30 }}>
                  <defs>
                    <linearGradient id="cg" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={T.amber} stopOpacity={0.4} />
                      <stop offset="95%" stopColor={T.amber} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke={T.b} strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 9, fill: T.muted }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: T.muted, fontFamily: T.mono }} tickLine={false} axisLine={false} domain={[2, 7]} tickFormatter={v => v + '%'} />
                  <Tooltip content={<CT />} />
                  <Area type="monotone" dataKey="value" stroke={T.amber} strokeWidth={2} fill="url(#cg)" name="CPI%" dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div style={card({ padding: '16px 18px' })}>
              <div style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 14 }}>USD / INR Exchange Rate</div>
              <ResponsiveContainer width="100%" height={175}>
                <LineChart data={usdInrData} margin={{ top: 4, right: 8, bottom: 0, left: 40 }}>
                  <CartesianGrid stroke={T.b} strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 9, fill: T.muted }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: T.muted, fontFamily: T.mono }} tickLine={false} axisLine={false} domain={['auto', 'auto']} tickFormatter={v => '₹' + v} />
                  <Tooltip content={<CT />} />
                  <Line type="monotone" dataKey="value" stroke={'#a78bfa'} strokeWidth={2} dot={{ r: 3, fill: '#a78bfa' }} name="USD/INR" />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div style={card({ padding: '16px 18px' })}>
              <div style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 14 }}>FII Net Flows (₹ Cr)</div>
              <ResponsiveContainer width="100%" height={175}>
                <BarChart data={fiiData} margin={{ top: 4, right: 8, bottom: 0, left: 50 }}>
                  <CartesianGrid stroke={T.b} strokeDasharray="3 3" />
                  <XAxis dataKey="month" tick={{ fontSize: 9, fill: T.muted }} tickLine={false} axisLine={false} />
                  <YAxis tick={{ fontSize: 10, fill: T.muted, fontFamily: T.mono }} tickLine={false} axisLine={false} tickFormatter={v => (v / 1000).toFixed(0) + 'k'} />
                  <Tooltip content={<CT />} />
                  <Bar dataKey="value" fill={T.blue} name="FII Net Flow">
                    {fiiData.map((entry, index) => (
                      <rect key={index} fill={entry.value >= 0 ? T.green : T.red} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
