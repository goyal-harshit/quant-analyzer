// /frontend/components/stocks/StockChart.tsx
'use client'

import { useEffect, useRef, useState } from 'react'
import { createChart, ColorType, CandlestickSeries, LineSeries, HistogramSeries } from 'lightweight-charts'
import { Activity, Maximize2, Minimize2 } from 'lucide-react'

interface ChartDataPoint {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

interface StockChartProps {
  data: ChartDataPoint[]
}

const PERIODS = ['1M', '3M', '6M', '1Y', '5Y', 'MAX']

// ── Indicator math (client-side, from the OHLC already loaded) ──────────────
function sma(values: number[], period: number): (number | null)[] {
  const out: (number | null)[] = []
  for (let i = 0; i < values.length; i++) {
    if (i < period - 1) { out.push(null); continue }
    let sum = 0
    for (let j = 0; j < period; j++) sum += values[i - j]
    out.push(sum / period)
  }
  return out
}
function stddev(values: number[], period: number, means: (number | null)[]): (number | null)[] {
  const out: (number | null)[] = []
  for (let i = 0; i < values.length; i++) {
    const m = means[i]
    if (i < period - 1 || m == null) { out.push(null); continue }
    let s = 0
    for (let j = 0; j < period; j++) s += (values[i - j] - m) ** 2
    out.push(Math.sqrt(s / period))
  }
  return out
}
function ema(values: number[], period: number): number[] {
  const k = 2 / (period + 1)
  const out: number[] = []
  let prev = values[0]
  for (let i = 0; i < values.length; i++) {
    prev = i === 0 ? values[0] : values[i] * k + prev * (1 - k)
    out.push(prev)
  }
  return out
}
function rsi(closes: number[], period = 14): (number | null)[] {
  const out: (number | null)[] = new Array(closes.length).fill(null)
  if (closes.length <= period) return out
  let gain = 0, loss = 0
  for (let i = 1; i <= period; i++) {
    const d = closes[i] - closes[i - 1]
    if (d >= 0) gain += d; else loss -= d
  }
  let avgG = gain / period, avgL = loss / period
  out[period] = 100 - 100 / (1 + (avgL === 0 ? 100 : avgG / avgL))
  for (let i = period + 1; i < closes.length; i++) {
    const d = closes[i] - closes[i - 1]
    avgG = (avgG * (period - 1) + (d > 0 ? d : 0)) / period
    avgL = (avgL * (period - 1) + (d < 0 ? -d : 0)) / period
    out[i] = 100 - 100 / (1 + (avgL === 0 ? 100 : avgG / avgL))
  }
  return out
}

export default function StockChart({ data }: StockChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<any>(null)
  const [selectedPeriod, setSelectedPeriod] = useState('1Y')
  const [overlays, setOverlays] = useState({ ma20: false, ma50: false, bb: false })
  const [subpane, setSubpane] = useState<'none' | 'rsi' | 'macd'>('none')
  const [fullscreen, setFullscreen] = useState(false)

  useEffect(() => {
    if (!chartContainerRef.current || !data || data.length === 0) return
    const container = chartContainerRef.current

    const getFilteredData = () => {
      const sorted = [...data].sort((a, b) => a.date.localeCompare(b.date))
      if (selectedPeriod === 'MAX') return sorted
      const latestDate = new Date(sorted[sorted.length - 1].date)
      const cutoff = new Date(latestDate)
      if (selectedPeriod === '1M') cutoff.setMonth(latestDate.getMonth() - 1)
      else if (selectedPeriod === '3M') cutoff.setMonth(latestDate.getMonth() - 3)
      else if (selectedPeriod === '6M') cutoff.setMonth(latestDate.getMonth() - 6)
      else if (selectedPeriod === '1Y') cutoff.setFullYear(latestDate.getFullYear() - 1)
      else if (selectedPeriod === '5Y') cutoff.setFullYear(latestDate.getFullYear() - 5)
      const cutoffStr = cutoff.toISOString().split('T')[0]
      return sorted.filter((d) => d.date >= cutoffStr)
    }

    const filtered = getFilteredData()
    if (filtered.length === 0) return

    const baseHeight = fullscreen ? Math.max(480, window.innerHeight - 220) : 380
    const subHeight = subpane === 'none' ? 0 : 130
    const handleResize = () => chartRef.current?.applyOptions({ width: container.clientWidth })

    const chart = createChart(container, {
      layout: {
        background: { type: ColorType.Solid, color: '#040b16' },
        textColor: '#94a3b8', fontSize: 11, fontFamily: 'var(--font-mono, monospace)',
        panes: { separatorColor: '#162034', separatorHoverColor: 'rgba(59,130,246,0.3)' },
      },
      grid: { vertLines: { color: 'rgba(22, 32, 52, 0.4)' }, horzLines: { color: 'rgba(22, 32, 52, 0.4)' } },
      width: container.clientWidth,
      height: baseHeight + subHeight,
      timeScale: { borderColor: '#162034', timeVisible: true, rightOffset: 5, barSpacing: 6 },
      rightPriceScale: { borderColor: '#162034', autoScale: true },
      crosshair: {
        vertLine: { color: '#3b82f6', width: 1, style: 3, labelBackgroundColor: '#0c1526' },
        horzLine: { color: '#3b82f6', width: 1, style: 3, labelBackgroundColor: '#0c1526' },
      },
    })
    chartRef.current = chart

    const candle = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e', downColor: '#f43f5e', borderVisible: false,
      wickUpColor: '#22c55e', wickDownColor: '#f43f5e',
    })
    const ohlc = filtered.map((d) => ({ time: d.date, open: d.open, high: d.high, low: d.low, close: d.close }))
    candle.setData(ohlc)

    const volume = chart.addSeries(HistogramSeries, { priceFormat: { type: 'volume' }, priceScaleId: '' })
    volume.priceScale().applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } })
    volume.setData(filtered.map((d) => ({
      time: d.date, value: d.volume,
      color: d.close >= d.open ? 'rgba(34, 197, 94, 0.22)' : 'rgba(244, 63, 94, 0.22)',
    })))

    const closes = filtered.map((d) => d.close)
    const times = filtered.map((d) => d.date)
    const lineData = (vals: (number | null)[]) =>
      vals.map((v, i) => (v == null ? null : { time: times[i], value: v })).filter(Boolean) as any[]

    // ── Overlays (price pane) ──
    if (overlays.ma20) {
      const s = chart.addSeries(LineSeries, { color: '#f59e0b', lineWidth: 2, priceLineVisible: false, crosshairMarkerVisible: false })
      s.setData(lineData(sma(closes, 20)))
    }
    if (overlays.ma50) {
      const s = chart.addSeries(LineSeries, { color: '#a855f7', lineWidth: 2, priceLineVisible: false, crosshairMarkerVisible: false })
      s.setData(lineData(sma(closes, 50)))
    }
    if (overlays.bb) {
      const mid = sma(closes, 20)
      const sd = stddev(closes, 20, mid)
      const upper = mid.map((m, i) => (m == null || sd[i] == null ? null : m + 2 * (sd[i] as number)))
      const lower = mid.map((m, i) => (m == null || sd[i] == null ? null : m - 2 * (sd[i] as number)))
      const up = chart.addSeries(LineSeries, { color: 'rgba(59,130,246,0.6)', lineWidth: 1, priceLineVisible: false, crosshairMarkerVisible: false })
      const lo = chart.addSeries(LineSeries, { color: 'rgba(59,130,246,0.6)', lineWidth: 1, priceLineVisible: false, crosshairMarkerVisible: false })
      const md = chart.addSeries(LineSeries, { color: 'rgba(148,163,184,0.5)', lineWidth: 1, lineStyle: 2, priceLineVisible: false, crosshairMarkerVisible: false })
      up.setData(lineData(upper)); lo.setData(lineData(lower)); md.setData(lineData(mid))
    }

    // ── Sub-pane indicator (pane 1) ──
    if (subpane === 'rsi') {
      const r = rsi(closes, 14)
      const s = chart.addSeries(LineSeries, { color: '#06b6d4', lineWidth: 2, priceLineVisible: false }, 1)
      s.setData(lineData(r))
      // 70/30 guide lines
      const g70 = chart.addSeries(LineSeries, { color: 'rgba(244,63,94,0.4)', lineWidth: 1, lineStyle: 2, priceLineVisible: false, crosshairMarkerVisible: false, lastValueVisible: false }, 1)
      const g30 = chart.addSeries(LineSeries, { color: 'rgba(34,197,94,0.4)', lineWidth: 1, lineStyle: 2, priceLineVisible: false, crosshairMarkerVisible: false, lastValueVisible: false }, 1)
      g70.setData(times.map((t) => ({ time: t, value: 70 })))
      g30.setData(times.map((t) => ({ time: t, value: 30 })))
    } else if (subpane === 'macd') {
      const e12 = ema(closes, 12), e26 = ema(closes, 26)
      const macd = e12.map((v, i) => v - e26[i])
      const signal = ema(macd, 9)
      const hist = macd.map((v, i) => v - signal[i])
      const macdS = chart.addSeries(LineSeries, { color: '#3b82f6', lineWidth: 2, priceLineVisible: false }, 1)
      const sigS = chart.addSeries(LineSeries, { color: '#f59e0b', lineWidth: 2, priceLineVisible: false }, 1)
      const histS = chart.addSeries(HistogramSeries, { priceLineVisible: false }, 1)
      macdS.setData(times.map((t, i) => ({ time: t, value: macd[i] })))
      sigS.setData(times.map((t, i) => ({ time: t, value: signal[i] })))
      histS.setData(times.map((t, i) => ({ time: t, value: hist[i], color: hist[i] >= 0 ? 'rgba(34,197,94,0.5)' : 'rgba(244,63,94,0.5)' })))
    }

    // Size the sub-pane if present.
    if (subpane !== 'none') {
      try { chart.panes()[1]?.setHeight(subHeight) } catch {}
    }

    chart.timeScale().fitContent()
    window.addEventListener('resize', handleResize)
    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
      chartRef.current = null
    }
  }, [data, selectedPeriod, overlays, subpane, fullscreen])

  const Toggle = ({ active, onClick, label, color }: { active: boolean; onClick: () => void; label: string; color: string }) => (
    <button
      onClick={onClick}
      className={`px-2.5 py-1 text-[10px] font-bold rounded border transition-all ${
        active ? 'text-white shadow-inner' : 'border-border/60 text-textMuted hover:text-textSub'
      }`}
      style={active ? { backgroundColor: `${color}22`, borderColor: color, color } : {}}
    >
      {label}
    </button>
  )

  return (
    <div className={`w-full glass rounded-xl border border-border p-4 sm:p-6 space-y-4 shadow-lg bg-card/60 backdrop-blur-md relative overflow-hidden ${fullscreen ? 'fixed inset-2 z-50 overflow-auto' : ''}`}>
      <div className="absolute top-0 right-0 w-80 h-80 bg-brand/5 rounded-full blur-[100px] pointer-events-none -z-10" />

      {/* Toolbar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 pb-2 border-b border-border/40">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-brand animate-pulse" />
          <span className="text-sm font-bold font-display text-textPrimary uppercase tracking-wider">Price Telemetry</span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {/* Period selector */}
          <div className="flex items-center bg-elevated/70 border border-border/80 p-0.5 rounded-lg">
            {PERIODS.map((p) => (
              <button key={p} onClick={() => setSelectedPeriod(p)}
                className={`px-2.5 py-1 text-[11px] font-mono font-bold rounded transition-all ${
                  selectedPeriod === p ? 'bg-brand text-white shadow-md scale-105' : 'text-textSub hover:text-textPrimary hover:bg-border/30'
                }`}>{p}</button>
            ))}
          </div>
          {/* Overlays */}
          <div className="flex items-center gap-1.5 border-l border-border/50 pl-2">
            <Toggle active={overlays.ma20} onClick={() => setOverlays((o) => ({ ...o, ma20: !o.ma20 }))} label="MA20" color="#f59e0b" />
            <Toggle active={overlays.ma50} onClick={() => setOverlays((o) => ({ ...o, ma50: !o.ma50 }))} label="MA50" color="#a855f7" />
            <Toggle active={overlays.bb} onClick={() => setOverlays((o) => ({ ...o, bb: !o.bb }))} label="BB" color="#3b82f6" />
          </div>
          {/* Sub-pane indicators */}
          <div className="flex items-center gap-1.5 border-l border-border/50 pl-2">
            <Toggle active={subpane === 'rsi'} onClick={() => setSubpane((s) => (s === 'rsi' ? 'none' : 'rsi'))} label="RSI" color="#06b6d4" />
            <Toggle active={subpane === 'macd'} onClick={() => setSubpane((s) => (s === 'macd' ? 'none' : 'macd'))} label="MACD" color="#3b82f6" />
          </div>
          <button onClick={() => setFullscreen((f) => !f)} className="p-1.5 rounded border border-border/60 text-textMuted hover:text-textPrimary" title="Fullscreen">
            {fullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      <div ref={chartContainerRef} className="w-full relative rounded-lg overflow-hidden border border-border/50 bg-[#040b16]" />
    </div>
  )
}
