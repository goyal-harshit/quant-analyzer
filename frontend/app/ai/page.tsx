'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, MessageSquare, Cpu, RefreshCw } from 'lucide-react'
import { STOCKS, MACRO, BT_STATS, T, pct } from '@/lib/stockData'
import { aiApi } from '@/lib/api'

const card = (x = {}) => ({ background: T.card, border: `1px solid ${T.b}`, borderRadius: 10, ...x })
const sc = v => v >= 70 ? T.green : v >= 45 ? T.amber : T.red

function Tag({ children, color = '#a78bfa' }) {
  return <span style={{ background: `${color}22`, color, border: `1px solid ${color}44`, borderRadius: 4, padding: '2px 7px', fontSize: 10, fontWeight: 700 }}>{children}</span>
}

const QUICK = [
  'Analyze HDFC Bank vs ICICI Bank quality factors',
  'Impact of RBI rate cuts on NBFC sector',
  'Best large-cap IT stocks for FY26 — growth vs valuations',
  'Explain momentum investing for Indian markets',
  'Nifty 50 sector rotation — current macro regime signal',
]

function buildOfflineChatReply(q) {
  const ql = q.toLowerCase()
  const mentioned = STOCKS.filter(s => ql.includes(s.ticker.toLowerCase()) || ql.includes(s.name.toLowerCase().split(' ')[0]))
  if (mentioned.length >= 2) {
    const [a, b] = mentioned
    return `Comparing ${a.ticker} vs ${b.ticker} on quantitative factors:\n\n${a.ticker}: Composite ${a.composite} (Quality ${a.qual}, Momentum ${a.mom}, Value ${a.val}) · ROE ${a.roe.toFixed(1)}% · P/E ${a.pe.toFixed(1)}x\n${b.ticker}: Composite ${b.composite} (Quality ${b.qual}, Momentum ${b.mom}, Value ${b.val}) · ROE ${b.roe.toFixed(1)}% · P/E ${b.pe.toFixed(1)}x\n\nOn this data, ${a.composite > b.composite ? a.ticker : b.ticker} screens higher on the blended composite factor, driven primarily by ${a.composite > b.composite ? (a.qual > a.mom ? 'Quality' : 'Momentum') : (b.qual > b.mom ? 'Quality' : 'Momentum')}.\n\n⚠️ Offline rule-based reply (Ollama not reachable). Self-host with Ollama for full LLM responses, free.`
  }
  if (mentioned.length === 1) {
    const s = mentioned[0]
    return `${s.name} (${s.ticker}) — quick data view:\nPrice ₹${s.price.toLocaleString('en-IN')} (${pct(s.chg)}) · Sector: ${s.sector}\nP/E ${s.pe.toFixed(1)}x · P/B ${s.pb.toFixed(1)}x · ROE ${s.roe.toFixed(1)}%\nFactor scores — Momentum ${s.mom} · Quality ${s.qual} · Value ${s.val} · Growth ${s.grw} · Composite ${s.composite}\n\nOpen the Screener or click this stock from the Dashboard for the full AI report.\n\n⚠️ Offline rule-based reply (Ollama not reachable).`
  }
  if (ql.includes('rbi') || ql.includes('repo') || ql.includes('rate')) {
    return `RBI's repo rate currently stands at ${MACRO.repo[MACRO.repo.length - 1].v}%, down from 6.5% a year ago — an easing cycle. Historically, falling rates benefit rate-sensitive sectors: Banking, NBFC, Real Estate, and Auto (financing-driven demand). Check the Macro tab for the full repo rate and CPI trend charts.\n\n⚠️ Offline rule-based reply (Ollama not reachable).`
  }
  if (ql.includes('momentum')) {
    return `Momentum investing ranks stocks by relative price strength over the trailing 12 months (skipping the most recent month to avoid short-term reversal). In the Indian market context, momentum has historically been one of the stronger factors — see the Backtester tab, where the "High Momentum" strategy shows a ${BT_STATS['High Momentum'].cagr}% CAGR vs ${BT_STATS['Nifty 50'].cagr}% for Nifty 50 over the same period.\n\n⚠️ Offline rule-based reply (Ollama not reachable).`
  }
  return `I can discuss specific Nifty stocks (try mentioning a ticker like "HDFCBANK" or "TCS"), RBI policy, or factor investing concepts. Try one of the quick prompts below, or ask about a specific stock or sector.\n\n⚠️ This is an offline rule-based reply because Ollama isn't reachable from this preview. Run this app on your own device with \`ollama serve\` running for full open-source LLM responses — completely free, no API key.`
}

export default function AIChat() {
  const [msgs, setMsgs] = useState<{ role: string; content: string; source?: string }[]>([
    {
      role: 'assistant',
      content: '\u{1F1EE}\u{1F1F3} Namaste! I\'m QuantAI — running on a 100% free, open-source, self-hosted LLM (Ollama). No API keys, no payment, ever.\n\nI can help you:\n• Analyze Nifty 500 stocks and compare fundamentals\n• Discuss RBI policy impacts on sectors\n• Explain quantitative factors and factor investing\n• Research any NSE/BSE listed company\n• Interpret macro data for investment context\n\nWhat would you like to explore today?',
    },
  ])
  const [inp, setInp] = useState('')
  const [load, setLoad] = useState(false)
  const endRef = useRef(null)
  useEffect(() => endRef.current?.scrollIntoView({ behavior: 'smooth' }), [msgs])

  async function send() {
    if (!inp.trim() || load) return
    const q = inp.trim()
    setInp('')
    const next = [...msgs, { role: 'user', content: q }]
    setMsgs(next)
    setLoad(true)
    try {
      const apiMsgs = next.filter((m, i) => !(m.role === 'assistant' && i === 0)).map(m => ({ role: m.role, content: m.content }))
      const d = await aiApi.chat({ messages: apiMsgs })
      setMsgs(p => [...p, { role: 'assistant', content: d.response || d.content, source: 'ollama' }])
    } catch {
      setMsgs(p => [...p, { role: 'assistant', content: buildOfflineChatReply(q), source: 'offline' }])
    }
    setLoad(false)
  }

  return (
    <div style={{ padding: '26px 30px', maxWidth: 860, display: 'flex', flexDirection: 'column', height: 'calc(100vh - 0px)', fontFamily: T.sans }}>
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 22, fontWeight: 700, color: T.text }}>QuantAI Research Assistant</div>
        <div style={{ fontSize: 13, color: T.sub, marginTop: 3, display: 'flex', alignItems: 'center', gap: 6 }}>
          <Cpu size={12} color={T.green} /> Powered by Ollama (free, open-source, self-hosted) · Indian equity specialist
        </div>
      </div>

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
                  {m.source && <Tag color={m.source === 'ollama' ? T.green : T.amber}>{m.source === 'ollama' ? 'Ollama' : 'Offline'}</Tag>}
                </div>
              )}
              {m.content}
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
