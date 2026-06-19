// ━━━ Seeded RNG ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function mkRng(seed: number) {
  let s = seed;
  return () => { s = (s * 9301 + 49297) % 233280; return s / 233280; };
}

// ━━━ Stock Types ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export type Stock = {
  ticker: string;
  name: string;
  sector: string;
  price: number;
  chg: number;
  pe: number;
  pb: number;
  roe: number;
  rev: number;
  mom: number;
  qual: number;
  val: number;
  grw: number;
  mcap: number;
  composite: number;
};

export type PricePoint = { d: string; p: number };

export type Position = {
  ticker: string;
  qty: number;
  cost: number;
};

export type BacktestStat = {
  cagr: number;
  sharpe: number;
  maxDD: number;
  ret: number;
};

// ━━━ RAW DATA ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const RAW: [string, string, string, number, number, number, number, number, number, number, number, number, number, number][] = [
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

export const STOCKS: Stock[] = RAW.map(([ticker, name, sector, price, chg, pe, pb, roe, rev, mom, qual, val, grw, mcap]) => ({
  ticker, name, sector, price, chg, pe, pb, roe, rev, mom, qual, val, grw, mcap,
  composite: Math.round(mom * 0.25 + qual * 0.25 + val * 0.20 + grw * 0.20 + Math.min(100, roe * 0.8) * 0.10),
}));

export const SECTORS: string[] = ['All', ...new Set(STOCKS.map(s => s.sector))];

// ━━━ Price History Generation ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export function genPrices(base: number, seed: number, n = 120): PricePoint[] {
  const r = mkRng(seed);
  const pts: PricePoint[] = [];
  let p = base * 0.80;
  const st = new Date('2024-11-15');
  for (let i = 0; i < n; i++) {
    const d = new Date(st);
    d.setDate(d.getDate() + i);
    if (d.getDay() === 0 || d.getDay() === 6) continue;
    const shock = r() < 0.06 ? (r() - 0.5) * 0.04 : 0;
    p *= (1 + 0.0004 + (r() - 0.48) * 0.018 + shock);
    pts.push({ d: d.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }), p: +p.toFixed(2) });
  }
  if (!pts.length) return pts;
  const scale = base / pts[pts.length - 1].p;
  return pts.map(x => ({ ...x, p: +(x.p * scale).toFixed(2) }));
}

export const priceMap: Record<string, PricePoint[]> = {};
STOCKS.forEach((s, i) => { priceMap[s.ticker] = genPrices(s.price, i * 137 + 42); });

// ━━━ Portfolio Seed Data ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export const SEED_POSITIONS: Position[] = [
  { ticker: 'ICICIBANK', qty: 150, cost: 985.40 },
  { ticker: 'TCS', qty: 20, cost: 3650.80 },
  { ticker: 'BHARTIARTL', qty: 100, cost: 1425.50 },
  { ticker: 'TATAMOTORS', qty: 200, cost: 820.30 },
  { ticker: 'SBIN', qty: 250, cost: 710.20 },
];

// ━━━ Macro Data ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export const MACRO = {
  repo: [
    { q: 'Q2FY23', v: 5.9 }, { q: 'Q3FY23', v: 6.25 }, { q: 'Q4FY23', v: 6.5 },
    { q: 'Q1FY24', v: 6.5 }, { q: 'Q2FY24', v: 6.5 }, { q: 'Q3FY24', v: 6.5 },
    { q: 'Q4FY24', v: 6.5 }, { q: 'Q1FY25', v: 6.5 }, { q: 'Q2FY25', v: 6.5 },
    { q: 'Q3FY25', v: 6.25 }, { q: 'Q4FY25', v: 6.0 }, { q: 'Q1FY26', v: 5.75 },
  ],
  cpi: [
    { m: 'Jul-24', v: 3.54 }, { m: 'Aug-24', v: 3.65 }, { m: 'Sep-24', v: 5.49 },
    { m: 'Oct-24', v: 6.21 }, { m: 'Nov-24', v: 5.48 }, { m: 'Dec-24', v: 5.22 },
    { m: 'Jan-25', v: 4.26 }, { m: 'Feb-25', v: 3.61 }, { m: 'Mar-25', v: 3.34 },
    { m: 'Apr-25', v: 3.16 }, { m: 'May-25', v: 2.82 }, { m: 'Jun-25', v: 2.60 },
  ],
  inr: [
    { m: 'Jul-24', v: 83.71 }, { m: 'Aug-24', v: 83.95 }, { m: 'Sep-24', v: 83.80 },
    { m: 'Oct-24', v: 84.05 }, { m: 'Nov-24', v: 84.48 }, { m: 'Dec-24', v: 84.92 },
    { m: 'Jan-25', v: 85.98 }, { m: 'Feb-25', v: 86.45 }, { m: 'Mar-25', v: 86.12 },
    { m: 'Apr-25', v: 85.41 }, { m: 'May-25', v: 84.89 }, { m: 'Jun-25', v: 84.32 },
  ],
  fii: [
    { m: 'Jul-24', v: 8543 }, { m: 'Aug-24', v: 7234 }, { m: 'Sep-24', v: 57724 },
    { m: 'Oct-24', v: -94017 }, { m: 'Nov-24', v: -45974 }, { m: 'Dec-24', v: 15446 },
    { m: 'Jan-25', v: -87374 }, { m: 'Feb-25', v: -34574 }, { m: 'Mar-25', v: 3973 },
    { m: 'Apr-25', v: 10456 }, { m: 'May-25', v: 23782 }, { m: 'Jun-25', v: 15234 },
  ],
};

// ━━━ Backtest Data ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export function genBT(seed: number, cagr: number, vol: number) {
  const r = mkRng(seed);
  const pts: { date: string; value: number }[] = [];
  let v = 100;
  const mr = (1 + cagr / 100) ** (1 / 12) - 1;
  const st = new Date('2022-06-01');
  for (let i = 0; i <= 36; i++) {
    const d = new Date(st);
    d.setMonth(d.getMonth() + i);
    const lbl = d.toLocaleDateString('en-IN', { month: 'short', year: '2-digit' });
    if (i > 0) v *= (1 + mr + (r() - 0.5) * vol * 2);
    pts.push({ date: lbl, value: +v.toFixed(1) });
  }
  return pts;
}

export const BT_DATA: Record<string, { date: string; value: number }[]> = {
  'High Momentum': genBT(42, 22.5, 0.045),
  'Quality Value': genBT(99, 18.8, 0.035),
  'Composite Score': genBT(7, 24.3, 0.040),
  'Nifty 50': genBT(200, 16.2, 0.038),
};

export const BT_STATS: Record<string, BacktestStat> = {
  'High Momentum': { cagr: 22.5, sharpe: 1.42, maxDD: -18.3, ret: 82.1 },
  'Quality Value': { cagr: 18.8, sharpe: 1.21, maxDD: -14.2, ret: 67.3 },
  'Composite Score': { cagr: 24.3, sharpe: 1.56, maxDD: -16.8, ret: 91.4 },
  'Nifty 50': { cagr: 16.2, sharpe: 0.94, maxDD: -22.1, ret: 56.2 },
};

export const BT_CHART = Array.from({ length: 37 }, (_, i) => {
  const o: Record<string, number | string> = { date: BT_DATA['Nifty 50'][i].date };
  Object.entries(BT_DATA).forEach(([k, a]) => { o[k] = a[i].value; });
  return o;
});

export const BT_COLORS: Record<string, string> = {
  'High Momentum': '#f59e0b',
  'Quality Value': '#a78bfa',
  'Composite Score': '#3b82f6',
  'Nifty 50': '#475569',
};

// ━━━ Utilities ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export const fI = (n: number) => '₹' + n.toLocaleString('en-IN', { maximumFractionDigits: 0 });
export const pct = (n: number) => `${n > 0 ? '+' : ''}${n.toFixed(2)}%`;

export function scoreColor(v: number): string {
  return v >= 70 ? '#22c55e' : v >= 45 ? '#f59e0b' : '#f43f5e';
}

// ━━━ Design Tokens ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export const T = {
  bg: '#030712',
  card: '#0a1020',
  el: '#0f182e',
  b: '#1e2d4a',
  bhi: '#2a3f6a',
  blue: '#3b82f6',
  green: '#22c55e',
  red: '#f43f5e',
  amber: '#f59e0b',
  purple: '#a78bfa',
  text: '#e2e8f0',
  sub: '#94a3b8',
  muted: '#475569',
  mono: '"JetBrains Mono",Consolas,monospace',
  sans: 'Inter,system-ui,sans-serif',
};
