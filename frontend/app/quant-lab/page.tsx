'use client'

import { useState } from 'react'
import { Database, Sparkles } from 'lucide-react'
import { T } from '@/lib/stockData'

const card = (x = {}) => ({ background: T.card, border: `1px solid ${T.b}`, borderRadius: 10, ...x })

export default function QuantLabPage() {
  return (
    <div style={{ padding: '26px 30px', maxWidth: 1200, fontFamily: T.sans }}>
      <div style={{ marginBottom: 22 }}>
        <div style={{ fontSize: 22, fontWeight: 700, color: T.text }}>Quant Lab</div>
        <div style={{ fontSize: 13, color: T.sub, marginTop: 3 }}>
          Custom factor models · Strategy sandbox · Quant research
        </div>
      </div>

      <div style={card({ padding: '40px', textAlign: 'center' as const })}>
        <Sparkles size={40} color={T.muted} style={{ marginBottom: 16, opacity: 0.4 }} />
        <div style={{ fontSize: 16, fontWeight: 600, color: T.text, marginBottom: 8 }}>
          Coming Soon
        </div>
        <div style={{ fontSize: 13, color: T.sub, maxWidth: 400, margin: '0 auto', lineHeight: 1.7 }}>
          Build and test custom factor models, run multi-factor regressions,
          and backtest proprietary strategies — all on Indian market data.
        </div>
        <div style={{ marginTop: 20, display: 'flex', gap: 8, justifyContent: 'center', flexWrap: 'wrap' }}>
          {['Factor Builder', 'Portfolio Optimization', 'Risk Decomposition', 'Monte Carlo Simulation'].map(f => (
            <span key={f} style={{
              background: `${T.blue}22`, color: T.blue,
              border: `1px solid ${T.blue}44`, borderRadius: 4,
              padding: '4px 10px', fontSize: 11, fontWeight: 600,
            }}>{f}</span>
          ))}
        </div>
      </div>
    </div>
  )
}
