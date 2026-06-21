/**
 * QuantAI API Client
 * Typed wrapper around the FastAPI backend.
 */

import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

const client = axios.create({
  baseURL: API_BASE,
  timeout: 120000,
  headers: { "Content-Type": "application/json" },
});

// Attach Authorization header if token exists in localStorage
client.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// ── TYPES ───────────────────────────────────────────────────────
export interface StockQuote {
  ticker: string;
  name: string;
  sector: string;
  price: number;
  change: number;
  change_pct: number;
  prev_close?: number;
  volume: number;
  market_cap: number | null;
  day_high?: number;
  day_low?: number;
  fifty_two_week_high?: number;
  fifty_two_week_low?: number;
}

export interface Fundamentals {
  ticker: string;
  pe_ratio: number | null;
  pb_ratio: number | null;
  ev_ebitda?: number | null;
  ps_ratio?: number | null;
  peg_ratio?: number | null;
  roe: number | null;
  roce?: number | null;
  roa?: number | null;
  net_margin?: number | null;
  operating_margin?: number | null;
  current_ratio?: number | null;
  quick_ratio?: number | null;
  debt_equity: number | null;
  interest_coverage?: number | null;
  revenue_growth: number | null;
  dividend_yield?: number | null;
  market_cap: number | null;
  book_value?: number | null;
  face_value?: number | null;
  sector: string | null;
  industry?: string | null;
  exchange?: string | null;
  factor_scores?: {
    momentum?: number;
    quality?: number;
    value?: number;
    growth?: number;
    low_volatility?: number;
    composite?: number;
  };
}

export interface ScreenerResult {
  ticker: string;
  name: string;
  sector: string;
  price: number;
  change_pct: number;
  pe_ratio: number | null;
  pb_ratio: number | null;
  roe: number | null;
  revenue_growth: number | null;
  momentum_score: number | null;
  quality_score: number | null;
  value_score: number | null;
  growth_score: number | null;
  composite_score: number | null;
  market_cap: number | null;
}

export interface PortfolioSummary {
  id: number;
  name: string;
  total_value: number;
  total_cost: number;
  total_pnl: number;
  total_pnl_pct: number;
  position_count: number;
}

export interface BacktestMetrics {
  total_return: number;
  annualised_return: number;
  benchmark_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
}

// ── STOCKS ──────────────────────────────────────────────────────
export const stocksApi = {
  getQuote: (ticker: string, refresh = false) =>
    client.get<StockQuote>(`/stocks/${ticker}/quote`, { params: { refresh } }).then((r) => r.data),

  getHistory: (ticker: string, period = "1y", refresh = false) =>
    client.get(`/stocks/${ticker}/history`, { params: { period, refresh } }).then((r) => r.data),

  getFundamentals: (ticker: string, refresh = false) =>
    client.get<Fundamentals>(`/stocks/${ticker}/fundamentals`, { params: { refresh } }).then((r) => r.data),

  getFactors: (ticker: string) =>
    client.get(`/stocks/${ticker}/factors`).then((r) => r.data),

  getTechnicals: (ticker: string) =>
    client.get(`/stocks/${ticker}/technicals`).then((r) => r.data),

  getBatchQuotes: (tickers: string[], refresh = false) =>
    client.get(`/stocks/batch/quotes`, { params: { tickers: tickers.join(","), refresh } }).then((r) => r.data),

  search: (query: string) =>
    client.get(`/stocks/search`, { params: { q: query } }).then((r) => r.data),
};

// ── SCREENER ────────────────────────────────────────────────────
export const screenerApi = {
  screen: (filters: Record<string, any>) =>
    client.post<{ results: ScreenerResult[]; total: number; filtered: number }>("/screener", filters)
      .then((r) => r.data),

  getSectors: () => client.get<{ sectors: string[] }>("/screener/sectors").then((r) => r.data),

  getFactorDefinitions: () => client.get("/screener/factor-definitions").then((r) => r.data),
};

// ── PORTFOLIO ───────────────────────────────────────────────────
export const portfolioApi = {
  list: () => client.get<PortfolioSummary[]>("/portfolio").then((r) => r.data),

  create: (data: { name: string; currency?: string; benchmark?: string }) =>
    client.post("/portfolio", data).then((r) => r.data),

  get: (id: number, refresh = false) => client.get(`/portfolio/${id}`, { params: { refresh } }).then((r) => r.data),

  addPosition: (portfolioId: number, position: { ticker: string; quantity: number; avg_cost: number }) =>
    client.post(`/portfolio/${portfolioId}/positions`, position).then((r) => r.data),

  removePosition: (portfolioId: number, positionId: number) =>
    client.delete(`/portfolio/${portfolioId}/positions/${positionId}`).then((r) => r.data),

  getSectorAllocation: (portfolioId: number) =>
    client.get(`/portfolio/${portfolioId}/sector-allocation`).then((r) => r.data),

  delete: (id: number) =>
    client.delete(`/portfolio/${id}`).then((r) => r.data),

  getPerformance: (id: number, benchmark = "NIFTY50", period = "1y", refresh = false) =>
    client.get(`/portfolio/${id}/performance`, { params: { benchmark, period, refresh } }).then((r) => r.data),
};

// ── BACKTEST ────────────────────────────────────────────────────
export const backtestApi = {
  run: (request: Record<string, any>) =>
    client.post("/backtest", request).then((r) => r.data),

  getStrategyTemplates: () => client.get("/backtest/strategies").then((r) => r.data),
};

// ── MACRO ───────────────────────────────────────────────────────
export const macroApi = {
  getDashboard: (refresh = false) => client.get("/macro", { params: { refresh } }).then((r) => r.data),
  getRegime: () => client.get("/macro/regime").then((r) => r.data),
  getIndicators: (refresh = false) => client.get("/macro", { params: { refresh } }).then((r) => r.data),
};

// ── AI ──────────────────────────────────────────────────────────
export const aiApi = {
  chat: (data: { messages: Array<{ role: string; content: string }>; context_ticker?: string; provider?: string; model?: string; api_key?: string }) =>
    client.post("/ai/chat", data).then((r) => r.data),

  generateReport: (ticker: string, reportType = "full") =>
    client.post(`/ai/report/${ticker}`, { ticker, report_type: reportType }).then((r) => r.data),

  generateThesis: (ticker: string) =>
    client.post(`/ai/thesis/${ticker}`).then((r) => r.data),

  earningsSummary: (ticker: string, period = "latest") =>
    client.post("/ai/earnings-summary", { ticker, period }).then((r) => r.data),

  portfolioRiskNarrative: (portfolioData: Record<string, any>) =>
    client.post("/ai/portfolio-risk-narrative", portfolioData).then((r) => r.data),

  getReport: (data: { ticker: string; report_type?: string }) =>
    client.post("/ai/report", data).then((r) => r.data),

  getEarningsSummary: (data: { ticker: string; period?: string }) =>
    client.post("/ai/earnings-summary", data).then((r) => r.data),
};

// ── DASHBOARD ────────────────────────────────────────────────────
export const dashboardApi = {
  getMarketSummary: (refresh = false) =>
    client.get("/dashboard/market-summary", { params: { refresh } }).then((r) => r.data),

  getTopMovers: (refresh = false) =>
    client.get("/dashboard/top-gainers-losers", { params: { refresh } }).then((r) => r.data),

  getTopGainersLosers: (refresh = false) =>
    client.get("/dashboard/top-gainers-losers", { params: { refresh } }).then((r) => r.data),

  getSectorPerformance: (refresh = false) =>
    client.get("/dashboard/sector-performance", { params: { refresh } }).then((r) => r.data),

  getFactorSignals: (refresh = false) =>
    client.get("/dashboard/factor-signals", { params: { refresh } }).then((r) => r.data),

  getUniverseOverview: (refresh = false) =>
    client.get("/dashboard/universe-overview", { params: { refresh } }).then((r) => r.data),
};

// ── NEWS ──────────────────────────────────────────────────────────
export const newsApi = {
  getNews: () =>
    client.get("/news").then((r) => r.data),

  getTickerSentiment: (ticker: string) =>
    client.get(`/news/sentiment/${ticker}`).then((r) => r.data),
};

// ── EARNINGS ──────────────────────────────────────────────────────
export const earningsApi = {
  getCalendar: () =>
    client.get("/earnings/calendar").then((r) => r.data),

  getHistory: (ticker: string) =>
    client.get(`/earnings/${ticker}/history`).then((r) => r.data),
};

// ── QUANT LAB ─────────────────────────────────────────────────────
export const quantLabApi = {
  scoreUniverse: (request: Record<string, any>) =>
    client.post("/quant-lab/score", request).then((r) => r.data),

  getFactorDefinitions: () =>
    client.get("/quant-lab/factor-definitions").then((r) => r.data),
};

// ── STRATEGY BUILDER ──────────────────────────────────────────────
export const strategyBuilderApi = {
  backtest: (request: Record<string, any>) =>
    client.post("/strategy-builder/backtest", request).then((r) => r.data),

  getRuleTemplates: () =>
    client.get("/strategy-builder/rule-templates").then((r) => r.data),
};

// ── WATCHLISTS ────────────────────────────────────────────────────
export const watchlistsApi = {
  create: (data: { name: string; tickers?: string[] }) =>
    client.post("/watchlists", data).then((r) => r.data),

  list: () =>
    client.get("/watchlists").then((r) => r.data),

  get: (id: number, refresh = false) =>
    client.get(`/watchlists/${id}`, { params: { refresh } }).then((r) => r.data),

  updateTickers: (id: number, tickers: string[]) =>
    client.put(`/watchlists/${id}/tickers`, tickers).then((r) => r.data),

  delete: (id: number) =>
    client.delete(`/watchlists/${id}`).then((r) => r.data),

  getPerformance: (id: number, benchmark = "NIFTY50", period = "1y") =>
    client.get(`/watchlists/${id}/performance`, { params: { benchmark, period } }).then((r) => r.data),
};

// ── ALERTS ────────────────────────────────────────────────────────
export const alertsApi = {
  create: (data: { ticker: string; condition_type: string; threshold: number }) =>
    client.post("/alerts", data).then((r) => r.data),

  list: () =>
    client.get("/alerts").then((r) => r.data),

  evaluate: () =>
    client.get("/alerts/evaluate").then((r) => r.data),

  delete: (id: number) =>
    client.delete(`/alerts/${id}`).then((r) => r.data),
};

// ── AUTH ──────────────────────────────────────────────────────────
export const authApi = {
  register: (data: Record<string, any>) =>
    client.post("/auth/register", data).then((r) => r.data),

  login: (data: URLSearchParams) =>
    client.post("/auth/login", data, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    }).then((r) => r.data),

  me: () =>
    client.get("/auth/me").then((r) => r.data),
};


// ── STOCK INSIGHT (consolidated — replaces 4+ sequential calls) ─────
export const insightApi = {
  getStockInsight: (ticker: string, includeAi = false, refresh = false) =>
    client.get(`/insight/${ticker}`, { params: { include_ai: includeAi, refresh } }).then((r) => r.data),
};

// ── MUTUAL FUNDS ──────────────────────────────────────────────────
export interface MFSearchResult {
  scheme_code: number;
  scheme_name: string;
  fund_house?: string | null;
  category?: string | null;
}

export const mfApi = {
  search: (q: string) =>
    client.get<{ query: string; count: number; results: MFSearchResult[] }>("/mf/search", { params: { q } })
      .then((r) => r.data),

  popular: () =>
    client.get<{ results: MFSearchResult[] }>("/mf/popular").then((r) => r.data),

  getScheme: (code: number, period = "3y") =>
    client.get(`/mf/${code}`, { params: { period } }).then((r) => r.data),

  getReturns: (code: number) =>
    client.get(`/mf/${code}/returns`).then((r) => r.data),

  getRisk: (code: number) =>
    client.get(`/mf/${code}/risk`).then((r) => r.data),

  sipCalculator: (body: { monthly_amount: number; years: number; expected_return?: number; annual_step_up?: number }) =>
    client.post("/mf/sip-calculator", body).then((r) => r.data),

  compare: (scheme_codes: number[]) =>
    client.post("/mf/compare", { scheme_codes }).then((r) => r.data),
};

// ── IPO ───────────────────────────────────────────────────────────
export interface IPOItem {
  id: string;
  company_name: string;
  symbol?: string | null;
  exchange: string;
  ipo_type: string;
  issue_size_cr?: number | null;
  price_band_low?: number | null;
  price_band_high?: number | null;
  lot_size?: number | null;
  open_date?: string | null;
  close_date?: string | null;
  listing_date?: string | null;
  listing_price?: number | null;
  current_price?: number | null;
  listing_gain_pct?: number | null;
  gmp?: number | null;
  gmp_pct?: number | null;
  subscription_times?: number | null;
  status: string;
}

export const ipoApi = {
  all: (refresh = false) => client.get<{ ipos: IPOItem[] }>("/ipo", { params: { refresh } }).then((r) => r.data),
  upcoming: () => client.get<{ ipos: IPOItem[] }>("/ipo/upcoming").then((r) => r.data),
  open: () => client.get<{ ipos: IPOItem[] }>("/ipo/open").then((r) => r.data),
  listed: (days = 60) => client.get<{ ipos: IPOItem[] }>("/ipo/listed", { params: { days } }).then((r) => r.data),
  sme: () => client.get<{ ipos: IPOItem[] }>("/ipo/sme").then((r) => r.data),
  calendar: (month?: string) => client.get("/ipo/calendar", { params: { month } }).then((r) => r.data),
};

// MF refresh helpers
export const mfRefresh = {
  scheme: (code: number, period = "3y") =>
    client.get(`/mf/${code}`, { params: { period, refresh: true } }).then((r) => r.data),
};

export default client;
