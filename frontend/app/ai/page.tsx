'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, Cpu, RefreshCw, Database, BookOpen } from 'lucide-react'
import { T, pct } from '@/lib/stockData'
import { aiApi } from '@/lib/api'
import ModelSelector from '@/components/ai/ModelSelector'
import { useModelStore, PROVIDERS } from '@/lib/model-store'

const card = (x = {}) => ({ background: T.card, border: `1px solid ${T.b}`, borderRadius: 10, ...x })

const OFFLINE_STOCKS = [
  { ticker: 'RELIANCE', name: 'Reliance Industries', sector: 'Energy', price: 2847.5, chg: 1.24, pe: 24.5, pb: 2.1, roe: 15.2, composite: 71, qual: 78, mom: 67, val: 63, grw: 71 },
  { ticker: 'HDFCBANK', name: 'HDFC Bank', sector: 'Banking', price: 1742.3, chg: 0.83, pe: 19.2, pb: 2.8, roe: 17.1, composite: 74, qual: 85, mom: 72, val: 76, grw: 74 },
  { ticker: 'TCS', name: 'Tata Consultancy', sector: 'IT', price: 3912.5, chg: -0.45, pe: 28.7, pb: 12.4, roe: 47.2, composite: 58, qual: 92, mom: 61, val: 52, grw: 58 },
  { ticker: 'INFY', name: 'Infosys Ltd', sector: 'IT', price: 1478.9, chg: -0.21, pe: 25.3, pb: 8.9, roe: 33.8, composite: 56, qual: 88, mom: 58, val: 60, grw: 56 },
  { ticker: 'ICICIBANK', name: 'ICICI Bank', sector: 'Banking', price: 1089.8, chg: 2.17, pe: 17.8, pb: 2.9, roe: 17.9, composite: 79, qual: 82, mom: 81, val: 79, grw: 79 },
  { ticker: 'BHARTIARTL', name: 'Bharti Airtel', sector: 'Telecom', price: 1621.3, chg: 1.89, pe: 65.2, pb: 5.8, roe: 9.2, composite: 82, qual: 72, mom: 89, val: 38, grw: 82 },
  { ticker: 'SBIN', name: 'State Bank of India', sector: 'Banking', price: 795.6, chg: 3.12, pe: 11.2, pb: 1.5, roe: 14.2, composite: 71, qual: 71, mom: 73, val: 88, grw: 71 },
]

const QUICK = [
  'Analyze HDFC Bank vs ICICI Bank quality factors with citations',
  'What does the indexed data say about Reliance valuation?',
  'Best large-cap IT stocks for FY26 — growth vs valuations',
  'Explain momentum investing for Indian markets',
  'Nifty 50 sector rotation — current macro regime signal',
]

type RagSource = {
  n?: number
  ref?: string | null
  title?: string | null
  kind?: string | null
  score?: number | null
}

type ChatMessage = {
  role: string
  content: string
  source?: string
  sources?: RagSource[]
  grounded?: boolean
}

function Tag({ children, color = '#a78bfa' }: { children: any; color?: string }) {
  return <span style={{ background: `${color}22`, color, border: `1px solid ${color}44`, borderRadius: 4, padding: '2px 7px', fontSize: 10, fontWeight: 700 }}>{children}</span>
}

function buildOfflineChatReply(q: string) {
  const ql = q.toLowerCase()
  const mentioned = OFFLINE_STOCKS.filter(s => ql.includes(s.ticker.toLowerCase()) || ql.includes(s.name.toLowerCase().split(' ')[0]))
  if (mentioned.length >= 2) {
    const [a, b] = mentioned
    return `Comparing ${a.ticker} vs ${b.ticker} on quantitative factors:\n\n${a.ticker}: Composite ${a.composite} (Quality ${a.qual}, Momentum ${a.mom}, Value ${a.val}) · ROE ${a.roe.toFixed(1)}% · P/E ${a.pe.toFixed(1)}x\n${b.ticker}: Composite ${b.composite} (Quality ${b.qual}, Momentum ${b.mom}, Value ${b.val}) · ROE ${b.roe.toFixed(1)}% · P/E ${b.pe.toFixed(1)}x\n\nOn this data, ${a.composite > b.composite ? a.ticker : b.ticker} screens higher on the blended composite factor, driven primarily by ${a.composite > b.composite ? (a.qual > a.mom ? 'Quality' : 'Momentum') : (b.qual > b.mom ? 'Quality' : 'Momentum')}.\n\n⚠️ Offline rule-based reply (Ollama not reachable). Self-host with Ollama for full LLM responses, free.`
  }
  if (mentioned.length === 1) {
    const s = mentioned[0]
    return `${s.name} (${s.ticker}) — quick data view:\nPrice ₹${s.price.toLocaleString('en-IN')} (${pct(s.chg)}) · Sector: ${s.sector}\nP/E ${s.pe.toFixed(1)}x · P/B ${s.pb.toFixed(1)}x · ROE ${s.roe.toFixed(1)}%\nFactor scores — Momentum ${s.mom} · Quality ${s.qual} · Value ${s.val} · Growth ${s.grw} · Composite ${s.composite}\n\nOpen the Screener or click this stock from the Dashboard for the full AI report.\n\n⚠️ Offline rule-based reply (Ollama not reachable).`
  }
  if (ql.includes('rbi') || ql.includes('repo') || ql.includes('rate')) {
    return `RBI's repo rate currently stands at 5.75%, down from 6.5% a year ago — an easing cycle. Historically, falling rates benefit rate-sensitive sectors: Banking, NBFC, Real Estate, and Auto (financing-driven demand). Check the Macro tab for the full repo rate and CPI trend charts.\n\n⚠️ Offline rule-based reply (Ollama not reachable).`
  }
  if (ql.includes('momentum')) {
    return `Momentum investing ranks stocks by relative price strength over the trailing 12 months (skipping the most recent month to avoid short-term reversal). In the Indian market context, momentum has historically been one of the stronger factors — see the Backtester tab, where the "High Momentum" strategy shows a 22.5% CAGR vs 16.2% for Nifty 50 over the same period.\n\n⚠️ Offline rule-based reply (Ollama not reachable).`
  }
  return `I can discuss specific Nifty stocks (try mentioning a ticker like "HDFCBANK" or "TCS"), RBI policy, or factor investing concepts. Try one of the quick prompts below, or ask about a specific stock or sector.\n\n⚠️ This is an offline rule-based reply because Ollama isn't reachable from this preview. Run this app on your own device with \`ollama serve\` running for full open-source LLM responses — completely free, no API key.`
}

export default function AIChat() {
  const { provider, modelId, getApiKey, getActiveModel } = useModelStore()
  const activeModel = getActiveModel()
  const providerInfo = PROVIDERS[provider]

  const [msgs, setMsgs] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: 'Namaste! I\'m QuantAI — your Indian equity research assistant.\n\nAsk about indexed stocks, fundamentals, factors, sectors, or macro context. I will use the project RAG index first and show citations when matching data is available.',
    },
  ])
  const [inp, setInp] = useState('')
  const [load, setLoad] = useState(false)
  const [showModelPanel, setShowModelPanel] = useState(false)
  const [ragStatus, setRagStatus] = useState<{ documents: number; stock_documents: number } | null>(null)
  const endRef = useRef<HTMLDivElement>(null)
  useEffect(() => endRef.current?.scrollIntoView({ behavior: 'smooth' }), [msgs])
  useEffect(() => {
    aiApi.ragStatus()
      .then(setRagStatus)
      .catch(() => setRagStatus(null))
  }, [])

  async function send() {
    if (!inp.trim() || load) return
    const q = inp.trim()
    setInp('')
    const next = [...msgs, { role: 'user', content: q }]
    setMsgs(next)
    setLoad(true)
    try {
      const d = await aiApi.ask(q, 5)
      setMsgs(p => [...p, {
        role: 'assistant',
        content: d.answer || d.response || d.content,
        source: d.grounded ? 'rag' : (d.source || provider),
        sources: d.sources || [],
        grounded: Boolean(d.grounded),
      }])
    } catch {
      setMsgs(p => [...p, { role: 'assistant', content: buildOfflineChatReply(q), source: 'offline' }])
    }
    setLoad(false)
  }

  return (
    <div style={{ padding: '26px 30px', maxWidth: 860, display: 'flex', flexDirection: 'column', height: 'calc(100vh - 64px)', fontFamily: T.sans }}>
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 22, fontWeight: 700, color: T.text }}>QuantAI Research Assistant</div>
        <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <button
            onClick={() => setShowModelPanel(p => !p)}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              background: `${providerInfo.color}18`, border: `1px solid ${providerInfo.color}50`,
              borderRadius: 8, padding: '5px 12px', cursor: 'pointer', color: providerInfo.color,
              fontSize: 11, fontWeight: 700, fontFamily: T.mono,
            }}
          >
            {provider === 'ollama' ? <Cpu size={11} /> : null}
            {activeModel?.label ?? modelId} · {providerInfo.label}
            <span style={{ fontSize: 9, opacity: 0.7 }}>▼</span>
          </button>
          <span style={{ fontSize: 11, color: T.muted }}>Indian equity specialist</span>
          <span
            style={{
              display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: ragStatus?.documents ? T.green : T.muted,
              border: `1px solid ${ragStatus?.documents ? T.green + '44' : T.b}`, borderRadius: 999, padding: '4px 9px',
              background: ragStatus?.documents ? T.green + '12' : T.el,
            }}
            title="Indexed documents available for grounded answers"
          >
            <Database size={11} />
            {ragStatus ? `${ragStatus.documents} indexed docs` : 'RAG status unavailable'}
          </span>
        </div>
      </div>

      {showModelPanel && (
        <div style={{ background: T.card, border: `1px solid ${T.b}`, borderRadius: 12, marginBottom: 12, overflow: 'hidden' }}>
          <ModelSelector />
        </div>
      )}


      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
        {QUICK.map(p => (
          <button
            key={p}
            onClick={() => setInp(p)}
            style={{ background: T.el, border: `1px solid ${T.b}`, borderRadius: 20, padding: '5px 13px', fontSize: 11, color: T.sub, cursor: 'pointer' }}
          >
            {p}
          </button>
        ))}
      </div>

      <div style={{ flex: 1, overflowY: 'auto', paddingBottom: 8 }}>
        {msgs.map((m, i) => (
          <div key={i} style={{ marginBottom: 14, display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start' }}>
            <div
              style={{
                maxWidth: '82%',
                background: m.role === 'user' ? T.blue : T.el,
                border: `1px solid ${m.role === 'user' ? T.blue + '66' : T.b}`,
                borderRadius: m.role === 'user' ? '12px 12px 3px 12px' : '12px 12px 12px 3px',
                padding: '11px 15px', fontSize: 13, color: T.text, lineHeight: 1.75, whiteSpace: 'pre-wrap',
              }}
            >
              {m.role === 'assistant' && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                  <span style={{ fontSize: 10, color: T.blue, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>QuantAI</span>
                  {m.source && <Tag color={m.source === 'offline' ? T.amber : m.source === 'rag' ? T.blue : T.green}>{m.source === 'offline' ? 'Offline' : m.source === 'rag' ? 'Grounded' : m.source}</Tag>}
                </div>
              )}
              {m.content}
              {m.sources && m.sources.length > 0 && (
                <div style={{ marginTop: 12, paddingTop: 10, borderTop: `1px solid ${T.b}`, display: 'grid', gap: 7 }}>
                  {m.sources.map((s, idx) => (
                    <div
                      key={`${s.ref || s.title || idx}`}
                      style={{
                        display: 'flex', alignItems: 'flex-start', gap: 8,
                        color: T.sub, fontSize: 11, lineHeight: 1.45,
                      }}
                    >
                      <BookOpen size={13} style={{ color: T.blue, marginTop: 1, flexShrink: 0 }} />
                      <span>
                        <strong style={{ color: T.text }}>[{s.n ?? idx + 1}] {s.title || s.ref || 'Indexed source'}</strong>
                        {s.kind ? <span> · {s.kind}</span> : null}
                        {typeof s.score === 'number' ? <span> · score {s.score.toFixed(2)}</span> : null}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {load && (
          <div
            style={{
              display: 'flex', alignItems: 'center', gap: 8, padding: '11px 15px',
              background: T.el, border: `1px solid ${T.b}`, borderRadius: 12,
              width: 'fit-content', fontSize: 12, color: T.muted,
            }}
          >
            <span style={{ fontSize: 10, color: T.blue, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', marginRight: 4 }}>QuantAI</span>
            <RefreshCw size={12} style={{ animation: 'spin 1s linear infinite' }} /> Thinking…
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div style={{ display: 'flex', gap: 10, marginTop: 12 }}>
        <input
          value={inp}
          onChange={e => setInp(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
          placeholder="Ask about Indian stocks, sectors, macro factors, quant strategies…"
          style={{
            flex: 1, background: T.el, border: `1px solid ${T.bhi}`, borderRadius: 9,
            padding: '11px 15px', fontSize: 13, color: T.text, outline: 'none', fontFamily: T.sans,
          }}
        />
        <button
          onClick={send}
          disabled={load || !inp.trim()}
          style={{
            background: T.blue, border: 'none', borderRadius: 9, padding: '11px 18px',
            cursor: load || !inp.trim() ? 'not-allowed' : 'pointer',
            opacity: load || !inp.trim() ? 0.5 : 1, display: 'flex', alignItems: 'center',
          }}
        >
          <Send size={16} color="#fff" />
        </button>
      </div>
    </div>
  )
}
