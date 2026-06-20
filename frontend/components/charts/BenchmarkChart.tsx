// /frontend/components/charts/BenchmarkChart.tsx
'use client'

import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from 'recharts'
import Card from '../ui/Card'

interface PerformanceDataPoint {
  date: string
  portfolio?: number
  watchlist?: number
  benchmark: number
}

interface BenchmarkChartProps {
  data: PerformanceDataPoint[]
  benchmarkName?: string
  mode?: 'portfolio' | 'watchlist'
}

export default function BenchmarkChart({
  data, benchmarkName = 'Nifty 50', mode = 'portfolio'
}: BenchmarkChartProps) {
  if (!data || data.length === 0) {
    return (
      <Card padding="md">
        <div className="text-center text-textMuted py-12">No performance telemetry available.</div>
      </Card>
    )
  }

  return (
    <Card padding="md">
      <Card.Header 
        title="Performance vs Benchmark" 
        subtitle="Growth of ₹100 invested at period start" 
      />
      <div className="w-full h-80">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 8, left: -20, bottom: 4 }}>
            <CartesianGrid stroke="rgba(22, 32, 52, 0.5)" strokeDasharray="3 3" />
            <XAxis 
              dataKey="date" 
              tick={{ fill: '#475569', fontSize: 10 }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis 
              tick={{ fill: '#475569', fontSize: 10, fontFamily: 'monospace' }}
              tickFormatter={(v) => `₹${v}`}
              tickLine={false}
              axisLine={false}
              domain={['auto', 'auto']}
            />
            <Tooltip
              contentStyle={{ background: '#0c1526', borderColor: '#1f3055', borderRadius: 8 }}
              labelStyle={{ color: '#94a3b8', fontSize: 11 }}
              itemStyle={{ fontSize: 12 }}
            />
            <Legend verticalAlign="top" height={36} iconType="circle" />
            
            {mode === 'portfolio' && (
              <Line 
                name="Portfolio" 
                type="monotone" 
                dataKey="portfolio" 
                stroke="#3b82f6" 
                strokeWidth={2.5} 
                dot={false}
                activeDot={{ r: 6 }}
              />
            )}

            {mode === 'watchlist' && (
              <Line 
                name="Watchlist Index" 
                type="monotone" 
                dataKey="watchlist" 
                stroke="#a855f7" 
                strokeWidth={2.5} 
                dot={false}
                activeDot={{ r: 6 }}
              />
            )}

            <Line 
              name={benchmarkName} 
              type="monotone" 
              dataKey="benchmark" 
              stroke="#475569" 
              strokeWidth={1.5} 
              strokeDasharray="4 4"
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}
