// /frontend/components/stocks/StockChart.tsx
'use client'

import { useEffect, useRef, useState } from 'react'
import { createChart, ColorType, CandlestickSeries, LineSeries, HistogramSeries } from 'lightweight-charts'
import { Calendar, Layers, Activity } from 'lucide-react'

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

export default function StockChart({ data }: StockChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<any>(null)
  const [selectedPeriod, setSelectedPeriod] = useState('1Y')
  const [ma20Active, setMa20Active] = useState(false)
  const [ma50Active, setMa50Active] = useState(false)

  // Moving Average Helper
  const computeSMA = (dataPoints: any[], period: number) => {
    const sma: any[] = []
    for (let i = 0; i < dataPoints.length; i++) {
      if (i < period - 1) continue
      let sum = 0
      for (let j = 0; j < period; j++) {
        sum += dataPoints[i - j].close
      }
      sma.push({
        time: dataPoints[i].time,
        value: sum / period,
      })
    }
    return sma
  }

  // Filter data based on selected period
  const getFilteredData = () => {
    if (!data || data.length === 0) return []
    const sorted = [...data].sort((a, b) => a.date.localeCompare(b.date))
    if (selectedPeriod === 'MAX') return sorted

    const latestDate = new Date(sorted[sorted.length - 1].date)
    let cutoff = new Date(latestDate)

    if (selectedPeriod === '1M') cutoff.setMonth(latestDate.getMonth() - 1)
    else if (selectedPeriod === '3M') cutoff.setMonth(latestDate.getMonth() - 3)
    else if (selectedPeriod === '6M') cutoff.setMonth(latestDate.getMonth() - 6)
    else if (selectedPeriod === '1Y') cutoff.setFullYear(latestDate.getFullYear() - 1)
    else if (selectedPeriod === '5Y') cutoff.setFullYear(latestDate.getFullYear() - 5)

    const cutoffStr = cutoff.toISOString().split('T')[0]
    return sorted.filter((d) => d.date >= cutoffStr)
  }

  useEffect(() => {
    if (!chartContainerRef.current || !data || data.length === 0) return

    const container = chartContainerRef.current
    const filteredData = getFilteredData()
    if (filteredData.length === 0) return

    const handleResize = () => {
      chartRef.current?.applyOptions({ width: container.clientWidth })
    }

    // Initialize Chart
    const chart = createChart(container, {
      layout: {
        background: { type: ColorType.Solid, color: '#040b16' },
        textColor: '#94a3b8',
        fontSize: 11,
        fontFamily: 'var(--font-mono, monospace)',
      },
      grid: {
        vertLines: { color: 'rgba(22, 32, 52, 0.4)' },
        horzLines: { color: 'rgba(22, 32, 52, 0.4)' },
      },
      width: container.clientWidth,
      height: 380,
      timeScale: {
        borderColor: '#162034',
        timeVisible: true,
        rightOffset: 5,
        barSpacing: 6,
      },
      rightPriceScale: {
        borderColor: '#162034',
        autoScale: true,
      },
      crosshair: {
        vertLine: {
          color: '#3b82f6',
          width: 1,
          style: 3, // dashed
          labelBackgroundColor: '#0c1526',
        },
        horzLine: {
          color: '#3b82f6',
          width: 1,
          style: 3, // dashed
          labelBackgroundColor: '#0c1526',
        },
      },
    })
    chartRef.current = chart

    // Add Candlestick Series
    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e',
      downColor: '#f43f5e',
      borderVisible: false,
      wickUpColor: '#22c55e',
      wickDownColor: '#f43f5e',
    })

    const formattedData = filteredData.map((d) => ({
      time: d.date,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    }))

    candlestickSeries.setData(formattedData)

    // Add Volume Histogram Series
    const volumeSeries = chart.addSeries(HistogramSeries, {
      color: '#2563eb',
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: '', // Set overlay mode
    })

    // Position the volume series at the bottom of the chart
    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.8, // Occupies bottom 20%
        bottom: 0,
      },
    })

    const volumeData = formattedData.map((d, index) => ({
      time: d.time,
      value: filteredData[index].volume,
      color: d.close >= d.open ? 'rgba(34, 197, 94, 0.25)' : 'rgba(244, 63, 94, 0.25)',
    }))
    volumeSeries.setData(volumeData)

    // Compute and Add MA 20 Line Series
    if (ma20Active) {
      const ma20Series = chart.addSeries(LineSeries, {
        color: '#f59e0b',
        lineWidth: 2,
        crosshairMarkerVisible: false,
        priceLineVisible: false,
      })
      const ma20Data = computeSMA(formattedData, 20)
      ma20Series.setData(ma20Data)
    }

    // Compute and Add MA 50 Line Series
    if (ma50Active) {
      const ma50Series = chart.addSeries(LineSeries, {
        color: '#a855f7',
        lineWidth: 2,
        crosshairMarkerVisible: false,
        priceLineVisible: false,
      })
      const ma50Data = computeSMA(formattedData, 50)
      ma50Series.setData(ma50Data)
    }

    chart.timeScale().fitContent()
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
      chartRef.current = null
    }
  }, [data, selectedPeriod, ma20Active, ma50Active])

  return (
    <div className="w-full glass rounded-xl border border-border p-4 sm:p-6 space-y-5 shadow-lg bg-card/60 backdrop-blur-md relative overflow-hidden">
      {/* Background glow element */}
      <div className="absolute top-0 right-0 w-80 h-80 bg-brand/5 rounded-full blur-[100px] pointer-events-none -z-10" />

      {/* Chart Toolbar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-2 border-b border-border/40">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-brand animate-pulse" />
          <span className="text-sm font-bold font-display text-textPrimary uppercase tracking-wider">
            Market Price Telemetry
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {/* Period Selector (Before/Above Graph) */}
          <div className="flex items-center bg-elevated/70 border border-border/80 p-0.5 rounded-lg">
            {PERIODS.map((period) => (
              <button
                key={period}
                onClick={() => setSelectedPeriod(period)}
                className={`px-3 py-1 text-[11px] font-mono font-bold rounded transition-all duration-200 ${
                  selectedPeriod === period
                    ? 'bg-brand text-white shadow-md shadow-brand/20 scale-105'
                    : 'text-textSub hover:text-textPrimary hover:bg-border/30'
                }`}
              >
                {period}
              </button>
            ))}
          </div>

          {/* Indicators toggles */}
          <div className="flex items-center gap-2 border-l border-border/50 pl-3">
            <button
              onClick={() => setMa20Active(!ma20Active)}
              className={`px-2.5 py-1 text-[10px] font-bold rounded transition-all duration-200 border ${
                ma20Active
                  ? 'bg-warn-dim border-warn text-warn shadow-inner'
                  : 'border-border/60 text-textMuted hover:border-textSub hover:text-textSub'
              }`}
            >
              MA 20
            </button>
            <button
              onClick={() => setMa50Active(!ma50Active)}
              className={`px-2.5 py-1 text-[10px] font-bold rounded transition-all duration-200 border ${
                ma50Active
                  ? 'bg-purple-dim border-purple text-purple shadow-inner'
                  : 'border-border/60 text-textMuted hover:border-textSub hover:text-textSub'
              }`}
            >
              MA 50
            </button>
          </div>
        </div>
      </div>

      {/* Lightweight Chart Container */}
      <div
        ref={chartContainerRef}
        className="w-full relative min-h-[380px] rounded-lg overflow-hidden border border-border/50 bg-[#040b16]"
      />
    </div>
  )
}
