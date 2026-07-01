'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { RefreshCw } from 'lucide-react'
import { dashboardApi } from '@/lib/api'

const RAW = [
  ['RELIANCE',  'Reliance Industries',  2891.40, 0.83],
  ['HDFCBANK',  'HDFC Bank',            1712.20,-0.21],
  ['TCS',       'Tata Consultancy',     3945.80, 1.14],
  ['INFY',      'Infosys',              1621.55, 0.68],
  ['ICICIBANK', 'ICICI Bank',           1298.35, 0.92],
  ['HINDUNILVR','Hindustan Unilever',   2341.90,-0.34],
  ['BHARTIARTL','Bharti Airtel',        1789.60, 1.52],
  ['BAJFINANCE','Bajaj Finance',        7345.25, 2.14],
  ['KOTAKBANK', 'Kotak Mahindra',       1978.40, 0.45],
  ['SBIN',      'State Bank of India',   812.70,-0.78],
  ['WIPRO',     'Wipro',                542.35,  0.33],
  ['TITAN',     'Titan Company',        3456.80, 1.21],
  ['ITC',       'ITC Limited',          468.45, -0.12],
  ['LT',        'Larsen & Toubro',      3678.90, 0.89],
  ['ASIANPAINT','Asian Paints',         2890.15,-0.56],
  ['MARUTI',    'Maruti Suzuki',        12890.40,0.77],
  ['AXISBANK',  'Axis Bank',            1123.70, 1.03],
  ['HCLTECH',   'HCL Technologies',     1798.25, 0.41],
  ['SUNPHARMA', 'Sun Pharma',           1567.80, 0.95],
  ['TATAMOTORS','Tata Motors',           789.35, 2.34],
]
const SCREENER_DATA = [
  {t:'TCS',n:'Tata Consultancy',s:'IT Services',p:3945.80,c:1.14,pe:27.4,mom:87,qual:78,comp:84},
  {t:'INFY',n:'Infosys',s:'IT Services',p:1621.55,c:0.68,pe:23.8,mom:82,qual:74,comp:80},
  {t:'HCLTECH',n:'HCL Technologies',s:'IT Services',p:1798.25,c:0.41,pe:21.2,mom:76,qual:81,comp:79},
  {t:'BHARTIARTL',n:'Bharti Airtel',s:'Telecom',p:1789.60,c:1.52,pe:38.9,mom:91,qual:65,comp:77},
  {t:'BAJFINANCE',n:'Bajaj Finance',s:'NBFC',p:7345.25,c:2.14,pe:31.4,mom:88,qual:72,comp:82},
  {t:'RELIANCE',n:'Reliance Industries',s:'Energy',p:2891.40,c:0.83,pe:28.1,mom:71,qual:69,comp:71},
]

const SS = `
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#010810;--card:#080f1e;--elevated:#0c1526;--border:#162034;--border-hi:#1f3055;--brand:#3b82f6;--brand-dim:rgba(59,130,246,0.12);--cyan:#06b6d4;--cyan-dim:rgba(6,182,212,0.1);--success:#22c55e;--danger:#f43f5e;--warn:#f59e0b;--purple:#a855f7;--text-primary:#e2e8f0;--text-sub:#94a3b8;--text-muted:#475569;--font-display:'Space Grotesk',sans-serif;--font-body:'Inter',sans-serif;--font-mono:'JetBrains Mono',monospace}
body{background:var(--bg);color:var(--text-primary);font-family:var(--font-body);overflow-x:hidden;line-height:1.6}
nav{position:fixed;top:0;left:0;right:0;z-index:100;display:flex;align-items:center;justify-content:space-between;padding:0 2.5rem;height:64px;background:rgba(1,8,16,0.85);backdrop-filter:blur(16px);border-bottom:1px solid var(--border)}
.nav-logo{display:flex;align-items:center;gap:10px;font-family:var(--font-display);font-weight:700;font-size:1.25rem;color:#fff;text-decoration:none}
.logo-icon{width:32px;height:32px;border-radius:8px;background:var(--brand);display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:700;color:#fff;font-family:var(--font-mono)}
.nav-links{display:flex;gap:2rem}.nav-links a{color:var(--text-sub);text-decoration:none;font-size:.875rem;font-weight:500;transition:color .2s}.nav-links a:hover{color:var(--text-primary)}
.btn-nav{background:var(--brand);color:#fff;border:none;cursor:pointer;padding:.5rem 1.25rem;border-radius:8px;font-size:.875rem;font-weight:600;font-family:var(--font-body);transition:opacity .2s}.btn-nav:hover{opacity:.85}
.hero{padding:10rem 2.5rem 6rem;max-width:1200px;margin:0 auto;display:grid;grid-template-columns:1fr 1fr;gap:5rem;align-items:center}
.hero-badge{display:inline-flex;align-items:center;gap:8px;background:var(--brand-dim);border:1px solid rgba(59,130,246,.3);padding:6px 14px;border-radius:100px;margin-bottom:1.5rem;font-size:.75rem;font-weight:600;color:var(--brand);letter-spacing:.05em;text-transform:uppercase}
.pulse-dot{width:6px;height:6px;border-radius:50%;background:var(--brand);animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
h1{font-family:var(--font-display);font-weight:700;font-size:clamp(2.5rem,4vw,3.5rem);line-height:1.1;color:#fff;margin-bottom:1.25rem;letter-spacing:-.02em}
h1 span{color:var(--brand)}
.hero-sub{font-size:1.1rem;color:var(--text-sub);line-height:1.7;max-width:520px;margin-bottom:2.5rem}
.hero-actions{display:flex;gap:1rem;flex-wrap:wrap}
.btn-primary{background:var(--brand);color:#fff;border:none;cursor:pointer;padding:.875rem 2rem;border-radius:10px;font-size:1rem;font-weight:600;font-family:var(--font-body);transition:all .2s;text-decoration:none;display:inline-flex;align-items:center;gap:8px}
.btn-primary:hover{opacity:.9;transform:translateY(-1px)}
.btn-outline{background:transparent;color:var(--text-primary);border:1px solid var(--border-hi);cursor:pointer;padding:.875rem 2rem;border-radius:10px;font-size:1rem;font-weight:500;font-family:var(--font-body);transition:all .2s;text-decoration:none;display:inline-flex;align-items:center;gap:8px}
.btn-outline:hover{border-color:var(--brand);color:var(--brand)}
.ticker-stream{background:var(--card);border:1px solid var(--border);border-radius:16px;overflow:hidden;height:500px;position:relative}
.stream-header{padding:1rem 1.25rem;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;background:var(--elevated)}
.stream-title{font-family:var(--font-display);font-size:.875rem;font-weight:600;color:var(--text-primary);display:flex;align-items:center;gap:8px}
.live-badge{background:rgba(34,197,94,.15);border:1px solid rgba(34,197,94,.3);color:var(--success);font-size:.65rem;font-weight:700;padding:2px 8px;border-radius:100px;letter-spacing:.08em;text-transform:uppercase}
.stream-body{overflow:hidden;height:calc(100% - 54px)}
.stream-list{animation:scrollUp 24s linear infinite}
@keyframes scrollUp{0%{transform:translateY(0)}100%{transform:translateY(-50%)}}
.stream-item{display:flex;align-items:center;justify-content:space-between;padding:.7rem 1.25rem;border-bottom:1px solid var(--border);transition:background .2s}
.stream-item:hover{background:var(--elevated)}
.si-ticker{font-family:var(--font-mono);font-size:.8rem;font-weight:600;color:var(--brand);min-width:100px}
.si-name{font-size:.75rem;color:var(--text-muted);flex:1}
.si-price{font-family:var(--font-mono);font-size:.875rem;font-weight:600;color:var(--text-primary)}
.si-chg{font-family:var(--font-mono);font-size:.75rem;font-weight:600;min-width:60px;text-align:right}
.pos{color:var(--success)}.neg{color:var(--danger)}
.stats-bar{border-top:1px solid var(--border);border-bottom:1px solid var(--border);background:var(--card)}
.stats-inner{max-width:1200px;margin:0 auto;display:grid;grid-template-columns:repeat(4,1fr);padding:2.5rem}
.stat-item{text-align:center;padding:1rem}
.stat-num{font-family:var(--font-display);font-size:2.5rem;font-weight:700;color:#fff;letter-spacing:-.03em;line-height:1}
.stat-num span{color:var(--brand)}
.stat-label{font-size:.875rem;color:var(--text-sub);margin-top:.5rem;font-weight:500}
.section{max-width:1200px;margin:0 auto;padding:6rem 2.5rem}
.section-eyebrow{font-size:.75rem;font-weight:600;color:var(--brand);letter-spacing:.1em;text-transform:uppercase;margin-bottom:1rem}
.section-title{font-family:var(--font-display);font-weight:700;font-size:clamp(1.75rem,3vw,2.5rem);color:#fff;letter-spacing:-.02em;line-height:1.2;margin-bottom:1rem}
.section-sub{font-size:1.05rem;color:var(--text-sub);max-width:560px;line-height:1.7;margin-bottom:3.5rem}
.features-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:1.25rem}
.feature-card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:1.75rem;transition:border-color .2s}
.feature-card:hover{border-color:var(--border-hi)}
.fc-icon{width:44px;height:44px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1.25rem;margin-bottom:1.25rem}
.fc-icon.blue{background:var(--brand-dim)}.fc-icon.cyan{background:var(--cyan-dim)}.fc-icon.green{background:rgba(34,197,94,.1)}.fc-icon.purple{background:rgba(168,85,247,.1)}.fc-icon.warn{background:rgba(245,158,11,.1)}.fc-icon.red{background:rgba(244,63,94,.1)}
.fc-title{font-family:var(--font-display);font-size:1rem;font-weight:600;color:var(--text-primary);margin-bottom:.5rem}
.fc-desc{font-size:.875rem;color:var(--text-sub);line-height:1.6}
.dash-preview-wrap{background:var(--card);border:1px solid var(--border);border-radius:16px;overflow:hidden}
.dash-bar{background:var(--elevated);padding:.875rem 1.25rem;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:1rem}
.dash-dots{display:flex;gap:6px}.dot{width:10px;height:10px;border-radius:50%}.dot-r{background:#f43f5e}.dot-y{background:#f59e0b}.dot-g{background:#22c55e}
.dash-url{flex:1;background:var(--border);border-radius:6px;padding:4px 12px;font-size:.75rem;font-family:var(--font-mono);color:var(--text-sub)}
.dash-content{display:flex;height:500px}
.dash-sidebar{width:56px;background:var(--elevated);border-right:1px solid var(--border);display:flex;flex-direction:column;align-items:center;padding:1rem 0;gap:1.5rem}
.sb-item{width:36px;height:36px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:1rem;cursor:pointer;transition:background .2s}
.sb-item.active{background:var(--brand-dim)}.sb-item:hover{background:var(--border)}
.dash-main{flex:1;overflow:hidden;background:var(--bg)}
.dash-header{padding:1rem 1.5rem;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;background:var(--card)}
.dh-title{font-family:var(--font-display);font-size:1rem;font-weight:700;color:#fff}
.dh-sub{font-size:.75rem;color:var(--text-muted)}
.dash-body{padding:1.25rem;display:flex;flex-direction:column;gap:1rem;overflow:hidden}
.metric-row{display:grid;grid-template-columns:repeat(4,1fr);gap:.75rem}
.metric-card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:.875rem 1rem}
.mc-label{font-size:.65rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:.08em;margin-bottom:.35rem}
.mc-value{font-family:var(--font-mono);font-size:1.1rem;font-weight:700;color:var(--text-primary)}
.mc-change{font-family:var(--font-mono);font-size:.7rem;font-weight:600;margin-top:.2rem}
.factor-section{display:grid;grid-template-columns:2fr 1fr;gap:.75rem}
.factor-chart-card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:1rem}
.fcc-title{font-size:.8rem;font-weight:600;color:var(--text-primary);margin-bottom:.75rem}
.chart-bars{display:flex;flex-direction:column;gap:.5rem}
.bar-item{display:flex;align-items:center;gap:.75rem}
.bi-label{font-size:.7rem;color:var(--text-sub);min-width:80px}
.bi-track{flex:1;height:6px;background:var(--border);border-radius:3px;overflow:hidden}
.bi-fill{height:100%;border-radius:3px;transition:width 1s ease}
.bi-val{font-family:var(--font-mono);font-size:.7rem;font-weight:600;min-width:35px;text-align:right}
.signals-card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:1rem}
.signal-grid{display:grid;grid-template-columns:1fr 1fr;gap:.5rem}
.signal-chip{border-radius:8px;padding:.5rem .75rem;border:1px solid var(--border)}
.sc-name{font-size:.6rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:.06em}
.sc-val{font-family:var(--font-mono);font-size:1rem;font-weight:700;margin-top:2px}
.ai-section{display:grid;grid-template-columns:1fr 1fr;gap:4rem;align-items:center}
.ai-chat-mock{background:var(--card);border:1px solid var(--border);border-radius:16px;overflow:hidden}
.chat-header{background:var(--elevated);padding:1rem 1.25rem;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:10px}
.ai-avatar{width:30px;height:30px;border-radius:8px;background:var(--brand);display:flex;align-items:center;justify-content:center;font-size:.75rem;font-weight:700;color:#fff;font-family:var(--font-mono)}
.chat-name{font-size:.875rem;font-weight:600;color:var(--text-primary)}
.chat-status{font-size:.7rem;color:var(--success);display:flex;align-items:center;gap:4px}
.chat-body{padding:1.25rem;display:flex;flex-direction:column;gap:1rem}
.chat-msg{max-width:85%}
.cm-user{align-self:flex-end}
.cm-bubble{padding:.75rem 1rem;border-radius:12px;font-size:.8125rem;line-height:1.5}
.cm-user .cm-bubble{background:var(--brand);color:#fff;border-bottom-right-radius:4px}
.cm-ai .cm-bubble{background:var(--elevated);color:var(--text-primary);border-bottom-left-radius:4px;border:1px solid var(--border)}
.cm-label{font-size:.65rem;color:var(--text-muted);margin-bottom:4px}
.cm-user .cm-label{text-align:right}
.chat-typing{display:flex;gap:4px;padding:.5rem 0}
.typing-dot{width:6px;height:6px;border-radius:50%;background:var(--text-muted);animation:bounce 1.4s infinite}
.typing-dot:nth-child(2){animation-delay:.2s}.typing-dot:nth-child(3){animation-delay:.4s}
@keyframes bounce{0%,80%,100%{transform:translateY(0)}40%{transform:translateY(-6px)}}
.screener-section{background:var(--card);border:1px solid var(--border);border-radius:16px;overflow:hidden}
.sc-header{padding:1.25rem 1.5rem;border-bottom:1px solid var(--border);background:var(--elevated);display:flex;align-items:center;justify-content:space-between}
.sc-h-left{display:flex;align-items:center;gap:10px}
.sc-h-title{font-family:var(--font-display);font-size:.9375rem;font-weight:700;color:var(--text-primary)}
.sc-h-count{font-size:.75rem;color:var(--text-muted);background:var(--border);padding:3px 10px;border-radius:100px;font-family:var(--font-mono)}
.filter-chips{display:flex;gap:.5rem}
.chip{padding:4px 12px;border-radius:100px;font-size:.7rem;font-weight:600;border:1px solid var(--border);color:var(--text-sub);cursor:pointer;transition:all .2s}
.chip.active{background:var(--brand-dim);border-color:rgba(59,130,246,.4);color:var(--brand)}
.sc-table{width:100%}
.sc-table th{font-size:.7rem;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:.08em;padding:.875rem 1.5rem;border-bottom:1px solid var(--border);text-align:left;background:var(--elevated)}
.sc-table th.r{text-align:right}
.sc-table td{padding:.875rem 1.5rem;border-bottom:1px solid rgba(22,32,52,.6)}
.sc-table tr:last-child td{border-bottom:none}
.sc-table tr:hover td{background:var(--elevated)}
.td-ticker{font-family:var(--font-mono);font-size:.8125rem;font-weight:600;color:var(--brand)}
.td-name{font-size:.8125rem;color:var(--text-primary)}
.td-sector{font-size:.7rem;color:var(--text-muted)}
.td-right{text-align:right;font-family:var(--font-mono);font-size:.8125rem}
.score-pill{display:inline-flex;align-items:center;justify-content:center;width:38px;height:22px;border-radius:4px;font-family:var(--font-mono);font-size:.7rem;font-weight:700}
.score-high{background:rgba(34,197,94,.15);color:var(--success)}
.score-mid{background:rgba(245,158,11,.15);color:var(--warn)}
.score-low{background:rgba(244,63,94,.15);color:var(--danger)}
.tech-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:1rem}
.tech-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:1.5rem}
.tc-layer{font-size:.7rem;font-weight:600;color:var(--brand);text-transform:uppercase;letter-spacing:.1em;margin-bottom:.75rem}
.tc-title{font-family:var(--font-display);font-size:1rem;font-weight:600;color:var(--text-primary);margin-bottom:.5rem}
.tc-desc{font-size:.8125rem;color:var(--text-sub);line-height:1.6;margin-bottom:1rem}
.tech-tags{display:flex;flex-wrap:wrap;gap:.5rem}
.tech-tag{font-size:.7rem;font-weight:500;font-family:var(--font-mono);padding:3px 10px;border-radius:4px;background:var(--elevated);border:1px solid var(--border);color:var(--text-muted)}
.sep{height:1px;background:var(--border)}
.cta-section{text-align:center;padding:8rem 2.5rem;background:var(--card);border-top:1px solid var(--border);border-bottom:1px solid var(--border)}
.cta-inner{max-width:640px;margin:0 auto}
.cta-title{font-family:var(--font-display);font-size:clamp(2rem,4vw,3rem);font-weight:700;color:#fff;letter-spacing:-.02em;margin-bottom:1rem}
.cta-sub{color:var(--text-sub);font-size:1.1rem;margin-bottom:2.5rem}
.cta-actions{display:flex;gap:1rem;justify-content:center;flex-wrap:wrap}
footer{padding:2rem 2.5rem;display:flex;align-items:center;justify-content:space-between;max-width:1200px;margin:0 auto}
.footer-copy{font-size:.8125rem;color:var(--text-muted)}
.footer-links{display:flex;gap:1.5rem}
.footer-links a{font-size:.8125rem;color:var(--text-muted);text-decoration:none}
.footer-links a:hover{color:var(--text-sub)}
.bg-grid{position:fixed;inset:0;pointer-events:none;z-index:0;background-image:linear-gradient(rgba(59,130,246,.03) 1px,transparent 1px),linear-gradient(90deg,rgba(59,130,246,.03) 1px,transparent 1px);background-size:60px 60px}
section,nav,.stats-bar,.cta-section,footer{position:relative;z-index:1}
@media(max-width:900px){.hero{grid-template-columns:1fr;gap:3rem;padding:8rem 1.5rem 4rem}.ticker-stream{display:none}.stats-inner{grid-template-columns:repeat(2,1fr)}.features-grid{grid-template-columns:repeat(2,1fr)}.ai-section{grid-template-columns:1fr}.tech-grid{grid-template-columns:1fr}.factor-section{grid-template-columns:1fr}.metric-row{grid-template-columns:repeat(2,1fr)}}
`

export default function LandingPage() {
  const router = useRouter()
  const [universe, setUniverse] = useState<any[]>([])
  const [marketSummary, setMarketSummary] = useState<any[]>([])
  const [isRefreshing, setIsRefreshing] = useState(false)

  const fetchData = async () => {
    setIsRefreshing(true)
    try {
      const summary = await dashboardApi.getMarketSummary()
      const overview = await dashboardApi.getUniverseOverview()
      setMarketSummary(summary)
      setUniverse(overview)
    } catch (err) {
      console.error("Error fetching landing page live data:", err)
    } finally {
      setIsRefreshing(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [])

  // Live only when the API actually returned universe data; otherwise we render
  // the RAW/SCREENER_DATA sample set and must not badge it as "LIVE".
  const isLive = universe.length > 0

  const streamList = universe.length > 0
    ? universe
    : RAW.map(s => ({ ticker: s[0], name: s[1], price: s[2], change_pct: s[3] }))

  const scrollList = [...streamList, ...streamList]

  const previewScreenerData = universe.length > 0
    ? [...universe].sort((a, b) => (b.composite_score || 0) - (a.composite_score || 0)).slice(0, 6).map(s => ({
        t: s.ticker,
        n: s.name,
        s: s.sector,
        p: s.price,
        c: s.change_pct,
        pe: s.pe_ratio ?? 25.0,
        mom: Math.round(s.composite_score * 0.95),
        qual: Math.round(s.composite_score * 0.85),
        comp: s.composite_score
      }))
    : SCREENER_DATA

  return (
    <>
      {/* Inject raw CSS without React reconciling the text children — avoids a
          server/client hydration mismatch on this large inline stylesheet. */}
      <style dangerouslySetInnerHTML={{ __html: SS }} />
      <div className="bg-grid" />

      <nav>
        <a className="nav-logo" href="#">
          <div className="logo-icon">Q</div>
          QuantAI
        </a>
        <div className="nav-links">
          <a href="#features">Features</a>
          <a href="#dashboard">Dashboard</a>
          <a href="#screener">Screener</a>
          <a href="#ai">AI Research</a>
          <a href="https://github.com/goyal-harshit/quant-analyzer">GitHub</a>
        </div>
        <button className="btn-nav" onClick={() => router.push('/login')}>Launch App →</button>
      </nav>

      <div className="hero">
        <div>
          <div className="hero-badge">
            <span className="pulse-dot" />
            India-First Quantitative Intelligence
          </div>
          <h1>Markets decoded.<br />Factors <span>quantified</span>.<br />Edge yours.</h1>
          <p className="hero-sub">
            QuantAI is an open-source platform for serious Indian equity investors — 
            multi-factor signals, AI research, portfolio analytics, and real-time screener 
            for NSE & BSE. Built for Nifty 500 universe.
          </p>
          <div className="hero-actions">
            <button className="btn-primary" onClick={() => router.push('/login')}>Launch Dashboard →</button>
            <a href="https://github.com/goyal-harshit/quant-analyzer" className="btn-outline">⭐ Star on GitHub</a>
          </div>
        </div>

        <div className="ticker-stream">
          <div className="stream-header">
            <div className="stream-title">
              📡 {isLive ? 'Live Market Feed' : 'Market Feed'}
              {isLive
                ? <span className="live-badge">● LIVE</span>
                : <span className="live-badge" style={{ background: 'rgba(244,63,94,.15)', borderColor: 'rgba(244,63,94,.35)', color: '#f43f5e' }}>● SAMPLE</span>}
            </div>
            <button
              onClick={fetchData}
              disabled={isRefreshing}
              style={{
                background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-sub)',
                display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.7rem',
                fontFamily: 'var(--font-mono)'
              }}
            >
              <RefreshCw style={{ width: 12, height: 12 }} className={isRefreshing ? 'animate-spin' : ''} />
              {isRefreshing ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>
          <div className="stream-body">
            <div className="stream-list">
              {scrollList.map((s, i) => {
                const chg = s.change_pct ?? 0
                const cls = chg >= 0 ? 'pos' : 'neg'
                const sign = chg >= 0 ? '+' : ''
                return (
                  <div key={i} className="stream-item">
                    <span className="si-ticker">{s.ticker}</span>
                    <span className="si-name">{s.name}</span>
                    <span className="si-price">₹{(s.price ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}</span>
                    <span className={`si-chg ${cls}`}>{sign}{chg.toFixed(2)}%</span>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </div>

      <div className="stats-bar">
        <div className="stats-inner">
          {[
            {num: '500', label: 'Nifty 500 Stocks Covered'},
            {num: '15', label: 'Quantitative Factors'},
            {num: '100', label: 'Free & Open Source'},
            {num: '0', label: 'API Keys Required'},
          ].map(s => (
            <div key={s.label} className="stat-item">
              <div className="stat-num">{s.num}<span>+</span></div>
              <div className="stat-label">{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="section" id="features">
        <div className="section-eyebrow">Platform Capabilities</div>
        <div className="section-title">Everything a quant needs</div>
        <p className="section-sub">From single-stock deep-dives to full portfolio factor decomposition — all in one platform, fully open-source.</p>
        <div className="features-grid">
          {[
            {icon: '📊', title: 'Multi-Factor Engine', desc: 'Composite scores across momentum, quality, value, growth, and low-volatility factors — calibrated for the Indian market regime. Live signals updated every 15 minutes.', cls: 'blue'},
            {icon: '🔍', title: 'Quant Screener', desc: 'Screen the Nifty 500 universe by factor scores, fundamentals, technicals, and sector. Combine up to 20 conditions. Export to CSV.', cls: 'cyan'},
            {icon: '🤖', title: 'AI Research Assistant', desc: 'Powered by open-source LLMs via Ollama (Llama 3.2, Qwen2.5, Mistral). Deep-dive analysis, earnings summaries, macro commentary — zero API bill.', cls: 'green'},
            {icon: '💼', title: 'Portfolio Analytics', desc: 'Sector allocation, Sharpe ratio, beta, max drawdown, factor exposure decomposition. Full portfolio risk dashboard in real time.', cls: 'purple'},
            {icon: '⚗️', title: 'Quant Lab', desc: 'Build custom 15-factor models with adjustable weights, rank the Nifty 500, optimise a factor-tilted portfolio, and run Monte-Carlo simulations.', cls: 'warn'},
            {icon: '🌐', title: 'Macro Dashboard', desc: 'RBI policy rates, CPI, IIP, FII/DII flows, INR/USD, India VIX — all in one macro overlay. Understand the regime before you size a position.', cls: 'red'},
          ].map(f => (
            <div key={f.title} className="feature-card">
              <div className={`fc-icon ${f.cls}`}>{f.icon}</div>
              <div className="fc-title">{f.title}</div>
              <p className="fc-desc">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="section" id="dashboard" style={{paddingTop:0}}>
        <div className="section-eyebrow">Live Dashboard</div>
        <div className="section-title">The terminal for Indian equity quants</div>
        <p className="section-sub">A unified interface for market telemetry, factor signals, and portfolio tracking — all live, all quantitative.</p>
        <div className="dash-preview-wrap">
          <div className="dash-bar">
            <div className="dash-dots">
              <div className="dot dot-r" /><div className="dot dot-y" /><div className="dot dot-g" />
            </div>
            <div className="dash-url">localhost:3000 — QuantAI Dashboard</div>
            <span style={{fontSize:'0.7rem',color:'var(--text-muted)',fontFamily:'var(--font-mono)'}}>v1.0.0</span>
          </div>
          <div className="dash-content">
            <div className="dash-sidebar">
              {['📊','📈','🔍','💼','🤖','⚗️','🌐'].map((icon, i) => (
                <div key={i} className={`sb-item ${i === 0 ? 'active' : ''}`} title={['Dashboard','Stocks','Screener','Portfolio','AI','Quant Lab','Macro'][i]}>{icon}</div>
              ))}
            </div>
            <div className="dash-main">
              <div className="dash-header">
                <div>
                  <div className="dh-title">Quant Dashboard</div>
                  <div className="dh-sub">Real-time multi-factor signals & market telemetry</div>
                </div>
                <div style={{display:'flex',alignItems:'center',gap:8}}>
                  <span className="live-badge">● LIVE</span>
                  <span suppressHydrationWarning style={{fontSize:'0.7rem',color:'var(--text-muted)',fontFamily:'var(--font-mono)'}}>{new Date().toLocaleDateString('en-IN', {weekday:'short',day:'numeric',month:'short',year:'numeric'})}</span>
                </div>
              </div>
              <div className="dash-body">
                <div className="metric-row">
                  {(marketSummary.length > 0 ? marketSummary.map(m => {
                    const isVix = m.name === 'INDIA VIX' || m.name === 'India VIX';
                    return {
                      label: m.name,
                      val: isVix ? m.last.toFixed(2) : '₹' + m.last.toLocaleString('en-IN', { maximumFractionDigits: 0 }),
                      chg: isVix ? 'Volatility Index' : (m.change_pct >= 0 ? '+' : '') + m.change_pct.toFixed(2) + '%',
                      cls: isVix ? '' : (m.change_pct >= 0 ? 'pos' : 'neg')
                    }
                  }) : [
                    {label:'Nifty 50',val:'₹25,123',chg:'+0.45%',cls:'pos'},
                    {label:'Sensex',val:'₹82,145',chg:'+0.38%',cls:'pos'},
                    {label:'Bank Nifty',val:'₹52,431',chg:'-0.15%',cls:'neg'},
                    {label:'India VIX',val:'13.45',chg:'Volatility Index',cls:''},
                  ]).map(m => (
                    <div key={m.label} className="metric-card">
                      <div className="mc-label">{m.label}</div>
                      <div className="mc-value">{m.val}</div>
                      {m.cls && <div className={`mc-change ${m.cls}`}>{m.chg}</div>}
                      {!m.cls && <div style={{fontSize:'0.65rem',color:'var(--text-muted)'}}>{m.chg}</div>}
                    </div>
                  ))}
                </div>
                <div className="factor-section">
                  <div className="factor-chart-card">
                    <div className="fcc-title">Factor Signal Strength — Current Composite</div>
                    <div className="chart-bars">
                      {[
                        {label:'Momentum',val:81,color:'var(--brand)'},
                        {label:'Quality',val:55,color:'var(--purple)'},
                        {label:'Value',val:68,color:'var(--success)'},
                        {label:'Growth',val:42,color:'var(--warn)'},
                        {label:'Low Vol',val:73,color:'var(--cyan)'},
                      ].map(f => (
                        <div key={f.label} className="bar-item">
                          <span className="bi-label">{f.label}</span>
                          <div className="bi-track"><div className="bi-fill" style={{width:`${f.val}%`,background:f.color}} /></div>
                          <span className="bi-val" style={{color:f.color}}>{f.val}/100</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="signals-card">
                    <div className="fcc-title">Market Regime</div>
                    <div style={{background:'rgba(34,197,94,0.08)',border:'1px solid rgba(34,197,94,0.2)',borderRadius:8,padding:'0.75rem',marginBottom:'0.75rem'}}>
                      <div style={{fontSize:'0.7rem',fontWeight:700,color:'var(--success)',textTransform:'uppercase',letterSpacing:'0.06em'}}>Low Volatility Expansion</div>
                      <div style={{fontSize:'0.7rem',color:'var(--text-sub)',marginTop:4,lineHeight:1.5}}>Quality + Momentum tilt favored. Build exposure in defensive large-caps.</div>
                    </div>
                    <div className="signal-grid">
                      {[
                        {name:'Momentum Tilt',val:'81%',color:'var(--brand)',bg:'rgba(59,130,246,0.08)'},
                        {name:'Value Tilt',val:'68%',color:'var(--success)',bg:'rgba(34,197,94,0.08)'},
                        {name:'Quality Tilt',val:'55%',color:'var(--purple)',bg:'rgba(168,85,247,0.08)'},
                        {name:'Low Vol Tilt',val:'73%',color:'var(--cyan)',bg:'rgba(6,182,212,0.08)'},
                      ].map(s => (
                        <div key={s.name} className="signal-chip" style={{background:s.bg}}>
                          <div className="sc-name">{s.name}</div>
                          <div className="sc-val" style={{color:s.color}}>{s.val}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="section" id="screener" style={{paddingTop:0}}>
        <div className="section-eyebrow">Smart Screener</div>
        <div className="section-title">Filter Nifty 500 by what matters</div>
        <p className="section-sub">Combine factor scores, fundamentals, sector filters, and momentum ranks to discover high-conviction opportunities. Screen in seconds, not hours.</p>
        <div className="screener-section">
          <div className="sc-header">
            <div className="sc-h-left">
              <div className="sc-h-title">🔍 Quant Screener</div>
              <span className="sc-h-count">{previewScreenerData.length} results</span>
            </div>
            <div className="filter-chips">
              {['High Momentum','Quality > 60','Large Cap'].map(c => (
                <span key={c} className="chip active">{c}</span>
              ))}
            </div>
          </div>
          <table className="sc-table">
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Company</th>
                <th className="r">Price</th>
                <th className="r">1D %</th>
                <th className="r">P/E</th>
                <th className="r">Momentum</th>
                <th className="r">Quality</th>
                <th className="r">Composite</th>
              </tr>
            </thead>
            <tbody>
              {previewScreenerData.map(r => {
                const chgCls = r.c >= 0 ? 'pos' : 'neg'
                const chgSign = r.c >= 0 ? '+' : ''
                const scorePill = (v: number) => {
                  const cls = v >= 75 ? 'score-high' : v >= 55 ? 'score-mid' : 'score-low'
                  return <span className={`score-pill ${cls}`}>{v}</span>
                }
                return (
                  <tr key={r.t}>
                    <td><span className="td-ticker">{r.t}</span></td>
                    <td><div className="td-name">{r.n}</div><div className="td-sector">{r.s}</div></td>
                    <td className="td-right">₹{r.p.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</td>
                    <td className={`td-right ${chgCls}`}>{chgSign}{r.c.toFixed(2)}%</td>
                    <td className="td-right" style={{color:'var(--text-sub)'}}>{r.pe !== null ? r.pe.toFixed(1) + 'x' : 'N/A'}</td>
                    <td className="td-right">{scorePill(r.mom)}</td>
                    <td className="td-right">{scorePill(r.qual)}</td>
                    <td className="td-right">{scorePill(r.comp)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      <div className="section" id="ai">
        <div className="ai-section">
          <div>
            <div className="section-eyebrow">AI Research Assistant</div>
            <div className="section-title">Ask anything about Indian equities</div>
            <p className="section-sub">Powered by open-source LLMs running locally via Ollama. No data leaves your machine. Contextually aware of the stock you&apos;re analyzing.</p>
            <div style={{marginTop:'2rem',display:'flex',flexDirection:'column',gap:'0.75rem'}}>
              {[
                'Zero API cost — runs entirely on your hardware via Ollama',
                'Grounded in live factor scores, fundamentals, and price history',
                'Indian regulatory context — SEBI, RBI, NSE/BSE norms built in',
                'Supports Llama 3.2, Qwen 2.5, Mistral, Phi-3',
              ].map((text, i) => (
                <div key={i} style={{display:'flex',alignItems:'center',gap:10}}>
                  <span style={{width:24,height:24,borderRadius:6,background:'var(--brand-dim)',display:'flex',alignItems:'center',justifyContent:'center',fontSize:'0.7rem',color:'var(--brand)'}}>✓</span>
                  <span style={{fontSize:'0.875rem',color:'var(--text-sub)'}}>{text}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="ai-chat-mock">
            <div className="chat-header">
              <div className="ai-avatar">Q</div>
              <div>
                <div className="chat-name">QuantAI Research</div>
                <div className="chat-status"><span style={{width:5,height:5,borderRadius:'50%',background:'var(--success)',display:'inline-block'}} /> Powered by Llama 3.2</div>
              </div>
            </div>
            <div className="chat-body">
              <div className="chat-msg cm-user">
                <div className="cm-label">You</div>
                <div className="cm-bubble">Give me a quick factor analysis of HDFCBANK. Is it a buy on momentum?</div>
              </div>
              <div className="chat-msg cm-ai">
                <div className="cm-label">QuantAI</div>
                <div className="cm-bubble">
                  <strong>HDFCBANK Factor Snapshot</strong><br /><br />
                  Currently scoring <strong>74/100</strong> composite — top-tier in Banking sector. Momentum score sits at <strong>61/100</strong> (mid-tier), suggesting the post-merger re-rating thesis is partially priced in.<br /><br />
                  Quality remains outstanding: ROE 16.8%, GNPA stable at 1.28%, NIMs recovering to 3.6%. Value at 42/100 — 2.3x P/B is reasonable for HDFC&apos;s franchise.<br /><br />
                  <span style={{color:'var(--warn)'}}>⚠️</span> Momentum alone isn&apos;t a strong enough signal here. Quality-value combo makes it a better hold than a fresh momentum entry.<br /><br />
                  <span style={{fontSize:'0.7rem',color:'var(--text-muted)'}}>Educational only. Not investment advice.</span>
                </div>
              </div>
              <div className="chat-msg cm-user">
                <div className="cm-label">You</div>
                <div className="cm-bubble">What peers should I compare it against?</div>
              </div>
              <div className="chat-msg cm-ai">
                <div className="cm-label">QuantAI</div>
                <div className="chat-typing">
                  <div className="typing-dot" /><div className="typing-dot" /><div className="typing-dot" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="sep" />
      <div className="section">
        <div className="section-eyebrow">Architecture</div>
        <div className="section-title">Built for production from day one</div>
        <p className="section-sub">Open-source, containerized, and designed to scale. Every layer is replaceable and self-hostable.</p>
        <div className="tech-grid">
          {[
            {layer:'Frontend',title:'Next.js 14 App Router',desc:'Server components, React Query for server state, TypeScript end-to-end, glassmorphism dark UI.',tags:['Next.js 14','TypeScript','Tailwind','React Query']},
            {layer:'Backend API',title:'FastAPI + Python 3.12',desc:'Async SQLAlchemy, 15 domain routers, multi-tier caching with Redis + TTLCache, retry with exponential backoff.',tags:['FastAPI','SQLAlchemy','Redis','Celery']},
            {layer:'AI / LLM',title:'Local Ollama Runtime',desc:'Zero-cost LLM inference on your own hardware. Llama 3.2, Qwen 2.5, Mistral supported. No data sent to external APIs.',tags:['Ollama','Llama 3.2','Qwen 2.5','Mistral']},
            {layer:'Data Layer',title:'PostgreSQL + TimescaleDB',desc:'Time-series optimized schema for price data, async connection pooling, Alembic migrations, JSONB for factor scores.',tags:['PostgreSQL','TimescaleDB','Alembic','asyncpg']},
            {layer:'Data Sources',title:'Free Indian Market Data',desc:'Multi-source fallback chain: NSE API → Screener.in → yfinance → seed data. 100% free, no paid subscriptions required.',tags:['NSE API','Screener.in','yfinance','jugaad-data']},
            {layer:'Infrastructure',title:'Docker Compose Stack',desc:'6-service compose file: backend + frontend + ollama + postgres + redis + celery worker. One command to start everything.',tags:['Docker','Compose','nginx','Celery Beat']},
          ].map(t => (
            <div key={t.title} className="tech-card">
              <div className="tc-layer">{t.layer}</div>
              <div className="tc-title">{t.title}</div>
              <p className="tc-desc">{t.desc}</p>
              <div className="tech-tags">{t.tags.map(tag => <span key={tag} className="tech-tag">{tag}</span>)}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="cta-section">
        <div className="cta-inner">
          <div className="hero-badge" style={{margin:'0 auto 1.5rem'}}>
            <span className="pulse-dot" />
            Open Source · Self-Hostable · Free Forever
          </div>
          <div className="cta-title">Start analyzing India&apos;s markets today</div>
          <p className="cta-sub">Deploy in minutes with Docker Compose. No subscriptions. No API keys. Just clone, run, and go.</p>
          <div className="cta-actions">
            <button className="btn-primary" onClick={() => router.push('/login')}>Launch App →</button>
            <a href="https://github.com/goyal-harshit/quant-analyzer" className="btn-outline">Read the Docs</a>
          </div>
          <div style={{marginTop:'2rem',fontFamily:'var(--font-mono)',fontSize:'0.8rem',color:'var(--text-muted)',background:'var(--elevated)',border:'1px solid var(--border)',borderRadius:10,padding:'1rem 1.5rem',textAlign:'left',display:'inline-block'}}>
            $ git clone https://github.com/goyal-harshit/quant-analyzer<br />
            $ cd quant-analyzer<br />
            $ docker compose up -d<br />
            <span style={{color:'var(--success)'}}>✅ QuantAI running at http://localhost:3000</span>
          </div>
        </div>
      </div>

      <footer>
        <div className="footer-copy">© 2026 QuantAI · India-First Quantitative Analytics · Open Source</div>
        <div className="footer-links">
          <a href="https://github.com/goyal-harshit/quant-analyzer">GitHub</a>
          <a href="#">Docs</a>
          <a href="#">API Reference</a>
        </div>
      </footer>
    </>
  )
}
