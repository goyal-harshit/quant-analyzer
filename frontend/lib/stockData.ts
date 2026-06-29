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
// Surface / text tokens reference theme-aware CSS variables (defined in
// app/globals.css; flipped by the ThemeProvider via `html.light`/`html.dark`),
// so inline `style={{ background: T.card }}` reacts to the dark/light toggle.
// Accent colors stay literal hex — they read well on both themes AND are used
// with the alpha-append idiom (`${T.green}22`) that requires a hex string.
export const T = {
  bg: 'var(--bg)',
  card: 'var(--card)',
  el: 'var(--elevated)',
  b: 'var(--border)',
  bhi: 'var(--border-hi)',
  blue: '#3b82f6',
  green: '#22c55e',
  red: '#f43f5e',
  amber: '#f59e0b',
  purple: '#a78bfa',
  text: 'var(--text-primary)',
  sub: 'var(--text-sub)',
  muted: 'var(--text-muted)',
  mono: '"JetBrains Mono",Consolas,monospace',
  sans: 'Inter,system-ui,sans-serif',
};
