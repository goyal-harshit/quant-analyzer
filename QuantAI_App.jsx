import { useState, useRef, useEffect } from "react";
import { Home, Filter, Target, RefreshCw, Globe, MessageSquare, Zap, Database, Activity, TrendingUp, Shield, Send, Cpu } from "lucide-react";
import { AreaChart, Area, LineChart, Line, BarChart, Bar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

// ━━━ DESIGN TOKENS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const T = {
  bg:'#030712', card:'#0a1020', el:'#0f182e', b:'#1e2d4a', bhi:'#2a3f6a',
  blue:'#3b82f6', green:'#22c55e', red:'#f43f5e', amber:'#f59e0b', purple:'#a78bfa',
  text:'#e2e8f0', sub:'#94a3b8', muted:'#475569',
  mono:'"JetBrains Mono",Consolas,monospace', sans:'Inter,system-ui,sans-serif',
};
const card = (x={}) => ({ background:T.card, border:`1px solid ${T.b}`, borderRadius:10, ...x });
const sc = v => v>=70 ? T.green : v>=45 ? T.amber : T.red;

// ━━━ OLLAMA CONFIG (free, self-hosted — no API key, no payment) ━━━
const OLLAMA_URL = 'http://localhost:11434/api/chat';
const OLLAMA_MODEL = 'llama3.2';

// ━━━ SEEDED RNG ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function mkRng(seed){ let s=seed; return ()=>{ s=(s*9301+49297)%233280; return s/233280; }; }

// ━━━ STOCK DATA (25 NSE STOCKS) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const RAW=[
  ['RELIANCE',  'Reliance Industries', 'Energy',       2847.5, 1.24,24.5, 2.1,15.2,12.3,67,78,71,63,1924],
  ['HDFCBANK',  'HDFC Bank',           'Banking',      1742.3, 0.83,19.2, 2.8,17.1,18.5,72,85,76,74,1323],
  ['TCS',       'Tata Consultancy',    'IT',           3912.5,-0.45,28.7,12.4,47.2, 8.7,61,92,52,58,1421],
  ['INFY',      'Infosys Ltd',         'IT',           1478.9,-0.21,25.3, 8.9,33.8, 9.1,58,88,60,56, 614],
  ['ICICIBANK', 'ICICI Bank',          'Banking',      1089.8, 2.17,17.8, 2.9,17.9,22.1,81,82,79,79, 768],
  ['HINDUNILVR','Hindustan Unilever',  'FMCG',         2534.6, 0.34,58.3,11.2,19.5, 3.2,45,87,35,42, 594],
  ['BHARTIARTL','Bharti Airtel',       'Telecom',      1621.3, 1.89,65.2, 5.8, 9.2,24.5,89,72,38,82, 961],
  ['BAJFINANCE','Bajaj Finance',       'NBFC',         6834.2, 1.56,32.4, 6.1,19.8,28.7,76,79,55,84, 423],
  ['KOTAKBANK', 'Kotak Mahindra Bank', 'Banking',      1823.4,-0.67,21.5, 3.2,15.8,15.3,55,83,72,65, 362],
  ['SBIN',      'State Bank of India', 'Banking',       795.6, 3.12,11.2, 1.5,14.2,18.9,73,71,88,71, 709],
  ['WIPRO',     'Wipro Ltd',           'IT',            462.3,-1.23,22.7, 4.2,18.5, 3.1,42,78,67,38, 241],
  ['TITAN',     'Titan Company',       'Consumer',     3287.5, 0.91,82.4,17.3,21.2,19.8,71,84,28,76, 291],
  ['ITC',       'ITC Ltd',             'FMCG',          482.5, 0.52,27.8, 6.8,25.1, 7.5,48,86,69,52, 603],
  ['LT',        'Larsen & Toubro',     'Capital Goods',3567.8, 1.43,35.2, 5.4,16.3,17.2,77,75,54,73, 490],
  ['ASIANPAINT','Asian Paints',        'Consumer',     2891.3,-0.34,65.8,16.2,25.4, 5.3,38,89,32,44, 277],
  ['MARUTI',    'Maruti Suzuki',       'Auto',        12543.5, 0.78,29.7, 4.8,16.8,13.4,62,76,61,67, 390],
  ['AXISBANK',  'Axis Bank',           'Banking',      1156.8, 1.85,15.8, 2.3,16.2,20.4,68,74,81,75, 357],
  ['HCLTECH',   'HCL Technologies',    'IT',           1623.5, 0.19,24.1, 6.7,28.3, 7.9,56,83,63,57, 440],
  ['SUNPHARMA', 'Sun Pharmaceutical',  'Pharma',       1687.2, 0.62,38.4, 6.2,16.8,11.2,74,79,49,63, 405],
  ['TATAMOTORS','Tata Motors',         'Auto',          967.4, 2.34,12.4, 3.2,26.4,22.7,85,68,77,82, 355],
  ['NTPC',      'NTPC Ltd',            'Utilities',     387.3, 0.94,15.2, 2.1,14.1, 9.7,71,72,84,58, 376],
  ['POWERGRID', 'Power Grid Corp',     'Utilities',     342.6, 0.47,18.7, 3.1,17.2, 8.4,63,78,77,54, 318],
  ['NESTLEIND', 'Nestle India',        'FMCG',         2401.8,-0.15,74.2,94.3,127.5,6.8,35,91,22,46, 231],
  ['ONGC',      'ONGC Ltd',            'Energy',        281.4,-0.82, 7.8, 0.9,12.4,14.2,55,65,93,59, 354],
  ['ADANIENT',  'Adani Enterprises',   'Conglomerate', 2847.6, 3.45,78.3, 4.8, 6.2,35.4,82,52,31,88, 324],
];
const STOCKS = RAW.map(([ticker,name,sector,price,chg,pe,pb,roe,rev,mom,qual,val,grw,mcap])=>({
  ticker,name,sector,price,chg,pe,pb,roe,rev,mom,qual,val,grw,mcap,
  composite: Math.round(mom*0.25+qual*0.25+val*0.20+grw*0.20+Math.min(100,roe*0.8)*0.10)
}));

// ━━━ PRICE HISTORY ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function genPrices(base, seed, n=120){
  const r=mkRng(seed); const pts=[]; let p=base*0.80;
  const st=new Date('2024-11-15');
  for(let i=0;i<n;i++){
    const d=new Date(st); d.setDate(d.getDate()+i);
    if(d.getDay()===0||d.getDay()===6) continue;
    const shock = r()<0.06 ? (r()-0.5)*0.04 : 0;
    p *= (1+0.0004+(r()-0.48)*0.018+shock);
    pts.push({ d:d.toLocaleDateString('en-IN',{month:'short',day:'numeric'}), p:+p.toFixed(2) });
  }
  if(!pts.length) return pts;
  const scale = base/pts[pts.length-1].p;
  return pts.map(x=>({...x, p:+(x.p*scale).toFixed(2)}));
}
const SP={};
STOCKS.forEach((s,i)=>{ SP[s.ticker]=genPrices(s.price,i*137+42); });

// ━━━ PORTFOLIO ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const POS=[
  {ticker:'ICICIBANK', qty:150, cost:985.40},
  {ticker:'TCS',       qty: 20, cost:3650.80},
  {ticker:'BHARTIARTL',qty:100, cost:1425.50},
  {ticker:'TATAMOTORS',qty:200, cost:820.30},
  {ticker:'SBIN',      qty:250, cost:710.20},
];

// ━━━ MACRO DATA ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const MACRO={
  repo:[{q:'Q2FY23',v:5.9},{q:'Q3FY23',v:6.25},{q:'Q4FY23',v:6.5},{q:'Q1FY24',v:6.5},{q:'Q2FY24',v:6.5},{q:'Q3FY24',v:6.5},{q:'Q4FY24',v:6.5},{q:'Q1FY25',v:6.5},{q:'Q2FY25',v:6.5},{q:'Q3FY25',v:6.25},{q:'Q4FY25',v:6.0},{q:'Q1FY26',v:5.75}],
  cpi:[{m:'Jul-24',v:3.54},{m:'Aug-24',v:3.65},{m:'Sep-24',v:5.49},{m:'Oct-24',v:6.21},{m:'Nov-24',v:5.48},{m:'Dec-24',v:5.22},{m:'Jan-25',v:4.26},{m:'Feb-25',v:3.61},{m:'Mar-25',v:3.34},{m:'Apr-25',v:3.16},{m:'May-25',v:2.82},{m:'Jun-25',v:2.60}],
  inr:[{m:'Jul-24',v:83.71},{m:'Aug-24',v:83.95},{m:'Sep-24',v:83.80},{m:'Oct-24',v:84.05},{m:'Nov-24',v:84.48},{m:'Dec-24',v:84.92},{m:'Jan-25',v:85.98},{m:'Feb-25',v:86.45},{m:'Mar-25',v:86.12},{m:'Apr-25',v:85.41},{m:'May-25',v:84.89},{m:'Jun-25',v:84.32}],
  fii:[{m:'Jul-24',v:8543},{m:'Aug-24',v:7234},{m:'Sep-24',v:57724},{m:'Oct-24',v:-94017},{m:'Nov-24',v:-45974},{m:'Dec-24',v:15446},{m:'Jan-25',v:-87374},{m:'Feb-25',v:-34574},{m:'Mar-25',v:3973},{m:'Apr-25',v:10456},{m:'May-25',v:23782},{m:'Jun-25',v:15234}],
};

// ━━━ BACKTEST DATA ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function genBT(seed,cagr,vol){
  const r=mkRng(seed); const pts=[]; let v=100;
  const mr=(1+cagr/100)**(1/12)-1;
  const st=new Date('2022-06-01');
  for(let i=0;i<=36;i++){
    const d=new Date(st); d.setMonth(d.getMonth()+i);
    const lbl=d.toLocaleDateString('en-IN',{month:'short',year:'2-digit'});
    if(i>0) v*=(1+mr+(r()-0.5)*vol*2);
    pts.push({date:lbl,value:+v.toFixed(1)});
  }
  return pts;
}
const BTS={'High Momentum':genBT(42,22.5,0.045),'Quality Value':genBT(99,18.8,0.035),'Composite Score':genBT(7,24.3,0.040),'Nifty 50':genBT(200,16.2,0.038)};
const BT_STATS={'High Momentum':{cagr:22.5,sharpe:1.42,maxDD:-18.3,ret:82.1},'Quality Value':{cagr:18.8,sharpe:1.21,maxDD:-14.2,ret:67.3},'Composite Score':{cagr:24.3,sharpe:1.56,maxDD:-16.8,ret:91.4},'Nifty 50':{cagr:16.2,sharpe:0.94,maxDD:-22.1,ret:56.2}};
const BT_CHART=Array.from({length:37},(_,i)=>{ const o={date:BTS['Nifty 50'][i].date}; Object.entries(BTS).forEach(([k,a])=>{o[k]=a[i].value;}); return o; });
const BT_COL={'High Momentum':T.amber,'Quality Value':'#a78bfa','Composite Score':T.blue,'Nifty 50':'#475569'};

// ━━━ UTILITIES ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const fI = n => '₹'+n.toLocaleString('en-IN',{maximumFractionDigits:0});
const pct = n => `${n>0?'+':''}${n.toFixed(2)}%`;

// ━━━ OFFLINE RULE-BASED ANALYSIS ENGINE ━━━━━━━━━━━━━━━━━━━━━━━━
// This runs with ZERO external calls and ZERO cost. The app tries
// your self-hosted Ollama instance first (also free, open-source);
// if it's unreachable — as it will be inside this sandboxed preview,
// since the browser can't reach a localhost service on your machine —
// it falls back to this deterministic, data-driven generator so the
// feature still works end-to-end with no setup at all.
function buildOfflineReport(s){
  const tier = v => v>=70?'top-tier':v>=45?'mid-tier':'lower-tier';
  const peers = STOCKS.filter(x=>x.sector===s.sector && x.ticker!==s.ticker).sort((a,b)=>b.composite-a.composite).slice(0,2);
  return `**Quick Snapshot**
${s.name} (${s.ticker}) trades at ₹${s.price.toLocaleString('en-IN')} (${pct(s.chg)} today) with a P/E of ${s.pe.toFixed(1)}x and ROE of ${s.roe.toFixed(1)}%. Its composite factor score of ${s.composite}/100 places it in the ${tier(s.composite)} of the Nifty universe within ${s.sector}.

**Strengths**
• ${s.qual>=65?`Strong Quality score (${s.qual}) — ROE of ${s.roe.toFixed(1)}% signals efficient capital use`:`Revenue growing at ${s.rev.toFixed(1)}% YoY, a reasonable pace for ${s.sector}`}
• ${s.mom>=65?`Momentum score of ${s.mom} shows strong recent relative price strength`:`Valuation looks measured at ${s.pe.toFixed(1)}x earnings`}
• ${s.val>=55?`Value score of ${s.val} suggests the stock isn't expensive relative to peers`:`Established scale within the ${s.sector} sector (composite rank: ${s.composite})`}

**Risks**
• ${s.pe>40?`P/E of ${s.pe.toFixed(1)}x is elevated — leaves limited room for multiple expansion`:`Momentum score of ${s.mom} is muted — limited near-term price catalysts visible in the data`}
• ${s.pb>10?`P/B of ${s.pb.toFixed(1)}x implies the market is pricing in a lot of future growth`:`Growth score of ${s.grw} suggests topline momentum could be inconsistent quarter to quarter`}

**Factor View**
A composite score of ${s.composite}/100 (Momentum ${s.mom} · Quality ${s.qual} · Value ${s.val} · Growth ${s.grw}) places ${s.ticker} in the ${tier(s.composite)} of its peer set on a blended multi-factor basis.

**Peers**
${peers.length ? peers.map(p=>`${p.ticker} (composite ${p.composite})`).join(' · ') : 'No close sector peers in this sample universe.'}

⚠️ Generated by QuantAI's offline rule-based engine (no LLM call — Ollama not reachable from this sandboxed preview). Self-host this app with Ollama running locally (\`ollama serve\`) for full open-source LLM-generated analysis, completely free. Educational purposes only — not investment advice.`;
}

function buildOfflineChatReply(q){
  const ql=q.toLowerCase();
  const mentioned = STOCKS.filter(s=>ql.includes(s.ticker.toLowerCase())||ql.includes(s.name.toLowerCase().split(' ')[0]));
  if(mentioned.length>=2){
    const [a,b]=mentioned;
    return `Comparing ${a.ticker} vs ${b.ticker} on quantitative factors:\n\n${a.ticker}: Composite ${a.composite} (Quality ${a.qual}, Momentum ${a.mom}, Value ${a.val}) · ROE ${a.roe.toFixed(1)}% · P/E ${a.pe.toFixed(1)}x\n${b.ticker}: Composite ${b.composite} (Quality ${b.qual}, Momentum ${b.mom}, Value ${b.val}) · ROE ${b.roe.toFixed(1)}% · P/E ${b.pe.toFixed(1)}x\n\nOn this data, ${a.composite>b.composite?a.ticker:b.ticker} screens higher on the blended composite factor, driven primarily by ${a.composite>b.composite?(a.qual>a.mom?'Quality':'Momentum'):(b.qual>b.mom?'Quality':'Momentum')}.\n\n⚠️ Offline rule-based reply (Ollama not reachable in this preview). Self-host with Ollama for full LLM responses, free.`;
  }
  if(mentioned.length===1){
    const s=mentioned[0];
    return `${s.name} (${s.ticker}) — quick data view:\nPrice ₹${s.price.toLocaleString('en-IN')} (${pct(s.chg)}) · Sector: ${s.sector}\nP/E ${s.pe.toFixed(1)}x · P/B ${s.pb.toFixed(1)}x · ROE ${s.roe.toFixed(1)}%\nFactor scores — Momentum ${s.mom} · Quality ${s.qual} · Value ${s.val} · Growth ${s.grw} · Composite ${s.composite}\n\nOpen the Screener or click this stock from the Dashboard for the full AI report.\n\n⚠️ Offline rule-based reply (Ollama not reachable in this preview).`;
  }
  if(ql.includes('rbi')||ql.includes('repo')||ql.includes('rate')){
    return `RBI's repo rate currently stands at ${MACRO.repo[MACRO.repo.length-1].v}%, down from 6.5% a year ago — an easing cycle. Historically, falling rates benefit rate-sensitive sectors: Banking, NBFC, Real Estate, and Auto (financing-driven demand). Check the Macro tab for the full repo rate and CPI trend charts.\n\n⚠️ Offline rule-based reply (Ollama not reachable in this preview).`;
  }
  if(ql.includes('momentum')){
    return `Momentum investing ranks stocks by relative price strength over the trailing 12 months (skipping the most recent month to avoid short-term reversal). In the Indian market context, momentum has historically been one of the stronger factors — see the Backtester tab, where the "High Momentum" strategy shows a ${BT_STATS['High Momentum'].cagr}% CAGR vs ${BT_STATS['Nifty 50'].cagr}% for Nifty 50 over the same period.\n\n⚠️ Offline rule-based reply (Ollama not reachable in this preview).`;
  }
  return `I can discuss specific Nifty stocks (try mentioning a ticker like "HDFCBANK" or "TCS"), RBI policy, or factor investing concepts. Try one of the quick prompts below, or ask about a specific stock or sector.\n\n⚠️ This is an offline rule-based reply because Ollama isn't reachable from this sandboxed preview (browsers can't call services on your own machine from here). Run this app on your own device with \`ollama serve\` running for full open-source LLM responses — completely free, no API key.`;
}

async function callOllama(messages, system){
  const res = await fetch(OLLAMA_URL, {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({
      model: OLLAMA_MODEL,
      messages: [{role:'system',content:system}, ...messages],
      stream:false,
      options:{ temperature:0.4 }
    })
  });
  if(!res.ok) throw new Error('Ollama unreachable');
  const d = await res.json();
  return d.message?.content || '';
}

// ━━━ SHARED UI ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function FactorBar({label,value}){
  return(
    <div style={{marginBottom:9}}>
      <div style={{display:'flex',justifyContent:'space-between',marginBottom:3}}>
        <span style={{fontSize:11,color:T.sub}}>{label}</span>
        <span style={{fontSize:11,fontFamily:T.mono,fontWeight:700,color:sc(value)}}>{value}</span>
      </div>
      <div style={{height:5,background:T.b,borderRadius:3,overflow:'hidden'}}>
        <div style={{height:'100%',width:`${value}%`,borderRadius:3,background:'linear-gradient(90deg,#f43f5e,#f59e0b,#22c55e)'}}/>
      </div>
    </div>
  );
}
function Stat({label,value,sub,color,icon:Icon}){
  return(
    <div style={card({padding:'15px 18px'})}>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:8}}>
        <span style={{fontSize:10,color:T.muted,textTransform:'uppercase',letterSpacing:'0.07em'}}>{label}</span>
        {Icon&&<Icon size={13} color={T.muted}/>}
      </div>
      <div style={{fontSize:21,fontWeight:700,fontFamily:T.mono,color:color||T.text}}>{value}</div>
      {sub&&<div style={{fontSize:11,color:T.sub,marginTop:3}}>{sub}</div>}
    </div>
  );
}
function Tag({children,color='#a78bfa'}){
  return <span style={{background:`${color}22`,color,border:`1px solid ${color}44`,borderRadius:4,padding:'2px 7px',fontSize:10,fontWeight:700}}>{children}</span>;
}
function CT({active,payload,label}){
  if(!active||!payload?.length) return null;
  return(
    <div style={{background:T.el,border:`1px solid ${T.b}`,borderRadius:6,padding:'8px 12px',fontSize:12}}>
      <div style={{color:T.muted,marginBottom:4}}>{label}</div>
      {payload.map((p,i)=>(
        <div key={i} style={{color:p.color||T.text,fontFamily:T.mono}}>
          {p.name&&<span style={{color:T.sub}}>{p.name}: </span>}
          {typeof p.value==='number'?p.value.toFixed(2):p.value}
        </div>
      ))}
    </div>
  );
}
function Badge({v}){
  const c=sc(v);
  return <span style={{background:`${c}22`,color:c,border:`1px solid ${c}44`,borderRadius:4,padding:'2px 9px',fontSize:12,fontFamily:T.mono,fontWeight:700}}>{v}</span>;
}

// ━━━ SIDEBAR ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const NAV=[{id:'dashboard',icon:Home,label:'Dashboard'},{id:'screener',icon:Filter,label:'Screener'},{id:'portfolio',icon:Target,label:'Portfolio'},{id:'backtest',icon:RefreshCw,label:'Backtester'},{id:'macro',icon:Globe,label:'Macro'},{id:'ai',icon:MessageSquare,label:'QuantAI'}];
function Sidebar({page,nav}){
  return(
    <div style={{position:'fixed',left:0,top:0,bottom:0,width:215,background:T.card,borderRight:`1px solid ${T.b}`,display:'flex',flexDirection:'column',zIndex:100,fontFamily:T.sans}}>
      <div style={{padding:'18px 18px 14px',borderBottom:`1px solid ${T.b}`}}>
        <div style={{display:'flex',alignItems:'center',gap:10}}>
          <div style={{width:34,height:34,background:T.blue,borderRadius:8,display:'flex',alignItems:'center',justifyContent:'center'}}><Zap size={16} color="#fff"/></div>
          <div>
            <div style={{fontSize:15,fontWeight:700,color:T.text}}>QuantAI</div>
            <div style={{fontSize:10,color:T.muted}}>NSE · BSE Analytics</div>
          </div>
        </div>
      </div>
      <nav style={{flex:1,padding:'10px 8px'}}>
        {NAV.map(({id,icon:Icon,label})=>{
          const active=page===id||(page==='stock'&&id==='screener');
          return(
            <button key={id} onClick={()=>nav(id)} style={{width:'100%',display:'flex',alignItems:'center',gap:11,padding:'9px 12px',borderRadius:7,marginBottom:2,cursor:'pointer',background:active?`${T.blue}18`:'transparent',border:`1px solid ${active?T.blue+'44':'transparent'}`,color:active?T.blue:T.sub,fontSize:13,fontWeight:active?600:400}}>
              <Icon size={15}/>{label}
            </button>
          );
        })}
      </nav>
      <div style={{padding:'12px 16px',borderTop:`1px solid ${T.b}`}}>
        <div style={{display:'flex',alignItems:'center',gap:6,marginBottom:5}}>
          <Cpu size={11} color={T.green}/>
          <span style={{fontSize:10,color:T.green,fontWeight:600,fontFamily:T.mono}}>OLLAMA · FREE LLM</span>
        </div>
        <div style={{fontSize:10,color:T.muted,lineHeight:1.6}}>
          100% open-source stack · No API costs · Educational use only
        </div>
      </div>
    </div>
  );
}

// ━━━ DASHBOARD ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function Dashboard({nav,setStock}){
  const indices=[{label:'NIFTY 50',val:24857.2,chg:0.89},{label:'SENSEX',val:81865.4,chg:0.74},{label:'BANK NIFTY',val:53241.8,chg:1.12},{label:'INDIA VIX',val:13.42,chg:-0.85}];
  const sorted=[...STOCKS].sort((a,b)=>b.composite-a.composite);
  const byChg=[...STOCKS].sort((a,b)=>b.chg-a.chg);
  const niftyPts=genPrices(24857.2,999,120).slice(-88);
  return(
    <div style={{padding:'26px 30px',maxWidth:1200,fontFamily:T.sans}}>
      <div style={{marginBottom:24}}>
        <div style={{fontSize:22,fontWeight:700,color:T.text}}>Market Dashboard</div>
        <div style={{fontSize:13,color:T.sub,marginTop:3}}>NSE · BSE · India Equities — {new Date().toLocaleDateString('en-IN',{weekday:'long',year:'numeric',month:'long',day:'numeric'})}</div>
      </div>
      <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:12,marginBottom:20}}>
        {indices.map(({label,val,chg})=>(
          <div key={label} style={card({padding:'13px 16px'})}>
            <div style={{fontSize:10,color:T.muted,textTransform:'uppercase',letterSpacing:'0.07em',marginBottom:5}}>{label}</div>
            <div style={{fontSize:20,fontWeight:700,fontFamily:T.mono,color:T.text}}>{val.toLocaleString('en-IN')}</div>
            <div style={{fontSize:12,fontFamily:T.mono,color:chg>=0?T.green:T.red,marginTop:2}}>{chg>=0?'▲':'▼'} {Math.abs(chg).toFixed(2)}%</div>
          </div>
        ))}
      </div>
      <div style={{display:'grid',gridTemplateColumns:'2fr 1fr',gap:14,marginBottom:14}}>
        <div style={card({padding:'16px 18px'})}>
          <div style={{fontSize:13,fontWeight:600,color:T.text,marginBottom:14}}>Nifty 50 — 90 Days</div>
          <ResponsiveContainer width="100%" height={195}>
            <AreaChart data={niftyPts} margin={{top:4,right:4,bottom:0,left:44}}>
              <defs><linearGradient id="g0" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor={T.blue} stopOpacity={0.3}/><stop offset="95%" stopColor={T.blue} stopOpacity={0}/></linearGradient></defs>
              <XAxis dataKey="d" tick={{fontSize:10,fill:T.muted}} tickLine={false} axisLine={false} interval={15}/>
              <YAxis tick={{fontSize:10,fill:T.muted,fontFamily:T.mono}} tickLine={false} axisLine={false} domain={['auto','auto']} tickFormatter={v=>v.toLocaleString('en-IN')}/>
              <Tooltip content={<CT/>}/>
              <Area type="monotone" dataKey="p" stroke={T.blue} strokeWidth={2} fill="url(#g0)" dot={false}/>
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div style={card({padding:'16px 18px'})}>
          <div style={{fontSize:13,fontWeight:600,color:T.text,marginBottom:12}}>🏆 Top Factor Signals</div>
          {sorted.slice(0,6).map(stk=>(
            <div key={stk.ticker} onClick={()=>{setStock(stk);nav('stock');}} style={{display:'flex',justifyContent:'space-between',alignItems:'center',padding:'7px 0',borderBottom:`1px solid ${T.b}`,cursor:'pointer'}}>
              <div>
                <div style={{fontSize:12,fontWeight:600,color:T.text,fontFamily:T.mono}}>{stk.ticker}</div>
                <div style={{fontSize:10,color:T.muted}}>{stk.sector}</div>
              </div>
              <div style={{textAlign:'right'}}>
                <Badge v={stk.composite}/>
                <div style={{fontSize:10,fontFamily:T.mono,color:stk.chg>=0?T.green:T.red,marginTop:2}}>{pct(stk.chg)}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:14}}>
        {[{title:'📈 Top Gainers',data:byChg.slice(0,5)},{title:'📉 Top Losers',data:[...byChg].reverse().slice(0,5)}].map(({title,data})=>(
          <div key={title} style={card({padding:'15px 18px'})}>
            <div style={{fontSize:13,fontWeight:600,color:T.text,marginBottom:10}}>{title}</div>
            {data.map(stk=>(
              <div key={stk.ticker} onClick={()=>{setStock(stk);nav('stock');}} style={{display:'flex',justifyContent:'space-between',alignItems:'center',padding:'6px 0',borderBottom:`1px solid ${T.b}`,cursor:'pointer'}}>
                <div><div style={{fontSize:12,fontWeight:600,color:T.text,fontFamily:T.mono}}>{stk.ticker}</div><div style={{fontSize:10,color:T.muted}}>{stk.name}</div></div>
                <div style={{textAlign:'right'}}>
                  <div style={{fontSize:12,fontFamily:T.mono,color:T.text}}>₹{stk.price.toLocaleString('en-IN')}</div>
                  <div style={{fontSize:11,fontFamily:T.mono,color:stk.chg>=0?T.green:T.red}}>{pct(stk.chg)}</div>
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

// ━━━ SCREENER ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function Screener({nav,setStock}){
  const [flt,setFlt]=useState({sector:'All',minRoe:0,maxPe:100,minMom:0,minQual:0,minScore:0});
  const [sort,setSort]=useState({key:'composite',dir:-1});
  const [q,setQ]=useState('');
  const sectors=['All',...new Set(STOCKS.map(s=>s.sector))];
  const rows=[...STOCKS].filter(s=>(flt.sector==='All'||s.sector===flt.sector)&&s.roe>=flt.minRoe&&s.pe<=flt.maxPe&&s.mom>=flt.minMom&&s.qual>=flt.minQual&&s.composite>=flt.minScore&&(q===''||s.ticker.includes(q.toUpperCase())||s.name.toLowerCase().includes(q.toLowerCase()))).sort((a,b)=>typeof a[sort.key]==='string'?(a[sort.key]>b[sort.key]?1:-1)*sort.dir:(a[sort.key]-b[sort.key])*sort.dir);
  function Th({label,k,left}){
    return <th onClick={()=>setSort(p=>({key:k,dir:p.key===k?-p.dir:-1}))} style={{padding:'10px 13px',fontSize:10,textTransform:'uppercase',letterSpacing:'0.06em',color:sort.key===k?T.blue:T.muted,cursor:'pointer',textAlign:left?'left':'right',fontWeight:600,whiteSpace:'nowrap'}}>{label}{sort.key===k?(sort.dir===-1?' ↓':' ↑'):''}</th>;
  }
  return(
    <div style={{padding:'26px 30px',maxWidth:1400,fontFamily:T.sans}}>
      <div style={{marginBottom:20}}>
        <div style={{fontSize:22,fontWeight:700,color:T.text}}>Factor Screener</div>
        <div style={{fontSize:13,color:T.sub,marginTop:3}}>Screening {rows.length} of {STOCKS.length} stocks — Nifty 500 universe</div>
      </div>
      <div style={card({padding:'14px 18px',marginBottom:18})}>
        <div style={{display:'flex',gap:20,flexWrap:'wrap',alignItems:'flex-end'}}>
          <div>
            <div style={{fontSize:10,color:T.muted,marginBottom:4}}>SECTOR</div>
            <select value={flt.sector} onChange={e=>setFlt(f=>({...f,sector:e.target.value}))} style={{background:T.el,border:`1px solid ${T.b}`,borderRadius:6,padding:'6px 10px',fontSize:12,color:T.text,cursor:'pointer'}}>
              {sectors.map(s=><option key={s}>{s}</option>)}
            </select>
          </div>
          {[{label:'MIN ROE%',k:'minRoe',max:40},{label:'MAX PE',k:'maxPe',max:100},{label:'MIN MOM',k:'minMom',max:100},{label:'MIN QUAL',k:'minQual',max:100},{label:'MIN SCORE',k:'minScore',max:100}].map(({label,k,max})=>(
            <div key={k} style={{minWidth:110}}>
              <div style={{fontSize:10,color:T.muted,marginBottom:4}}>{label}: <span style={{color:T.blue,fontFamily:T.mono}}>{flt[k]}</span></div>
              <input type="range" min={0} max={max} value={flt[k]} onChange={e=>setFlt(f=>({...f,[k]:+e.target.value}))} style={{width:'100%',accentColor:T.blue}}/>
            </div>
          ))}
          <div style={{marginLeft:'auto'}}>
            <input value={q} onChange={e=>setQ(e.target.value)} placeholder="Search ticker..." style={{background:T.el,border:`1px solid ${T.b}`,borderRadius:6,padding:'6px 12px',fontSize:12,color:T.text,width:170,outline:'none'}}/>
          </div>
        </div>
      </div>
      <div style={card({overflow:'auto'})}>
        <table style={{width:'100%',borderCollapse:'collapse'}}>
          <thead>
            <tr style={{borderBottom:`1px solid ${T.b}`}}>
              <Th label="Ticker" k="ticker" left/><Th label="Sector" k="sector" left/><Th label="Price" k="price"/><Th label="Chg%" k="chg"/><Th label="PE" k="pe"/><Th label="PB" k="pb"/><Th label="ROE%" k="roe"/><Th label="Rev.G%" k="rev"/><Th label="Mom" k="mom"/><Th label="Qual" k="qual"/><Th label="Val" k="val"/><Th label="Grw" k="grw"/><Th label="Score" k="composite"/>
            </tr>
          </thead>
          <tbody>
            {rows.map((stk,i)=>(
              <tr key={stk.ticker} onClick={()=>{setStock(stk);nav('stock');}} style={{borderBottom:`1px solid ${T.b}`,cursor:'pointer',background:i%2===0?'transparent':`${T.el}66`}} onMouseEnter={e=>e.currentTarget.style.background=T.el} onMouseLeave={e=>e.currentTarget.style.background=i%2===0?'transparent':`${T.el}66`}>
                <td style={{padding:'9px 13px'}}><div style={{fontFamily:T.mono,fontWeight:700,fontSize:12,color:T.text}}>{stk.ticker}</div><div style={{fontSize:10,color:T.muted,marginTop:1}}>{stk.name}</div></td>
                <td style={{padding:'9px 13px'}}><Tag>{stk.sector}</Tag></td>
                <td style={{padding:'9px 13px',textAlign:'right',fontFamily:T.mono,fontSize:12,color:T.text}}>₹{stk.price.toLocaleString('en-IN')}</td>
                <td style={{padding:'9px 13px',textAlign:'right',fontFamily:T.mono,fontSize:12,color:stk.chg>=0?T.green:T.red}}>{pct(stk.chg)}</td>
                {[stk.pe,stk.pb,stk.roe,stk.rev].map((v,j)=><td key={j} style={{padding:'9px 13px',textAlign:'right',fontFamily:T.mono,fontSize:12,color:T.text}}>{v.toFixed(1)}</td>)}
                {[stk.mom,stk.qual,stk.val,stk.grw].map((v,j)=><td key={j} style={{padding:'9px 13px',textAlign:'right',fontFamily:T.mono,fontSize:11,color:sc(v),fontWeight:700}}>{v}</td>)}
                <td style={{padding:'9px 13px',textAlign:'right'}}><Badge v={stk.composite}/></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ━━━ STOCK DETAIL ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function StockDetail({stock,nav}){
  const [aiText,setAiText]=useState('');
  const [aiLoad,setAiLoad]=useState(false);
  const [aiSource,setAiSource]=useState(null); // 'ollama' | 'offline'
  const pts=SP[stock.ticker]||[];
  const radar=[{f:'Momentum',v:stock.mom},{f:'Quality',v:stock.qual},{f:'Value',v:stock.val},{f:'Growth',v:stock.grw},{f:'Composite',v:stock.composite}];

  async function getAI(){
    setAiLoad(true); setAiText(''); setAiSource(null);
    const prompt=`Analyze ${stock.name} (${stock.ticker}, NSE):
Price: ₹${stock.price} | 1-Day: ${pct(stock.chg)} | Sector: ${stock.sector} | MCap: ₹${stock.mcap}K Cr
PE: ${stock.pe}x | PB: ${stock.pb}x | ROE: ${stock.roe}% | Revenue Growth: ${stock.rev}%
Factor Scores (0-100): Momentum ${stock.mom} · Quality ${stock.qual} · Value ${stock.val} · Growth ${stock.grw} · Composite ${stock.composite}

Provide:
**Quick Snapshot** (2-3 sentences on what metrics reveal)
**Strengths** (top 3 quantitative positives)
**Risks** (top 2 risks from data)
**Factor View** (what composite score of ${stock.composite}/100 means in ${stock.sector} context)
**Peers** (1-2 comparable NSE stocks to benchmark against)`;
    try{
      const text = await callOllama(
        [{role:'user',content:prompt}],
        'You are a quantitative equity analyst specializing in Indian NSE/BSE stocks. Provide structured, data-driven analysis. Format clearly with headers. End with: ⚠️ Educational purposes only — not investment advice.'
      );
      setAiText(text); setAiSource('ollama');
    }catch{
      setAiText(buildOfflineReport(stock)); setAiSource('offline');
    }
    setAiLoad(false);
  }

  return(
    <div style={{padding:'26px 30px',maxWidth:1200,fontFamily:T.sans}}>
      <button onClick={()=>nav('screener')} style={{background:'none',border:'none',color:T.muted,cursor:'pointer',fontSize:12,marginBottom:10,padding:0}}>← Back to Screener</button>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start',marginBottom:22}}>
        <div style={{display:'flex',alignItems:'center',gap:12}}>
          <div style={{width:46,height:46,background:`${T.blue}33`,borderRadius:10,display:'flex',alignItems:'center',justifyContent:'center',fontSize:13,fontWeight:700,fontFamily:T.mono,color:T.blue}}>{stock.ticker.slice(0,2)}</div>
          <div>
            <div style={{fontSize:22,fontWeight:700,color:T.text}}>{stock.ticker} <span style={{fontSize:13,color:T.muted,fontWeight:400}}>· {stock.name}</span></div>
            <div style={{display:'flex',gap:8,marginTop:4}}><Tag>{stock.sector}</Tag><Tag color={T.blue}>NSE Listed</Tag></div>
          </div>
        </div>
        <div style={{textAlign:'right'}}>
          <div style={{fontSize:28,fontWeight:700,fontFamily:T.mono,color:T.text}}>₹{stock.price.toLocaleString('en-IN')}</div>
          <div style={{fontSize:14,fontFamily:T.mono,color:stock.chg>=0?T.green:T.red}}>{stock.chg>=0?'▲':'▼'} {Math.abs(stock.chg).toFixed(2)}%</div>
        </div>
      </div>
      <div style={{display:'grid',gridTemplateColumns:'1fr 280px',gap:14,marginBottom:14}}>
        <div style={card({padding:'16px 18px'})}>
          <div style={{fontSize:13,fontWeight:600,color:T.text,marginBottom:14}}>Price History (6M)</div>
          <ResponsiveContainer width="100%" height={195}>
            <AreaChart data={pts} margin={{top:4,right:4,bottom:0,left:50}}>
              <defs><linearGradient id="sg" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor={stock.chg>=0?T.green:T.red} stopOpacity={0.3}/><stop offset="95%" stopColor={stock.chg>=0?T.green:T.red} stopOpacity={0}/></linearGradient></defs>
              <XAxis dataKey="d" tick={{fontSize:10,fill:T.muted}} tickLine={false} axisLine={false} interval={15}/>
              <YAxis tick={{fontSize:10,fill:T.muted,fontFamily:T.mono}} tickLine={false} axisLine={false} domain={['auto','auto']} tickFormatter={v=>'₹'+v.toLocaleString('en-IN')}/>
              <Tooltip content={<CT/>}/>
              <Area type="monotone" dataKey="p" stroke={stock.chg>=0?T.green:T.red} strokeWidth={2} fill="url(#sg)" dot={false}/>
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div style={card({padding:'16px 14px'})}>
          <div style={{fontSize:13,fontWeight:600,color:T.text,marginBottom:4}}>Factor Profile</div>
          <ResponsiveContainer width="100%" height={190}>
            <RadarChart data={radar}>
              <PolarGrid stroke={T.b}/>
              <PolarAngleAxis dataKey="f" tick={{fontSize:10,fill:T.muted}}/>
              <PolarRadiusAxis angle={90} domain={[0,100]} tick={false} axisLine={false}/>
              <Radar dataKey="v" stroke={T.blue} fill={T.blue} fillOpacity={0.18} strokeWidth={2}/>
            </RadarChart>
          </ResponsiveContainer>
          <div style={{textAlign:'center',marginTop:4}}><Badge v={stock.composite}/></div>
        </div>
      </div>
      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:14}}>
        <div style={card({padding:'16px 18px'})}>
          <div style={{fontSize:13,fontWeight:600,color:T.text,marginBottom:14}}>Fundamentals</div>
          {[['P/E Ratio',stock.pe.toFixed(1)+'x',stock.pe<30?T.green:stock.pe<60?T.amber:T.red],['P/B Ratio',stock.pb.toFixed(1)+'x',stock.pb<4?T.green:stock.pb<10?T.amber:T.red],['ROE',stock.roe.toFixed(1)+'%',stock.roe>18?T.green:stock.roe>10?T.amber:T.red],['Revenue Growth',stock.rev.toFixed(1)+'%',stock.rev>15?T.green:stock.rev>7?T.amber:T.red],['Market Cap','₹'+stock.mcap+'K Cr',T.text],['Sector',stock.sector,T.text]].map(([l,v,c])=>(
            <div key={l} style={{display:'flex',justifyContent:'space-between',alignItems:'center',padding:'8px 0',borderBottom:`1px solid ${T.b}`}}>
              <span style={{fontSize:12,color:T.sub}}>{l}</span>
              <span style={{fontSize:12,fontFamily:T.mono,fontWeight:600,color:c}}>{v}</span>
            </div>
          ))}
          <div style={{marginTop:16}}>{[['Momentum',stock.mom],['Quality',stock.qual],['Value',stock.val],['Growth',stock.grw]].map(([l,v])=><FactorBar key={l} label={l} value={v}/>)}</div>
        </div>
        <div style={card({padding:'16px 18px',display:'flex',flexDirection:'column'})}>
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:12}}>
            <div style={{fontSize:13,fontWeight:600,color:T.text}}>AI Research Summary</div>
            <button onClick={getAI} disabled={aiLoad} style={{display:'flex',alignItems:'center',gap:6,background:T.blue,border:'none',borderRadius:6,padding:'7px 13px',fontSize:12,color:'#fff',cursor:aiLoad?'not-allowed':'pointer',opacity:aiLoad?0.6:1}}>
              <Zap size={12}/>{aiLoad?'Analyzing…':'Generate AI Report'}
            </button>
          </div>
          {aiSource && (
            <div style={{marginBottom:8}}>
              <Tag color={aiSource==='ollama'?T.green:T.amber}>{aiSource==='ollama'?'⚡ Ollama (local LLM)':'📐 Offline Engine'}</Tag>
            </div>
          )}
          <div style={{flex:1,overflowY:'auto',fontSize:12,color:T.text,lineHeight:1.75,minHeight:280}}>
            {!aiText&&!aiLoad&&(
              <div style={{display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',height:'100%',gap:10,color:T.muted}}>
                <Zap size={28} color={T.blue} style={{opacity:0.4}}/>
                <div style={{textAlign:'center',fontSize:12}}>
                  <div style={{color:T.sub,marginBottom:4}}>Free, Open-Source AI Research</div>
                  <div>Tries your self-hosted Ollama instance first, falls back to an offline rule-based engine — zero cost either way.</div>
                </div>
              </div>
            )}
            {aiLoad&&<div style={{color:T.muted,display:'flex',alignItems:'center',gap:8,fontSize:12}}><RefreshCw size={13} style={{animation:'spin 1s linear infinite'}}/> Analyzing {stock.ticker}…</div>}
            {aiText&&<div style={{whiteSpace:'pre-wrap'}}>{aiText}</div>}
          </div>
        </div>
      </div>
    </div>
  );
}

// ━━━ PORTFOLIO ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function Portfolio(){
  const positions=POS.map(pos=>{
    const stk=STOCKS.find(s=>s.ticker===pos.ticker);
    const cur=stk.price*pos.qty, cst=pos.cost*pos.qty;
    return{...pos,stk,cur,cst,pnl:cur-cst,pp:(cur-cst)/cst*100};
  });
  const totVal=positions.reduce((a,p)=>a+p.cur,0);
  const totCst=positions.reduce((a,p)=>a+p.cst,0);
  const totPnl=totVal-totCst;
  const COLS=[T.blue,T.green,T.amber,'#a78bfa',T.red];
  const pie=positions.map((p,i)=>({name:p.ticker,v:p.cur,c:COLS[i]}));
  const portPts=genPrices(totVal,777,120).map(x=>({...x,v:x.p}));
  return(
    <div style={{padding:'26px 30px',maxWidth:1200,fontFamily:T.sans}}>
      <div style={{marginBottom:22}}><div style={{fontSize:22,fontWeight:700,color:T.text}}>Portfolio Analytics</div><div style={{fontSize:13,color:T.sub,marginTop:3}}>India Equity Portfolio · NSE Listed</div></div>
      <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:12,marginBottom:18}}>
        <Stat label="Portfolio Value" value={fI(totVal)} sub="Current market value" icon={Database}/>
        <Stat label="Total P&L" value={(totPnl>=0?'+':'')+fI(totPnl)} sub={pct(totPnl/totCst*100)} color={totPnl>=0?T.green:T.red} icon={TrendingUp}/>
        <Stat label="Portfolio Beta" value="1.12" sub="vs Nifty 50" icon={Activity}/>
        <Stat label="Sharpe Ratio" value="1.28" sub="12-month trailing" icon={Shield}/>
      </div>
      <div style={{display:'grid',gridTemplateColumns:'2fr 1fr',gap:14,marginBottom:14}}>
        <div style={card({padding:'16px 18px'})}>
          <div style={{fontSize:13,fontWeight:600,color:T.text,marginBottom:14}}>Portfolio Value (6M)</div>
          <ResponsiveContainer width="100%" height={185}>
            <AreaChart data={portPts} margin={{top:4,right:4,bottom:0,left:60}}>
              <defs><linearGradient id="pg" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor={T.green} stopOpacity={0.3}/><stop offset="95%" stopColor={T.green} stopOpacity={0}/></linearGradient></defs>
              <XAxis dataKey="d" tick={{fontSize:10,fill:T.muted}} tickLine={false} axisLine={false} interval={15}/>
              <YAxis tick={{fontSize:10,fill:T.muted,fontFamily:T.mono}} tickLine={false} axisLine={false} domain={['auto','auto']} tickFormatter={v=>'₹'+(v/100000).toFixed(0)+'L'}/>
              <Tooltip content={<CT/>}/>
              <Area type="monotone" dataKey="v" stroke={T.green} strokeWidth={2} fill="url(#pg)" dot={false}/>
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div style={card({padding:'16px 18px'})}>
          <div style={{fontSize:13,fontWeight:600,color:T.text,marginBottom:8}}>Allocation</div>
          <ResponsiveContainer width="100%" height={150}>
            <PieChart><Pie data={pie} cx="50%" cy="50%" innerRadius={42} outerRadius={65} dataKey="v" paddingAngle={3}>{pie.map((e,i)=><Cell key={i} fill={e.c}/>)}</Pie><Tooltip formatter={v=>[fI(v),'Value']}/></PieChart>
          </ResponsiveContainer>
          {pie.map((d,i)=>(
            <div key={i} style={{display:'flex',alignItems:'center',gap:7,marginTop:5}}>
              <div style={{width:8,height:8,borderRadius:'50%',background:d.c,flexShrink:0}}/>
              <span style={{fontSize:11,fontFamily:T.mono,color:T.sub}}>{d.name}</span>
              <span style={{fontSize:11,color:T.muted,marginLeft:'auto'}}>{(d.v/totVal*100).toFixed(1)}%</span>
            </div>
          ))}
        </div>
      </div>
      <div style={card({overflow:'auto'})}>
        <div style={{padding:'13px 18px',borderBottom:`1px solid ${T.b}`,fontSize:13,fontWeight:600,color:T.text}}>Positions</div>
        <table style={{width:'100%',borderCollapse:'collapse'}}>
          <thead><tr style={{borderBottom:`1px solid ${T.b}`}}>{['Ticker','Sector','Qty','Avg Cost','LTP','Value','P&L','P&L%','Score'].map(h=><th key={h} style={{padding:'9px 15px',fontSize:10,color:T.muted,textAlign:h==='Ticker'||h==='Sector'?'left':'right',fontWeight:600,textTransform:'uppercase',letterSpacing:'0.06em'}}>{h}</th>)}</tr></thead>
          <tbody>
            {positions.map((p,i)=>(
              <tr key={p.ticker} style={{borderBottom:`1px solid ${T.b}`,background:i%2===0?'transparent':`${T.el}55`}}>
                <td style={{padding:'11px 15px',fontFamily:T.mono,fontWeight:700,fontSize:12,color:T.text}}>{p.ticker}</td>
                <td style={{padding:'11px 15px'}}><Tag>{p.stk?.sector}</Tag></td>
                <td style={{padding:'11px 15px',textAlign:'right',fontFamily:T.mono,fontSize:12,color:T.text}}>{p.qty}</td>
                <td style={{padding:'11px 15px',textAlign:'right',fontFamily:T.mono,fontSize:12,color:T.sub}}>₹{p.cost.toLocaleString('en-IN')}</td>
                <td style={{padding:'11px 15px',textAlign:'right',fontFamily:T.mono,fontSize:12,color:T.text}}>₹{p.stk?.price.toLocaleString('en-IN')}</td>
                <td style={{padding:'11px 15px',textAlign:'right',fontFamily:T.mono,fontSize:12,color:T.text}}>{fI(p.cur)}</td>
                <td style={{padding:'11px 15px',textAlign:'right',fontFamily:T.mono,fontSize:12,color:p.pnl>=0?T.green:T.red}}>{p.pnl>=0?'+':''}{fI(p.pnl)}</td>
                <td style={{padding:'11px 15px',textAlign:'right',fontFamily:T.mono,fontSize:12,color:p.pp>=0?T.green:T.red}}>{pct(p.pp)}</td>
                <td style={{padding:'11px 15px',textAlign:'right'}}><Badge v={p.stk?.composite||0}/></td>
              </tr>
            ))}
          </tbody>
        </table>
        <div style={{padding:'13px 18px',borderTop:`1px solid ${T.b}`,display:'flex',gap:32}}>
          {[['Beta','1.12'],['Volatility (Ann.)','18.4%'],['Sharpe Ratio','1.28'],['Max Drawdown','-12.3%'],['Positions','5']].map(([l,v])=>(
            <div key={l}><div style={{fontSize:10,color:T.muted,textTransform:'uppercase',letterSpacing:'0.06em'}}>{l}</div><div style={{fontSize:15,fontFamily:T.mono,fontWeight:700,color:T.text,marginTop:2}}>{v}</div></div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ━━━ BACKTESTER ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function Backtester(){
  const [sel,setSel]=useState('Composite Score');
  const strategies=Object.keys(BT_STATS).filter(s=>s!=='Nifty 50');
  const stat=BT_STATS[sel];
  return(
    <div style={{padding:'26px 30px',maxWidth:1100,fontFamily:T.sans}}>
      <div style={{marginBottom:22}}><div style={{fontSize:22,fontWeight:700,color:T.text}}>Strategy Backtester</div><div style={{fontSize:13,color:T.sub,marginTop:3}}>Factor-based strategies · Nifty 500 universe · Jun 2022 – Jun 2025</div></div>
      <div style={{display:'flex',gap:10,marginBottom:22}}>
        {strategies.map(s=>{const c=BT_COL[s];return(<button key={s} onClick={()=>setSel(s)} style={{padding:'8px 18px',borderRadius:8,border:`1px solid ${sel===s?c:T.b}`,background:sel===s?`${c}22`:'transparent',color:sel===s?c:T.sub,fontSize:13,fontWeight:sel===s?600:400,cursor:'pointer'}}>{s}</button>);})}
      </div>
      <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:12,marginBottom:18}}>
        {[['3Y Return',`+${stat.ret.toFixed(1)}%`,T.green,'vs +56.2% Nifty 50'],['CAGR',`${stat.cagr.toFixed(1)}%`,T.blue,'vs 16.2% Nifty 50'],['Sharpe',stat.sharpe.toFixed(2),T.amber,'vs 0.94 Nifty 50'],['Max DD',`${stat.maxDD.toFixed(1)}%`,T.red,'vs -22.1% Nifty 50']].map(([l,v,c,sub])=>(
          <div key={l} style={card({padding:'13px 16px'})}>
            <div style={{fontSize:10,color:T.muted,textTransform:'uppercase',letterSpacing:'0.07em',marginBottom:5}}>{l}</div>
            <div style={{fontSize:21,fontWeight:700,fontFamily:T.mono,color:c}}>{v}</div>
            <div style={{fontSize:10,color:T.muted,marginTop:3}}>{sub}</div>
          </div>
        ))}
      </div>
      <div style={card({padding:'16px 18px',marginBottom:14})}>
        <div style={{fontSize:13,fontWeight:600,color:T.text,marginBottom:14}}>Portfolio Growth (Base 100) · All Strategies vs Nifty 50</div>
        <ResponsiveContainer width="100%" height={270}>
          <LineChart data={BT_CHART} margin={{top:4,right:16,bottom:0,left:40}}>
            <CartesianGrid stroke={T.b} strokeDasharray="3 3"/>
            <XAxis dataKey="date" tick={{fontSize:9,fill:T.muted}} tickLine={false} axisLine={false} interval={5}/>
            <YAxis tick={{fontSize:10,fill:T.muted,fontFamily:T.mono}} tickLine={false} axisLine={false} domain={[80,'auto']} tickFormatter={v=>v.toFixed(0)}/>
            <Tooltip content={<CT/>}/>
            <Legend wrapperStyle={{fontSize:11,color:T.sub}}/>
            {Object.entries(BT_COL).map(([k,c])=><Line key={k} type="monotone" dataKey={k} stroke={c} strokeWidth={k===sel?2.5:k==='Nifty 50'?1.5:1} dot={false} opacity={k===sel||k==='Nifty 50'?1:0.35}/>)}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div style={card({padding:'15px 18px'})}>
        <div style={{fontSize:13,fontWeight:600,color:T.text,marginBottom:12}}>Strategy Descriptions</div>
        <div style={{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:12}}>
          {[['High Momentum','Top-decile 12-1 month price momentum. Equal-weight. Quarterly rebalance. Nifty 500 universe.',T.amber],['Quality Value','Intersection of top-quartile Quality (ROE, margins, low debt) and Value (EV/EBITDA, PB). Semi-annual rebalance.','#a78bfa'],['Composite Score','Multi-factor: 25% Momentum + 25% Quality + 20% Value + 20% Growth + 10% Low Volatility. Monthly rebalance.',T.blue]].map(([n,d,c])=>(
            <div key={n} style={{background:T.el,borderRadius:8,padding:'12px 14px',border:`1px solid ${T.b}`}}>
              <div style={{fontSize:12,fontWeight:600,color:c,marginBottom:5}}>{n}</div>
              <div style={{fontSize:11,color:T.sub,lineHeight:1.6}}>{d}</div>
            </div>
          ))}
        </div>
        <div style={{marginTop:10,fontSize:10,color:T.muted}}>⚠️ Backtest results are illustrative. Past performance ≠ future returns. Transaction costs/slippage not fully modeled.</div>
      </div>
    </div>
  );
}

// ━━━ MACRO DASHBOARD ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function MacroDashboard(){
  return(
    <div style={{padding:'26px 30px',maxWidth:1200,fontFamily:T.sans}}>
      <div style={{marginBottom:22}}><div style={{fontSize:22,fontWeight:700,color:T.text}}>Macro Dashboard</div><div style={{fontSize:13,color:T.sub,marginTop:3}}>India macroeconomic indicators · RBI DBIE · MOSPI · NSE (all free, public sources)</div></div>
      <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:12,marginBottom:18}}>
        {[['RBI Repo Rate','5.75%','Jun 2026',T.blue],['CPI Inflation','2.60%','May 2026',T.green],['GDP Growth FY25','7.6%','Advance Est.',T.amber],['USD / INR','84.32','Jun 2026',T.text]].map(([l,v,s,c])=>(
          <div key={l} style={card({padding:'13px 16px'})}>
            <div style={{fontSize:10,color:T.muted,textTransform:'uppercase',letterSpacing:'0.07em',marginBottom:5}}>{l}</div>
            <div style={{fontSize:21,fontWeight:700,fontFamily:T.mono,color:c}}>{v}</div>
            <div style={{fontSize:11,color:T.sub,marginTop:3}}>{s}</div>
          </div>
        ))}
      </div>
      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:14}}>
        <div style={card({padding:'16px 18px'})}>
          <div style={{fontSize:13,fontWeight:600,color:T.text,marginBottom:14}}>RBI Repo Rate (%)</div>
          <ResponsiveContainer width="100%" height={175}>
            <LineChart data={MACRO.repo} margin={{top:4,right:8,bottom:0,left:30}}>
              <CartesianGrid stroke={T.b} strokeDasharray="3 3"/>
              <XAxis dataKey="q" tick={{fontSize:9,fill:T.muted}} tickLine={false} axisLine={false} interval={2}/>
              <YAxis tick={{fontSize:10,fill:T.muted,fontFamily:T.mono}} tickLine={false} axisLine={false} domain={[5,7]} tickFormatter={v=>v+'%'}/>
              <Tooltip content={<CT/>}/>
              <Line type="stepAfter" dataKey="v" stroke={T.blue} strokeWidth={2.5} dot={{r:3,fill:T.blue}} name="Repo Rate"/>
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div style={card({padding:'16px 18px'})}>
          <div style={{fontSize:13,fontWeight:600,color:T.text,marginBottom:14}}>CPI Inflation India (%)</div>
          <ResponsiveContainer width="100%" height={175}>
            <AreaChart data={MACRO.cpi} margin={{top:4,right:8,bottom:0,left:30}}>
              <defs><linearGradient id="cg" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor={T.amber} stopOpacity={0.4}/><stop offset="95%" stopColor={T.amber} stopOpacity={0}/></linearGradient></defs>
              <CartesianGrid stroke={T.b} strokeDasharray="3 3"/>
              <XAxis dataKey="m" tick={{fontSize:9,fill:T.muted}} tickLine={false} axisLine={false} interval={2}/>
              <YAxis tick={{fontSize:10,fill:T.muted,fontFamily:T.mono}} tickLine={false} axisLine={false} domain={[2,7]} tickFormatter={v=>v+'%'}/>
              <Tooltip content={<CT/>}/>
              <Area type="monotone" dataKey="v" stroke={T.amber} strokeWidth={2} fill="url(#cg)" name="CPI%" dot={false}/>
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div style={card({padding:'16px 18px'})}>
          <div style={{fontSize:13,fontWeight:600,color:T.text,marginBottom:14}}>USD / INR Exchange Rate</div>
          <ResponsiveContainer width="100%" height={175}>
            <LineChart data={MACRO.inr} margin={{top:4,right:8,bottom:0,left:40}}>
              <CartesianGrid stroke={T.b} strokeDasharray="3 3"/>
              <XAxis dataKey="m" tick={{fontSize:9,fill:T.muted}} tickLine={false} axisLine={false} interval={2}/>
              <YAxis tick={{fontSize:10,fill:T.muted,fontFamily:T.mono}} tickLine={false} axisLine={false} domain={[83,87]} tickFormatter={v=>'₹'+v}/>
              <Tooltip content={<CT/>}/>
              <Line type="monotone" dataKey="v" stroke={'#a78bfa'} strokeWidth={2} dot={{r:3,fill:'#a78bfa'}} name="USD/INR"/>
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div style={card({padding:'16px 18px'})}>
          <div style={{fontSize:13,fontWeight:600,color:T.text,marginBottom:14}}>FII Net Flows (₹ Cr)</div>
          <ResponsiveContainer width="100%" height={175}>
            <BarChart data={MACRO.fii} margin={{top:4,right:8,bottom:0,left:50}}>
              <CartesianGrid stroke={T.b} strokeDasharray="3 3"/>
              <XAxis dataKey="m" tick={{fontSize:9,fill:T.muted}} tickLine={false} axisLine={false} interval={2}/>
              <YAxis tick={{fontSize:10,fill:T.muted,fontFamily:T.mono}} tickLine={false} axisLine={false} tickFormatter={v=>(v/1000).toFixed(0)+'K'}/>
              <Tooltip formatter={v=>['₹'+v.toLocaleString('en-IN')+' Cr','FII Flow']}/>
              <Bar dataKey="v" name="FII Flow">{MACRO.fii.map((e,i)=><Cell key={i} fill={e.v>=0?T.green:T.red}/>)}</Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div style={card({padding:'15px 18px',marginTop:14})}>
        <div style={{fontSize:13,fontWeight:600,color:T.text,marginBottom:12}}>📊 Current Macro Regime Analysis</div>
        <div style={{display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:12}}>
          {[['🏦','Monetary Policy','Easing',T.green,'RBI in rate-cut cycle. Repo at 5.75%. Favours Banking, NBFC, Real Estate.'],['📉','Inflation','Controlled',T.green,'CPI at 2.6% — below RBI 4% target. Creates room for 25-50 bps more cuts in FY26.'],['🌍','FII Sentiment','Recovering',T.amber,'FII flows positive for 3 consecutive months after large Jan–Feb 2025 outflows.']].map(([ic,l,sig,c,desc])=>(
            <div key={l} style={{background:T.el,borderRadius:8,padding:'12px 14px',border:`1px solid ${T.b}`}}>
              <div style={{display:'flex',alignItems:'center',gap:8,marginBottom:6}}>
                <span style={{fontSize:16}}>{ic}</span>
                <span style={{fontSize:11,color:T.sub}}>{l}</span>
                <span style={{marginLeft:'auto',background:`${c}22`,color:c,border:`1px solid ${c}44`,borderRadius:4,padding:'1px 7px',fontSize:10,fontWeight:700}}>{sig}</span>
              </div>
              <div style={{fontSize:11,color:T.muted,lineHeight:1.6}}>{desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ━━━ AI RESEARCH CHAT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const SYS_PROMPT=`You are QuantAI, an open-source research assistant for Indian equity markets (NSE/BSE), running on a free self-hosted LLM. Deep expertise in:
- Nifty 50, Nifty 500, BSE 500 companies and fundamentals
- RBI monetary policy and sectoral impacts on Indian equities
- SEBI regulations, corporate governance, Indian accounting standards
- Factor investing: momentum, quality, value, growth, low-volatility in Indian context
- India macro: GDP, CPI, FII/DII flows, INR/USD, credit growth
- Sectors: Banking/NBFC, IT Services, FMCG, Auto, Pharma, Capital Goods, Telecom, Energy, Utilities

Provide concise, data-driven insights. Use ₹ for Rupee. Reference specific Indian market context (SEBI, NSE, BSE, RBI, MOSPI). Keep responses structured and clear. Always conclude with: ⚠️ For educational purposes only — not investment advice.`;

const QUICK=['Analyze HDFC Bank vs ICICI Bank quality factors','Impact of RBI rate cuts on NBFC sector','Best large-cap IT stocks for FY26 — growth vs valuations','Explain momentum investing for Indian markets','Nifty 50 sector rotation — current macro regime signal'];

function AIChat(){
  const [msgs,setMsgs]=useState([{role:'assistant',content:'🇮🇳 Namaste! I\'m QuantAI — running on a 100% free, open-source, self-hosted LLM (Ollama). No API keys, no payment, ever.\n\nI can help you:\n• Analyze Nifty 500 stocks and compare fundamentals\n• Discuss RBI policy impacts on sectors\n• Explain quantitative factors and factor investing\n• Research any NSE/BSE listed company\n• Interpret macro data for investment context\n\nWhat would you like to explore today?'}]);
  const [inp,setInp]=useState('');
  const [load,setLoad]=useState(false);
  const endRef=useRef(null);
  useEffect(()=>endRef.current?.scrollIntoView({behavior:'smooth'}),[msgs]);

  async function send(){
    if(!inp.trim()||load) return;
    const q=inp.trim(); setInp('');
    const next=[...msgs,{role:'user',content:q}];
    setMsgs(next); setLoad(true);
    try{
      const apiMsgs=next.filter((m,i)=>!(m.role==='assistant'&&i===0)).map(m=>({role:m.role,content:m.content}));
      const text = await callOllama(apiMsgs, SYS_PROMPT);
      setMsgs(p=>[...p,{role:'assistant',content:text,source:'ollama'}]);
    }catch{
      setMsgs(p=>[...p,{role:'assistant',content:buildOfflineChatReply(q),source:'offline'}]);
    }
    setLoad(false);
  }

  return(
    <div style={{padding:'26px 30px',maxWidth:860,display:'flex',flexDirection:'column',height:'calc(100vh - 0px)',fontFamily:T.sans}}>
      <div style={{marginBottom:16}}>
        <div style={{fontSize:22,fontWeight:700,color:T.text}}>QuantAI Research Assistant</div>
        <div style={{fontSize:13,color:T.sub,marginTop:3,display:'flex',alignItems:'center',gap:6}}>
          <Cpu size={12} color={T.green}/> Powered by Ollama (free, open-source, self-hosted) · Indian equity specialist
        </div>
      </div>
      <div style={{display:'flex',gap:8,flexWrap:'wrap',marginBottom:16}}>
        {QUICK.map(p=><button key={p} onClick={()=>setInp(p)} style={{background:T.el,border:`1px solid ${T.b}`,borderRadius:20,padding:'5px 13px',fontSize:11,color:T.sub,cursor:'pointer'}}>{p}</button>)}
      </div>
      <div style={{flex:1,overflowY:'auto',paddingBottom:8}}>
        {msgs.map((m,i)=>(
          <div key={i} style={{marginBottom:14,display:'flex',justifyContent:m.role==='user'?'flex-end':'flex-start'}}>
            <div style={{maxWidth:'82%',background:m.role==='user'?T.blue:T.el,border:`1px solid ${m.role==='user'?T.blue+'66':T.b}`,borderRadius:m.role==='user'?'12px 12px 3px 12px':'12px 12px 12px 3px',padding:'11px 15px',fontSize:13,color:T.text,lineHeight:1.75,whiteSpace:'pre-wrap'}}>
              {m.role==='assistant'&&(
                <div style={{display:'flex',alignItems:'center',gap:6,marginBottom:6}}>
                  <span style={{fontSize:10,color:T.blue,fontWeight:700,textTransform:'uppercase',letterSpacing:'0.08em'}}>QuantAI</span>
                  {m.source&&<Tag color={m.source==='ollama'?T.green:T.amber}>{m.source==='ollama'?'Ollama':'Offline'}</Tag>}
                </div>
              )}
              {m.content}
            </div>
          </div>
        ))}
        {load&&<div style={{display:'flex',alignItems:'center',gap:8,padding:'11px 15px',background:T.el,border:`1px solid ${T.b}`,borderRadius:12,width:'fit-content',fontSize:12,color:T.muted}}><span style={{fontSize:10,color:T.blue,fontWeight:700,textTransform:'uppercase',letterSpacing:'0.08em',marginRight:4}}>QuantAI</span><RefreshCw size={12} style={{animation:'spin 1s linear infinite'}}/> Thinking…</div>}
        <div ref={endRef}/>
      </div>
      <div style={{display:'flex',gap:10,marginTop:12}}>
        <input value={inp} onChange={e=>setInp(e.target.value)} onKeyDown={e=>e.key==='Enter'&&!e.shiftKey&&send()} placeholder="Ask about Indian stocks, sectors, macro factors, quant strategies…" style={{flex:1,background:T.el,border:`1px solid ${T.bhi}`,borderRadius:9,padding:'11px 15px',fontSize:13,color:T.text,outline:'none',fontFamily:T.sans}}/>
        <button onClick={send} disabled={load||!inp.trim()} style={{background:T.blue,border:'none',borderRadius:9,padding:'11px 18px',cursor:load?'not-allowed':'pointer',opacity:load||!inp.trim()?0.5:1,display:'flex',alignItems:'center'}}><Send size={16} color="#fff"/></button>
      </div>
    </div>
  );
}

// ━━━ APP ROOT ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export default function App(){
  const [page,setPage]=useState('dashboard');
  const [stock,setStock]=useState(STOCKS[4]);
  return(
    <div style={{display:'flex',background:T.bg,minHeight:'100vh',color:T.text,fontFamily:T.sans}}>
      <style>{`*{box-sizing:border-box;margin:0;padding:0;}::-webkit-scrollbar{width:5px;height:5px;}::-webkit-scrollbar-track{background:${T.bg};}::-webkit-scrollbar-thumb{background:${T.b};border-radius:3px;}select option{background:${T.el};}@keyframes spin{from{transform:rotate(0deg);}to{transform:rotate(360deg);}}`}</style>
      <Sidebar page={page} nav={p=>setPage(p)}/>
      <main style={{marginLeft:215,flex:1,overflowY:'auto',minHeight:'100vh'}}>
        {page==='dashboard'&&<Dashboard nav={setPage} setStock={setStock}/>}
        {page==='screener' &&<Screener  nav={setPage} setStock={setStock}/>}
        {page==='stock'    &&<StockDetail stock={stock} nav={setPage}/>}
        {page==='portfolio'&&<Portfolio/>}
        {page==='backtest' &&<Backtester/>}
        {page==='macro'    &&<MacroDashboard/>}
        {page==='ai'       &&<AIChat/>}
      </main>
    </div>
  );
}
