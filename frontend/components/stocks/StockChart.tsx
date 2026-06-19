// /frontend/components/stocks/StockChart.tsx
'use client'

import { useEffect, useRef, useState } from 'react'
import { createChart, ColorType, CandlestickSeries } from 'lightweight-charts'

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

const PERIODS = [
  { label: '1M', value: '1mo' },
  { label: '3M', value: '3mo' },
  { label: '6M', value: '6mo' },
  { label: '1Y', value: '1y' },
  { label: '5Y', value: '5y' },
]

export default function StockChart({ data }: StockChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<any>(null)
  const seriesRef = useRef<any>(null)
  const [ma20Active, setMa20Active] = useState(false)
  const [ma50Active, setMa50Active] = useState(false)

  // simple moving average helper
  const computeSMA = (dataPoints: ChartDataPoint[], period: number) => {
    const sma: any[] = []
    for (let i = 0; i < dataPoints.length; i++) {
      if (i < period - 1) {
        continue
      }
      let sum = 0
      for (let j = 0; j < period; j++) {
        sum += dataPoints[i - j].close
      }
      sma.push({
        time: dataPoints[i].date,
        value: sum / period,
      })
    }
    return sma
  }

  useEffect(() => {
    if (!chartContainerRef.current || !data || data.length === 0) return

    const handleResize = () => {
      chartRef.current?.applyOptions({ width: chartContainerRef.current?.clientWidth })
    }

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#080f1e' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: 'rgba(22, 32, 52, 0.7)' },
        horzLines: { color: 'rgba(22, 32, 52, 0.7)' },
      },
      width: chartContainerRef.current.clientWidth,
      height: 380,
      timeScale: {
        borderColor: '#162034',
        timeVisible: true,
      },
    })
    chartRef.current = chart

    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e',
      downColor: '#f43f5e',
      borderVisible: false,
      wickUpColor: '#22c55e',
      wickDownColor: '#f43f5e',
    })
    seriesRef.current = candlestickSeries

    const formattedData = [...data]
      .sort((a, b) => a.date.localeCompare(b.date))
      .map((d) => ({
        time: d.date,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      }))

    candlestickSeries.setData(formattedData)
    chart.timeScale().fitContent()

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
      chartRef.current = null
    }
  }, [data])

  return (
    <div className="w-full bg-card border border-border p-4 rounded-xl space-y-4">
      {/* Chart Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="text-sm font-semibold font-display text-textPrimary">Interactive Price Chart</div>
        <div className="flex items-center gap-2">
          {/* MAs toggles */}
          <button
            onClick={() => setMa20Active(!ma20Active)}
            className={`px-2.5 py-1 text-xs rounded transition-all border ${
              ma20Active ? 'bg-warn/10 border-warn text-warn' : 'border-border text-textSub'
            }`}
          >
            MA 20
          </button>
          <button
            onClick={() => setMa50Active(!ma50Active)}
            className={`px-2.5 py-1 text-xs rounded transition-all border ${
              ma50Active ? 'bg-purple/10 border-purple text-purple' : 'border-border text-textSub'
            }`}
          >
            MA 50
          </button>
        </div>
      </div>

      <div ref={chartContainerRef} className="w-full relative min-h-[380px] rounded-lg overflow-hidden border border-border" />
    </div>
  )
}
