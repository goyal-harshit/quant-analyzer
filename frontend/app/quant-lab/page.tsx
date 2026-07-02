'use client'

import { useEffect, useMemo, useState } from 'react'
import { Sliders, Play, RefreshCw, TrendingUp, Dice5, Layers } from 'lucide-react'
import { T } from '@/lib/stockData'
import { quantLabApi } from '@/lib/api'

const card = (x = {}) => ({ background: T.card, border: `1px solid ${T.b}`, borderRadius: 10, ...x })
const sc = (v: number | null) => v === null || v === undefined ? T.muted : v >= 70 ? T.green : v >= 45 ? T.amber : T.red

// Factors shown as adjustable weights (composite is derived, not weighted).
const DEFAULT_WEIGHTS: Record<string, number> = {
  momentum: 25, quality: 25, value: 20, growth: 20, low_volatility: 10,
  size: 0, reversal: 0, profitability: 0, financial_health: 0, dividend: 0,
  liquidity: 0, beta: 0, earnings_quality: 0, trend: 0,
}

// Columns surfaced in the ranking table (composite first).
const TABLE_FACTORS = ['composite', 'momentum', 'value', 'quality', 'growth', 'low_volatility', 'profitability', 'trend']

function Badge({ v }: { v: number | null }) {
  const c = sc(v)
  return (
    <span style={{ background: `${c}22`, color: c, border: `1px solid ${c}44`, borderRadius: 4, padding: '2px 8px', fontSize: 12, fontFamily: T.mono, fontWeight: 700 }}>
      {v !== null && v !== undefined ? Math.round(v) : '—'}
    </span>
  )
}

export default function QuantLabPage() {
  const [defs, setDefs] = useState<Record<string, { label: string; description: string; family: string }>>({})
  const [weights, setWeights] = useState<Record<string, number>>(DEFAULT_WEIGHTS)
  const [universe, setUniverse] = useState<'NIFTY50' | 'NIFTY500'>('NIFTY500')

  const [results, setResults] = useState<any[]>([])
  const [ran, setRan] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [opt, setOpt] = useState<any>(null)
  const [mc, setMc] = useState<any>(null)
  const [busy, setBusy] = useState<'opt' | 'mc' | null>(null)

  useEffect(() => {
    quantLabApi.getFactorDefinitions().then(setDefs).catch(() => {})
  }, [])

  // Normalised weights (0-1) for the API; only non-zero factors count.
  const apiWeights = useMemo(() => {
    const total = Object.values(weights).reduce((a, b) => a + (b || 0), 0)
    if (total <= 0) return { momentum: 1 }
    const out: Record<string, number> = {}
    for (const [k, v] of Object.entries(weights)) if (v > 0) out[k] = +(v / total).toFixed(4)
    return out
  }, [weights])

  const body = () => ({ name: 'Custom Model', factor_weights: apiWeights, universe })

  const runScore = async () => {
    setLoading(true); setError(null); setOpt(null); setMc(null)
    try {
      const r = await quantLabApi.score(body())
      setResults(r.results || [])
      setRan(true)
    } catch {
      setError('Scoring failed — try again in a moment.')
    } finally {
      setLoading(false)
    }
  }

  const runOptimize = async () => {
    setBusy('opt')
    try { setOpt(await quantLabApi.optimize(body())) } catch { setOpt({ error: true }) } finally { setBusy(null) }
  }
  const runMonteCarlo = async () => {
    setBusy('mc')
    try { setMc(await quantLabApi.monteCarlo(body())) } catch { setMc({ error: true }) } finally { setBusy(null) }
  }

  const factorKeys = Object.keys(DEFAULT_WEIGHTS)
  const activeCount = Object.values(weights).filter(v => v > 0).length

  return (
    <div style={{ padding: '26px 30px', maxWidth: 1400, fontFamily: T.sans }} className="w-full">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-5">
        <div>
          <div style={{ fontSize: 22, fontWeight: 700, color: T.text, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Sliders size={20} color={T.blue} /> Quant Lab
          </div>
          <div style={{ fontSize: 13, color: T.sub, marginTop: 3 }}>
            Build a custom 15-factor model · rank {universe === 'NIFTY500' ? '500' : '50'} names · optimise &amp; simulate
          </div>
        </div>
        <div style={{ display: 'flex', background: T.el, border: `1px solid ${T.b}`, borderRadius: 6, overflow: 'hidden' }} className="w-fit">
          {([['NIFTY50', 'Nifty 50 · Live'], ['NIFTY500', 'Nifty 500']] as const).map(([val, label]) => (
            <button key={val} onClick={() => setUniverse(val)}
              style={{ padding: '6px 12px', fontSize: 12, fontWeight: 600, cursor: 'pointer', border: 'none', fontFamily: T.sans,
                background: universe === val ? `${T.blue}22` : 'transparent', color: universe === val ? T.blue : T.sub }}>
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* ── Factor weight builder ── */}
      <div style={card({ padding: '16px 18px', marginBottom: 18 })}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: T.text, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Layers size={15} color={T.muted} /> Factor Weights <span style={{ color: T.muted, fontWeight: 400 }}>· {activeCount} active</span>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={() => setWeights(DEFAULT_WEIGHTS)}
              style={{ padding: '4px 12px', borderRadius: 100, fontSize: 11, fontWeight: 600, cursor: 'pointer', background: 'transparent', border: `1px dashed ${T.b}`, color: T.muted }}>
              Reset
            </button>
            <button onClick={runScore} disabled={loading}
              style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 16px', borderRadius: 6, fontSize: 12, fontWeight: 700, cursor: loading ? 'default' : 'pointer', background: T.blue, border: 'none', color: '#fff', opacity: loading ? 0.6 : 1 }}>
              {loading ? <RefreshCw size={13} className="animate-spin" /> : <Play size={13} />} Run Model
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-x-5 gap-y-3">
          {factorKeys.map(k => (
            <div key={k}>
              <div style={{ fontSize: 10.5, color: T.muted, marginBottom: 3, display: 'flex', justifyContent: 'space-between' }} title={defs[k]?.description || ''}>
                <span style={{ textTransform: 'capitalize' }}>{defs[k]?.label || k.replace(/_/g, ' ')}</span>
                <span style={{ color: weights[k] > 0 ? T.blue : T.muted, fontFamily: T.mono }}>{weights[k]}</span>
              </div>
              <input type="range" min={0} max={50} value={weights[k]}
                onChange={e => setWeights(w => ({ ...w, [k]: +e.target.value }))}
                style={{ width: '100%', accentColor: T.blue }} />
            </div>
          ))}
        </div>
      </div>

      {/* ── Actions on the scored model ── */}
      {ran && !error && (
        <div style={{ display: 'flex', gap: 10, marginBottom: 18, flexWrap: 'wrap' }}>
          <button onClick={runOptimize} disabled={busy !== null}
            style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '7px 14px', borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer', background: T.el, border: `1px solid ${T.b}`, color: T.text }}>
            {busy === 'opt' ? <RefreshCw size={13} className="animate-spin" /> : <TrendingUp size={13} color={T.green} />} Build Optimised Portfolio
          </button>
          <button onClick={runMonteCarlo} disabled={busy !== null}
            style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '7px 14px', borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: 'pointer', background: T.el, border: `1px solid ${T.b}`, color: T.text }}>
            {busy === 'mc' ? <RefreshCw size={13} className="animate-spin" /> : <Dice5 size={13} color={T.purple} />} Monte-Carlo Simulation
          </button>
        </div>
      )}

      {/* ── Optimise + Monte-Carlo result cards ── */}
      {(opt || mc) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-18" style={{ marginBottom: 18 }}>
          {opt?.error && (
            <div style={card({ padding: 16, textAlign: 'center' })}>
              <span style={{ fontSize: 12, color: T.red }}>Portfolio optimisation failed — please try again in a moment.</span>
            </div>
          )}
          {mc?.error && (
            <div style={card({ padding: 16, textAlign: 'center' })}>
              <span style={{ fontSize: 12, color: T.red }}>Monte-Carlo simulation failed — please try again in a moment.</span>
            </div>
          )}
          {opt && !opt.error && (
            <div style={card({ padding: 16 })}>
              <div style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 10 }}>Optimised Portfolio · top {opt.holdings?.length} names</div>
              <div style={{ display: 'flex', gap: 14, flexWrap: 'wrap', marginBottom: 12 }}>
                {Object.entries(opt.metrics || {}).map(([k, v]: any) => (
                  <div key={k}>
                    <div style={{ fontSize: 10, color: T.muted, textTransform: 'uppercase' }}>{k.replace(/_pct/, ' %').replace(/_/g, ' ')}</div>
                    <div style={{ fontSize: 15, fontWeight: 700, color: T.text, fontFamily: T.mono }}>{v}</div>
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {opt.holdings?.slice(0, 12).map((h: any) => (
                  <span key={h.ticker} style={{ fontSize: 11, background: T.el, border: `1px solid ${T.b}`, borderRadius: 4, padding: '2px 8px', color: T.sub }}>
                    {h.ticker} <b style={{ color: T.text }}>{h.weight}%</b>
                  </span>
                ))}
              </div>
            </div>
          )}
          {mc && !mc.error && (
            <div style={card({ padding: 16 })}>
              <div style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 10 }}>
                Monte-Carlo · {mc.simulations} paths / {mc.horizon_days}d
              </div>
              <div className="grid grid-cols-5 gap-2 mb-3">
                {(['p5', 'p25', 'p50', 'p75', 'p95'] as const).map(p => (
                  <div key={p} style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 10, color: T.muted }}>{p.toUpperCase()}</div>
                    <div style={{ fontSize: 13, fontWeight: 700, fontFamily: T.mono, color: mc.projected_return_pct[p] >= 0 ? T.green : T.red }}>
                      {mc.projected_return_pct[p] >= 0 ? '+' : ''}{mc.projected_return_pct[p]}%
                    </div>
                  </div>
                ))}
              </div>
              <div style={{ fontSize: 11.5, color: T.sub }}>
                Probability of loss over horizon: <b style={{ color: mc.prob_loss_pct > 30 ? T.red : T.amber }}>{mc.prob_loss_pct}%</b>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Ranking table ── */}
      <div style={card({ overflow: 'auto' })} className="w-full overflow-x-auto">
        {loading ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '48px 0', gap: 10 }}>
            <RefreshCw className="w-6 h-6 animate-spin" style={{ color: T.blue }} />
            <span style={{ fontSize: 12, color: T.sub }}>Scoring {universe === 'NIFTY500' ? '500' : '50'} names across 15 factors…</span>
          </div>
        ) : error ? (
          <div style={{ padding: '40px 0', textAlign: 'center' }}>
            <div style={{ fontSize: 12, color: T.red, marginBottom: 10 }}>{error}</div>
            <button onClick={runScore} style={{ padding: '6px 14px', background: T.el, border: `1px solid ${T.b}`, borderRadius: 6, fontSize: 12, color: T.sub, cursor: 'pointer' }}>Retry</button>
          </div>
        ) : !ran ? (
          <div style={{ padding: '48px 20px', textAlign: 'center', color: T.sub, fontSize: 13, lineHeight: 1.7 }}>
            Set your factor weights above and hit <b style={{ color: T.text }}>Run Model</b> to rank the universe.<br />
            The composite score blends your active factors; every stock is also scored on all 15 factors individually.
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${T.b}` }}>
                <th style={{ padding: '10px 13px', fontSize: 10, color: T.muted, textAlign: 'left', textTransform: 'uppercase' }}>#</th>
                <th style={{ padding: '10px 13px', fontSize: 10, color: T.muted, textAlign: 'left', textTransform: 'uppercase' }}>Ticker</th>
                <th style={{ padding: '10px 13px', fontSize: 10, color: T.muted, textAlign: 'left', textTransform: 'uppercase' }}>Sector</th>
                {TABLE_FACTORS.map(f => (
                  <th key={f} style={{ padding: '10px 13px', fontSize: 10, color: f === 'composite' ? T.blue : T.muted, textAlign: 'right', textTransform: 'uppercase', whiteSpace: 'nowrap' }} title={defs[f]?.description || ''}>
                    {defs[f]?.label || f.replace(/_/g, ' ')}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {results.slice(0, 100).map((r, i) => (
                <tr key={r.ticker} style={{ borderBottom: `1px solid ${T.b}` }}>
                  <td style={{ padding: '9px 13px', fontSize: 12, color: T.muted, fontFamily: T.mono }}>{i + 1}</td>
                  <td style={{ padding: '9px 13px', fontSize: 13, fontWeight: 700, color: T.text }}>{r.ticker}</td>
                  <td style={{ padding: '9px 13px', fontSize: 12, color: T.sub }}>{r.sector || '—'}</td>
                  {TABLE_FACTORS.map(f => (
                    <td key={f} style={{ padding: '9px 13px', textAlign: 'right' }}><Badge v={r[f]} /></td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      {ran && !loading && !error && (
        <div style={{ fontSize: 11, color: T.muted, marginTop: 10 }}>
          Showing top {Math.min(100, results.length)} of {results.length}. Scores are cross-sectional percentile ranks (0–100) across the selected universe.
          {universe === 'NIFTY500' && ' Broad mode uses live data where warm and deterministic model estimates otherwise.'}
        </div>
      )}
    </div>
  )
}
