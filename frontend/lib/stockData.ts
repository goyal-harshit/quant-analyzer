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
