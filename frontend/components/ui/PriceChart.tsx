'use client'

import { useEffect, useRef } from 'react'
import { createChart, ColorType, CandlestickSeries } from 'lightweight-charts'

interface PriceChartProps {
  data: Array<{
    date: string
    open: number
    high: number
    low: number
    close: number
    volume: number
  }>
}

export default function PriceChart({ data }: PriceChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!chartContainerRef.current || !data || data.length === 0) return

    const handleResize = () => {
      chart.applyOptions({ width: chartContainerRef.current?.clientWidth })
    }

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: 'rgba(30, 45, 74, 0.3)' },
        horzLines: { color: 'rgba(30, 45, 74, 0.3)' },
      },
      width: chartContainerRef.current.clientWidth,
      height: 350,
      timeScale: {
        borderColor: '#1e2d4a',
      },
    })

    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e',
      downColor: '#f43f5e',
      borderVisible: false,
      wickUpColor: '#22c55e',
      wickDownColor: '#f43f5e',
    })

    // Format data for lightweight-charts
    const formattedData = data.map((d) => ({
      time: d.date,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    })).sort((a, b) => a.time.localeCompare(b.time))

    candlestickSeries.setData(formattedData)
    chart.timeScale().fitContent()

    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
    }
  }, [data])

  return (
    <div className="w-full relative glass p-4 rounded-xl">
      <div className="text-xs font-semibold text-textSub uppercase tracking-wider mb-4">Price History</div>
      <div ref={chartContainerRef} className="w-full" />
    </div>
  )
}
